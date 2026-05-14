from __future__ import annotations

from patient_similarity.config import EventWeightingConfig, SimilarityConfig
from patient_similarity.distance import InformationContentModel
from patient_similarity.domain import PatientEvent
from patient_similarity.weighting.base import get_event_weighting_config


def compute_rarity_weight(
    event: PatientEvent,
    information_content: InformationContentModel,
    config: SimilarityConfig | EventWeightingConfig,
) -> float:
    weighting_config = get_event_weighting_config(config)

    if weighting_config.rarity_strength == 0.0:
        return 1.0

    if not information_content.ontology.has_concept(event.code):
        return 1.0

    ic_value = information_content.ic(event.code)

    return 1.0 + weighting_config.rarity_strength * (
        ic_value / (ic_value + 1.0)
    )