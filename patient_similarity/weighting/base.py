from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from patient_similarity.config import EventWeightingConfig, SimilarityConfig
from patient_similarity.domain import PatientEvent


@dataclass(frozen=True)
class EventWeightDetails:
    event_index: int
    event: PatientEvent
    rarity_weight: float
    raw_semantic_support: float
    transformed_semantic_support: float
    semantic_support_multiplier: float
    final_weight: float


@dataclass(frozen=True)
class EventWeightingResult:
    details: Tuple[EventWeightDetails, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", tuple(self.details))

    @property
    def weights(self) -> tuple[float, ...]:
        return tuple(detail.final_weight for detail in self.details)

    @property
    def events(self) -> tuple[PatientEvent, ...]:
        return tuple(detail.event for detail in self.details)

    def as_debug_rows(self) -> list[dict]:
        return [
            {
                "event_index": detail.event_index,
                "event_type": detail.event.event_type,
                "code": detail.event.code,
                "date": detail.event.date.isoformat(),
                "rarity_weight": detail.rarity_weight,
                "raw_semantic_support": detail.raw_semantic_support,
                "transformed_semantic_support": detail.transformed_semantic_support,
                "semantic_support_multiplier": detail.semantic_support_multiplier,
                "final_weight": detail.final_weight,
            }
            for detail in self.details
        ]


def get_event_weighting_config(
    config: SimilarityConfig | EventWeightingConfig,
) -> EventWeightingConfig:
    if isinstance(config, EventWeightingConfig):
        return config

    return config.event_weighting