from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from patient_similarity.config import EventWeightingConfig, SimilarityConfig
from patient_similarity.distance import ConceptDistanceModel
from patient_similarity.domain import PatientEvent
from patient_similarity.weighting.base import get_event_weighting_config


@dataclass(frozen=True)
class SemanticSupportResult:
    raw_support: float
    transformed_support: float
    multiplier: float


def compute_condition_semantic_support(
    event_index: int,
    events: Sequence[PatientEvent],
    concept_distance: ConceptDistanceModel,
    config: SimilarityConfig | EventWeightingConfig,
) -> SemanticSupportResult:
    weighting_config = get_event_weighting_config(config)

    event = events[event_index]

    if event.event_type != "C":
        return SemanticSupportResult(
            raw_support=0.0,
            transformed_support=0.0,
            multiplier=1.0,
        )

    if weighting_config.semantic_support_strength == 0.0:
        return SemanticSupportResult(
            raw_support=0.0,
            transformed_support=0.0,
            multiplier=1.0,
        )

    other_condition_events = [
        other_event
        for other_index, other_event in enumerate(events)
        if other_index != event_index and other_event.event_type == "C"
    ]

    if not other_condition_events:
        return SemanticSupportResult(
            raw_support=0.0,
            transformed_support=0.0,
            multiplier=1.0,
        )

    raw_support = max(
        concept_distance.similarity(event.code, other_event.code)
        for other_event in other_condition_events
    )

    threshold = weighting_config.semantic_support_threshold

    transformed_support = max(0.0, raw_support - threshold) / (1.0 - threshold)

    multiplier = min(
        1.0 + weighting_config.semantic_support_strength * transformed_support,
        weighting_config.semantic_support_max_multiplier,
    )

    return SemanticSupportResult(
        raw_support=raw_support,
        transformed_support=transformed_support,
        multiplier=multiplier,
    )