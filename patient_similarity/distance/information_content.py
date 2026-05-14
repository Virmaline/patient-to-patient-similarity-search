from __future__ import annotations

from collections import Counter
from math import log
from typing import Iterable, Mapping, Optional

from patient_similarity.domain import Patient
from patient_similarity.ontology import Ontology


class InformationContentModel:
    """
    Fits patient-level information content for one event type.

    A concept contributes at most once per patient. Each retained concept is
    expanded to include all of its ontology ancestors before patient-level
    prevalence is counted.
    """

    def __init__(self, ontology: Ontology):
        self.ontology = ontology
        self._ic_by_concept: Optional[dict[str, float]] = None
        self._count_by_concept: Optional[dict[str, int]] = None
        self._patient_count: Optional[int] = None
        self._event_type: Optional[str] = None

    @property
    def is_fitted(self) -> bool:
        return self._ic_by_concept is not None

    @property
    def patient_count(self) -> int:
        self._require_fitted()
        assert self._patient_count is not None
        return self._patient_count

    @property
    def event_type(self) -> str:
        self._require_fitted()
        assert self._event_type is not None
        return self._event_type

    @property
    def counts(self) -> Mapping[str, int]:
        self._require_fitted()
        assert self._count_by_concept is not None
        return self._count_by_concept

    def fit_from_patients(
        self,
        patients: Iterable[Patient],
        event_type: str,
    ) -> "InformationContentModel":
        patient_to_concepts = {}

        for patient in patients:
            concepts = {
                self.ontology.normalize_code(event.code)
                for event in patient.events
                if event.event_type == event_type
            }

            known_concepts = {
                concept
                for concept in concepts
                if concept is not None and self.ontology.has_concept(concept)
            }

            if known_concepts:
                patient_to_concepts[patient.patient_id] = known_concepts

        return self.fit_from_patient_concepts(
            patient_to_concepts=patient_to_concepts,
            event_type=event_type,
        )

    def fit_from_patient_concepts(
        self,
        patient_to_concepts: Mapping[object, Iterable[str]],
        event_type: str,
    ) -> "InformationContentModel":
        concept_counts: Counter[str] = Counter()
        patient_count = 0

        for _patient_id, concepts in patient_to_concepts.items():
            known_concepts = {
                self.ontology.normalize_code(concept)
                for concept in concepts
            }

            known_concepts = {
                concept
                for concept in known_concepts
                if concept is not None and self.ontology.has_concept(concept)
            }

            if not known_concepts:
                continue

            patient_count += 1

            expanded_concepts = set()
            for concept in known_concepts:
                expanded_concepts.update(self.ontology.ancestors(concept))

            for concept in expanded_concepts:
                concept_counts[concept] += 1

        if patient_count == 0:
            raise ValueError(
                f"No valid retained events found for IC fitting: event_type={event_type!r}"
            )

        ic_by_concept = {}

        for concept in self.ontology.nodes:
            count = concept_counts.get(concept, 0)
            probability = (count + 1) / (patient_count + 1)
            ic_by_concept[concept] = -log(probability)

        self._ic_by_concept = ic_by_concept
        self._count_by_concept = dict(concept_counts)
        self._patient_count = patient_count
        self._event_type = event_type

        return self

    def ic(self, concept_id: object) -> float:
        self._require_fitted()

        concept_id = self.ontology.check_concept(concept_id)

        assert self._ic_by_concept is not None
        return self._ic_by_concept[concept_id]

    def count(self, concept_id: object) -> int:
        self._require_fitted()

        concept_id = self.ontology.check_concept(concept_id)

        assert self._count_by_concept is not None
        return self._count_by_concept.get(concept_id, 0)

    def probability(self, concept_id: object) -> float:
        self._require_fitted()

        concept_id = self.ontology.check_concept(concept_id)

        return (self.count(concept_id) + 1) / (self.patient_count + 1)

    def _require_fitted(self) -> None:
        if self._ic_by_concept is None:
            raise ValueError("InformationContentModel has not been fitted.")