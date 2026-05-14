from __future__ import annotations

from abc import ABC, abstractmethod


class ConceptDistanceModel(ABC):
    @abstractmethod
    def similarity(self, code_a: object, code_b: object) -> float:
        raise NotImplementedError

    @abstractmethod
    def distance(self, code_a: object, code_b: object) -> float:
        raise NotImplementedError