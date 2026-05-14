from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from patient_similarity.config import SimilarityConfig
from patient_similarity.distance import ConceptDistanceModel
from patient_similarity.domain import MatchResult, Patient, PatientEvent


class EventMatcher(ABC):
    @abstractmethod
    def match(
        self,
        seed_patient: Patient,
        candidate_patient: Patient,
        seed_events: Sequence[PatientEvent],
        candidate_events: Sequence[PatientEvent],
        concept_distance: ConceptDistanceModel,
        seed_event_weights: Sequence[float],
    ) -> MatchResult:
        raise NotImplementedError


def get_matching_config(config: SimilarityConfig):
    return config.matching


def get_scoring_config(config: SimilarityConfig):
    return config.scoring