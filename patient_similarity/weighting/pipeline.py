from __future__ import annotations

from typing import Iterable

from patient_similarity.config import EventWeightingConfig, SimilarityConfig
from patient_similarity.distance import ConceptDistanceModel, InformationContentModel
from patient_similarity.domain import PatientEvent
from patient_similarity.weighting.base import EventWeightDetails, EventWeightingResult
from patient_similarity.weighting.rarity import compute_rarity_weight
from patient_similarity.weighting.semantic_support import compute_condition_semantic_support


def compute_seed_event_weights(
    events: Iterable[PatientEvent],
    information_content: InformationContentModel,
    concept_distance: ConceptDistanceModel,
    config: SimilarityConfig | EventWeightingConfig,
) -> EventWeightingResult:
    events = tuple(events)

    details = []

    for event_index, event in enumerate(events):
        rarity_weight = compute_rarity_weight(
            event=event,
            information_content=information_content,
            config=config,
        )

        semantic_support = compute_condition_semantic_support(
            event_index=event_index,
            events=events,
            concept_distance=concept_distance,
            config=config,
        )

        final_weight = rarity_weight * semantic_support.multiplier

        details.append(
            EventWeightDetails(
                event_index=event_index,
                event=event,
                rarity_weight=rarity_weight,
                raw_semantic_support=semantic_support.raw_support,
                transformed_semantic_support=semantic_support.transformed_support,
                semantic_support_multiplier=semantic_support.multiplier,
                final_weight=final_weight,
            )
        )

    return EventWeightingResult(details=tuple(details))