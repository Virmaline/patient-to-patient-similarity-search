from __future__ import annotations

from patient_similarity.config import DistanceConfig, SimilarityConfig
from patient_similarity.distance.base import ConceptDistanceModel
from patient_similarity.distance.information_content import InformationContentModel
from patient_similarity.ontology import Ontology


class LinConceptDistanceModel(ConceptDistanceModel):
    def __init__(
        self,
        ontology: Ontology,
        information_content: InformationContentModel,
        config: SimilarityConfig | DistanceConfig,
    ):
        self.ontology = ontology
        self.information_content = information_content
        self.config = _get_distance_config(config)
        self.config.validate()

    def mica(self, code_a: object, code_b: object) -> str:
        """
        Return the most informative common ancestor.

        This method is intentionally strict: both concepts must be known.
        """
        code_a = self.ontology.check_concept(code_a)
        code_b = self.ontology.check_concept(code_b)

        common_ancestors = self.ontology.common_ancestors(code_a, code_b)

        if not common_ancestors:
            raise ValueError(f"No common ancestors found for {code_a!r} and {code_b!r}")

        return max(common_ancestors, key=self.information_content.ic)

    def similarity(self, code_a: object, code_b: object) -> float:
        """
        Return Lin similarity in the range [0.0, 1.0].

        Unknown concepts return 0.0 similarity.
        """
        normalized_a = self.ontology.normalize_code(code_a)
        normalized_b = self.ontology.normalize_code(code_b)

        if normalized_a is None or normalized_b is None:
            return 0.0

        if normalized_a == normalized_b:
            if self.ontology.has_concept(normalized_a):
                return 1.0
            return 0.0

        if not self.ontology.has_concept(normalized_a):
            return 0.0

        if not self.ontology.has_concept(normalized_b):
            return 0.0

        mica = self.mica(normalized_a, normalized_b)

        denominator = (
            self.information_content.ic(normalized_a)
            + self.information_content.ic(normalized_b)
        )

        if denominator <= 0.0:
            return 0.0

        lin_value = (2.0 * self.information_content.ic(mica)) / denominator

        return _clamp(lin_value, lower=0.0, upper=1.0)

    def distance(self, code_a: object, code_b: object) -> float:
        """
        Return Lin distance as 1.0 - similarity.

        Unknown concepts return config.distance.unknown_distance.
        """
        normalized_a = self.ontology.normalize_code(code_a)
        normalized_b = self.ontology.normalize_code(code_b)

        if normalized_a is None or normalized_b is None:
            return self.config.unknown_distance

        if not self.ontology.has_concept(normalized_a):
            return self.config.unknown_distance

        if not self.ontology.has_concept(normalized_b):
            return self.config.unknown_distance

        if normalized_a == normalized_b:
            return 0.0

        return 1.0 - self.similarity(normalized_a, normalized_b)


def _get_distance_config(
    config: SimilarityConfig | DistanceConfig,
) -> DistanceConfig:
    if isinstance(config, DistanceConfig):
        return config

    return config.distance


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))