from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from patient_similarity.config import SimilarityConfig
from patient_similarity.distance import ConceptDistanceModel
from patient_similarity.domain import MatchedEvent, MatchResult, Patient, PatientEvent
from patient_similarity.matching.base import EventMatcher
from patient_similarity.matching.event_features import EventFeatures, build_event_features


@dataclass(frozen=True)
class RealMatchCost:
    accepted: bool
    total_cost: float
    semantic_distance: float
    temporal_penalty: float = 0.0
    sequence_penalty: float = 0.0
    temporal_cost: float = 0.0
    sequence_cost: float = 0.0


class AssignmentMatcher(EventMatcher):
    def __init__(self, config: SimilarityConfig):
        self.config = config
        self.matching_config = config.matching
        self.scoring_config = config.scoring

        self.matching_config.validate()
        self.scoring_config.validate()

    def match(
        self,
        seed_patient: Patient,
        candidate_patient: Patient,
        seed_events: Sequence[PatientEvent],
        candidate_events: Sequence[PatientEvent],
        concept_distance: ConceptDistanceModel,
        seed_event_weights: Sequence[float],
    ) -> MatchResult:
        seed_events = tuple(seed_events)
        candidate_events = tuple(candidate_events)
        seed_event_weights = tuple(float(weight) for weight in seed_event_weights)

        if not seed_events:
            raise ValueError(
                f"Seed patient {seed_patient.patient_id} has no seed events to match."
            )

        if len(seed_event_weights) != len(seed_events):
            raise ValueError(
                "seed_event_weights must have the same length as seed_events."
            )

        if any(weight < 0.0 for weight in seed_event_weights):
            raise ValueError("seed_event_weights cannot contain negative values.")

        total_weight = sum(seed_event_weights)
        if total_weight <= 0.0:
            raise ValueError("Sum of seed_event_weights must be greater than 0.")

        seed_features = build_event_features(
            patient=seed_patient,
            selected_events=seed_events,
        )

        candidate_features = build_event_features(
            patient=candidate_patient,
            selected_events=candidate_events,
        )

        cost_matrix, real_cost_details = self._build_cost_matrix(
            seed_features=seed_features,
            candidate_features=candidate_features,
            concept_distance=concept_distance,
        )

        row_indices, column_indices = linear_sum_assignment(cost_matrix)

        matches = []

        for row_index, column_index in zip(row_indices, column_indices):
            seed_event = seed_events[row_index]
            weight = seed_event_weights[row_index]

            if column_index < len(candidate_events):
                details = real_cost_details[(row_index, column_index)]

                if details.accepted:
                    candidate_event = candidate_events[column_index]
                    assigned_cost = details.total_cost
                    semantic_distance = details.semantic_distance
                    temporal_penalty = details.temporal_penalty
                    sequence_penalty = details.sequence_penalty
                    temporal_cost = details.temporal_cost
                    sequence_cost = details.sequence_cost
                else:
                    candidate_event = None
                    assigned_cost = self.matching_config.unmatched_penalty
                    semantic_distance = details.semantic_distance
                    temporal_penalty = 0.0
                    sequence_penalty = 0.0
                    temporal_cost = 0.0
                    sequence_cost = 0.0
            else:
                candidate_event = None
                assigned_cost = self.matching_config.unmatched_penalty
                semantic_distance = None
                temporal_penalty = 0.0
                sequence_penalty = 0.0
                temporal_cost = 0.0
                sequence_cost = 0.0

            matches.append(
                MatchedEvent(
                    seed_event=seed_event,
                    candidate_event=candidate_event,
                    distance=assigned_cost,
                    weight=weight,
                    semantic_distance=semantic_distance,
                    temporal_penalty=temporal_penalty,
                    sequence_penalty=sequence_penalty,
                    temporal_cost=temporal_cost,
                    sequence_cost=sequence_cost,
                )
            )

        matches = tuple(
            sorted(matches, key=lambda match: seed_events.index(match.seed_event))
        )

        weighted_distance = sum(match.weighted_cost for match in matches) / total_weight

        return MatchResult(
            distance=weighted_distance,
            matches=matches,
        )

    def _build_cost_matrix(
        self,
        seed_features: Sequence[EventFeatures],
        candidate_features: Sequence[EventFeatures],
        concept_distance: ConceptDistanceModel,
    ) -> tuple[np.ndarray, dict[tuple[int, int], RealMatchCost]]:
        n_seed = len(seed_features)
        n_candidate = len(candidate_features)

        real_costs = np.empty((n_seed, n_candidate), dtype=float)
        real_cost_details: dict[tuple[int, int], RealMatchCost] = {}

        for seed_index, seed_feature in enumerate(seed_features):
            for candidate_index, candidate_feature in enumerate(candidate_features):
                cost_details = self._real_match_cost(
                    seed_feature=seed_feature,
                    candidate_feature=candidate_feature,
                    concept_distance=concept_distance,
                )

                real_cost_details[(seed_index, candidate_index)] = cost_details
                real_costs[seed_index, candidate_index] = cost_details.total_cost

        dummy_costs = np.full(
            shape=(n_seed, n_seed),
            fill_value=self.matching_config.unmatched_penalty,
            dtype=float,
        )

        if n_candidate == 0:
            return dummy_costs, real_cost_details

        return np.concatenate([real_costs, dummy_costs], axis=1), real_cost_details


    def _real_match_cost(
        self,
        seed_feature: EventFeatures,
        candidate_feature: EventFeatures,
        concept_distance: ConceptDistanceModel,
    ) -> RealMatchCost:
        semantic_distance = concept_distance.distance(
            seed_feature.event.code,
            candidate_feature.event.code,
        )

        threshold = self.matching_config.semantic_threshold

        if threshold is not None and semantic_distance > threshold:
            return RealMatchCost(
                accepted=False,
                # Slightly above unmatched penalty so the dummy column is preferred.
                total_cost=self.matching_config.unmatched_penalty + 1e-12,
                semantic_distance=semantic_distance,
            )

        temporal_penalty = _bounded_difference_penalty(
            left=seed_feature.event_age_years,
            right=candidate_feature.event_age_years,
            scale=self.scoring_config.match_age_scale_years,
        )

        sequence_penalty = _bounded_difference_penalty(
            left=seed_feature.sequence_position,
            right=candidate_feature.sequence_position,
            scale=self.scoring_config.sequence_scale,
        )

        temporal_cost = self.scoring_config.temporal_weight * temporal_penalty
        sequence_cost = self.scoring_config.sequence_weight * sequence_penalty

        total_cost = semantic_distance + temporal_cost + sequence_cost

        return RealMatchCost(
            accepted=True,
            total_cost=total_cost,
            semantic_distance=semantic_distance,
            temporal_penalty=temporal_penalty,
            sequence_penalty=sequence_penalty,
            temporal_cost=temporal_cost,
            sequence_cost=sequence_cost,
        )

def _bounded_difference_penalty(
    left: float,
    right: float,
    scale: float,
) -> float:
    difference = abs(left - right)

    if difference == 0.0:
        return 0.0

    return difference / (difference + scale)