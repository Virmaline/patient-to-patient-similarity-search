from __future__ import annotations

from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import DefaultDict, FrozenSet, Optional, Set

import pandas as pd

from patient_similarity.ontology.base import Ontology


class SnomedOntology(Ontology):
    IS_A_TYPE_ID = "116680003"

    def __init__(self, relationship_snapshot_path: str | Path):
        relationship_snapshot_path = Path(relationship_snapshot_path)

        if not relationship_snapshot_path.exists():
            raise FileNotFoundError(
                f"SNOMED relationship snapshot not found: {relationship_snapshot_path}"
            )

        relationships = pd.read_csv(
            relationship_snapshot_path,
            sep="\t",
            dtype=str,
            usecols=["sourceId", "destinationId", "typeId", "active"],
        )

        is_a_relationships = relationships[
            (relationships["active"] == "1")
            & (relationships["typeId"] == self.IS_A_TYPE_ID)
        ][["sourceId", "destinationId"]].drop_duplicates()

        self.parents: DefaultDict[str, Set[str]] = defaultdict(set)
        self.children: DefaultDict[str, Set[str]] = defaultdict(set)

        for child_id, parent_id in is_a_relationships.itertuples(index=False):
            self.parents[child_id].add(parent_id)
            self.children[parent_id].add(child_id)

        self.nodes: Set[str] = set(is_a_relationships["sourceId"]) | set(
            is_a_relationships["destinationId"]
        )

        self.roots: Set[str] = {
            node
            for node in self.nodes
            if node not in self.parents or not self.parents[node]
        }

    def normalize_code(self, code: object) -> Optional[str]:
        if code is None:
            return None

        if pd.isna(code):
            return None

        normalized = str(code).strip()
        if not normalized:
            return None

        if "_" in normalized:
            prefix, suffix = normalized.split("_", 1)
            if prefix in {"C", "P"}:
                normalized = suffix.strip()

        if normalized.endswith(".0"):
            normalized = normalized[:-2]

        return normalized or None

    def has_concept(self, concept_id: object) -> bool:
        normalized = self.normalize_code(concept_id)
        return normalized in self.nodes if normalized is not None else False

    def check_concept(self, concept_id: object) -> str:
        normalized = self.normalize_code(concept_id)

        if normalized is None or normalized not in self.nodes:
            raise KeyError(f"SNOMED concept not found in loaded hierarchy: {normalized}")

        return normalized

    @lru_cache(maxsize=None)
    def ancestors(self, concept_id: object) -> FrozenSet[str]:
        concept_id = self.check_concept(concept_id)

        result = {concept_id}
        stack = list(self.parents.get(concept_id, ()))

        while stack:
            parent_id = stack.pop()

            if parent_id in result:
                continue

            result.add(parent_id)
            stack.extend(self.parents.get(parent_id, ()))

        return frozenset(result)

    @lru_cache(maxsize=None)
    def ancestor_distances(self, concept_id: object) -> dict[str, int]:
        concept_id = self.check_concept(concept_id)

        distances = {concept_id: 0}
        queue = deque([concept_id])

        while queue:
            current_id = queue.popleft()

            for parent_id in self.parents.get(current_id, ()):
                new_distance = distances[current_id] + 1

                if parent_id not in distances or new_distance < distances[parent_id]:
                    distances[parent_id] = new_distance
                    queue.append(parent_id)

        return distances

    def subsumes(self, broader_code: object, narrower_code: object) -> bool:
        broader_code = self.check_concept(broader_code)
        narrower_code = self.check_concept(narrower_code)

        if broader_code == narrower_code:
            return False

        return broader_code in self.ancestors(narrower_code)

    def common_ancestors(self, code_a: object, code_b: object) -> Set[str]:
        code_a = self.check_concept(code_a)
        code_b = self.check_concept(code_b)

        return set(self.ancestors(code_a)) & set(self.ancestors(code_b))