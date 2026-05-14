from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from patient_similarity.domain.events import PatientEvent
from patient_similarity.domain.patients import PatientId


@dataclass(frozen=True)
class MatchedEvent:
    seed_event: PatientEvent
    candidate_event: Optional[PatientEvent]
    distance: float
    weight: float = 1.0

    semantic_distance: Optional[float] = None
    temporal_penalty: float = 0.0
    sequence_penalty: float = 0.0
    temporal_cost: float = 0.0
    sequence_cost: float = 0.0

    @property
    def is_unmatched(self) -> bool:
        return self.candidate_event is None

    @property
    def weighted_cost(self) -> float:
        return self.distance * self.weight

    @property
    def weighted_temporal_cost(self) -> float:
        return self.temporal_cost * self.weight

    @property
    def weighted_sequence_cost(self) -> float:
        return self.sequence_cost * self.weight


@dataclass(frozen=True)
class MatchResult:
    distance: float
    matches: Tuple[MatchedEvent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "matches", tuple(self.matches))

    @property
    def unmatched_seed_events(self) -> Tuple[PatientEvent, ...]:
        return tuple(
            match.seed_event
            for match in self.matches
            if match.is_unmatched
        )

    @property
    def total_weight(self) -> float:
        return sum(match.weight for match in self.matches)

    @property
    def temporal_penalty(self) -> float:
        if self.total_weight <= 0.0:
            return 0.0

        return sum(match.weighted_temporal_cost for match in self.matches) / self.total_weight

    @property
    def sequence_penalty(self) -> float:
        if self.total_weight <= 0.0:
            return 0.0

        return sum(match.weighted_sequence_cost for match in self.matches) / self.total_weight
    

@dataclass(frozen=True)
class ComponentScores:
    final_distance: float
    condition_distance: Optional[float] = None
    procedure_distance: Optional[float] = None
    age_penalty: Optional[float] = None
    temporal_penalty: Optional[float] = None
    sequence_penalty: Optional[float] = None


@dataclass(frozen=True)
class RankingResult:
    rank: int
    patient_id: PatientId
    scores: ComponentScores