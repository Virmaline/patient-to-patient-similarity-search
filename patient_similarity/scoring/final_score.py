from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from patient_similarity.config import SimilarityConfig
from patient_similarity.distance import ConceptDistanceModel, InformationContentModel
from patient_similarity.domain import ComponentScores, Patient, PatientId
from patient_similarity.matching import AssignmentMatcher
from patient_similarity.scoring.age_score import patient_age_penalty
from patient_similarity.scoring.event_score import EventTypeScore, score_event_type


@dataclass(frozen=True)
class PatientPairScore:
    seed_patient_id: PatientId
    candidate_patient_id: PatientId
    scores: ComponentScores
    event_distance: float
    condition_score: Optional[EventTypeScore] = None
    procedure_score: Optional[EventTypeScore] = None


def score_patient_pair(
    seed_patient: Patient,
    candidate_patient: Patient,
    condition_information_content: InformationContentModel,
    procedure_information_content: InformationContentModel,
    condition_distance: ConceptDistanceModel,
    procedure_distance: ConceptDistanceModel,
    config: SimilarityConfig,
) -> PatientPairScore:
    config.validate()

    if not seed_patient.condition_events and not seed_patient.procedure_events:
        raise ValueError(
            f"Seed patient {seed_patient.patient_id} has no retained condition "
            "or procedure events."
        )

    matcher = AssignmentMatcher(config)

    condition_score = None
    procedure_score = None

    active_event_distances: list[tuple[float, float]] = []

    if seed_patient.condition_events and config.scoring.condition_weight > 0.0:
        condition_score = score_event_type(
            event_type="C",
            seed_patient=seed_patient,
            candidate_patient=candidate_patient,
            seed_events=seed_patient.condition_events,
            candidate_events=candidate_patient.condition_events,
            information_content=condition_information_content,
            concept_distance=condition_distance,
            matcher=matcher,
            config=config,
        )

        active_event_distances.append(
            (config.scoring.condition_weight, condition_score.distance)
        )

    if seed_patient.procedure_events and config.scoring.procedure_weight > 0.0:
        procedure_score = score_event_type(
            event_type="P",
            seed_patient=seed_patient,
            candidate_patient=candidate_patient,
            seed_events=seed_patient.procedure_events,
            candidate_events=candidate_patient.procedure_events,
            information_content=procedure_information_content,
            concept_distance=procedure_distance,
            matcher=matcher,
            config=config,
        )

        active_event_distances.append(
            (config.scoring.procedure_weight, procedure_score.distance)
        )

    if not active_event_distances:
        raise ValueError(
            "No active event modalities to score. Check seed events and "
            "condition/procedure weights."
        )

    event_distance = _weighted_average(active_event_distances)

    active_temporal_penalties = []
    active_sequence_penalties = []

    if condition_score is not None:
        active_temporal_penalties.append(
            (config.scoring.condition_weight, condition_score.temporal_penalty)
        )
        active_sequence_penalties.append(
            (config.scoring.condition_weight, condition_score.sequence_penalty)
        )

    if procedure_score is not None:
        active_temporal_penalties.append(
            (config.scoring.procedure_weight, procedure_score.temporal_penalty)
        )
        active_sequence_penalties.append(
            (config.scoring.procedure_weight, procedure_score.sequence_penalty)
        )

    temporal_penalty = _weighted_average(active_temporal_penalties)
    sequence_penalty = _weighted_average(active_sequence_penalties)

    age_penalty = None
    final_distance = event_distance

    if config.scoring.age_weight > 0.0:
        age_penalty = patient_age_penalty(
            seed_patient=seed_patient,
            candidate_patient=candidate_patient,
            age_scale_years=config.scoring.age_scale_years,
        )

        final_distance = (
            (1.0 - config.scoring.age_weight) * event_distance
            + config.scoring.age_weight * age_penalty
        )

    scores = ComponentScores(
        final_distance=final_distance,
        condition_distance=condition_score.distance if condition_score else None,
        procedure_distance=procedure_score.distance if procedure_score else None,
        age_penalty=age_penalty,
        temporal_penalty=temporal_penalty,
        sequence_penalty=sequence_penalty,
    )

    return PatientPairScore(
        seed_patient_id=seed_patient.patient_id,
        candidate_patient_id=candidate_patient.patient_id,
        scores=scores,
        event_distance=event_distance,
        condition_score=condition_score,
        procedure_score=procedure_score,
    )


def _weighted_average(weighted_values: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for weight, _value in weighted_values)

    if total_weight <= 0.0:
        raise ValueError("At least one active event modality weight must be positive.")

    return sum(weight * value for weight, value in weighted_values) / total_weight