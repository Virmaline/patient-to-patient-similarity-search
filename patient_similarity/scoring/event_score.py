from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from patient_similarity.config import SimilarityConfig
from patient_similarity.distance import ConceptDistanceModel, InformationContentModel
from patient_similarity.domain import MatchResult, Patient, PatientEvent
from patient_similarity.matching import AssignmentMatcher
from patient_similarity.weighting import EventWeightingResult, compute_seed_event_weights


@dataclass(frozen=True)
class EventTypeScore:
    event_type: str
    distance: float
    temporal_penalty: float
    sequence_penalty: float
    match_result: MatchResult
    weighting_result: EventWeightingResult


def score_event_type(
    event_type: str,
    seed_patient: Patient,
    candidate_patient: Patient,
    seed_events: Sequence[PatientEvent],
    candidate_events: Sequence[PatientEvent],
    information_content: InformationContentModel,
    concept_distance: ConceptDistanceModel,
    matcher: AssignmentMatcher,
    config: SimilarityConfig,
) -> EventTypeScore:
    seed_events = tuple(seed_events)
    candidate_events = tuple(candidate_events)

    if not seed_events:
        raise ValueError(
            f"Seed patient {seed_patient.patient_id} has no {event_type} events."
        )

    weighting_result = compute_seed_event_weights(
        events=seed_events,
        information_content=information_content,
        concept_distance=concept_distance,
        config=config,
    )

    match_result = matcher.match(
        seed_patient=seed_patient,
        candidate_patient=candidate_patient,
        seed_events=seed_events,
        candidate_events=candidate_events,
        concept_distance=concept_distance,
        seed_event_weights=weighting_result.weights,
    )

    return EventTypeScore(
        event_type=event_type,
        distance=match_result.distance,
        temporal_penalty=match_result.temporal_penalty,
        sequence_penalty=match_result.sequence_penalty,
        match_result=match_result,
        weighting_result=weighting_result,
    )