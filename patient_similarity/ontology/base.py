from __future__ import annotations

from abc import ABC, abstractmethod
from typing import FrozenSet, Optional, Set


class Ontology(ABC):
    @abstractmethod
    def normalize_code(self, code: object) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def has_concept(self, concept_id: object) -> bool:
        raise NotImplementedError

    @abstractmethod
    def check_concept(self, concept_id: object) -> str:
        raise NotImplementedError

    @abstractmethod
    def ancestors(self, concept_id: object) -> FrozenSet[str]:
        raise NotImplementedError

    @abstractmethod
    def subsumes(self, broader_code: object, narrower_code: object) -> bool:
        raise NotImplementedError

    @abstractmethod
    def common_ancestors(self, code_a: object, code_b: object) -> Set[str]:
        raise NotImplementedError