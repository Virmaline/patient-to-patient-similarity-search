from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from patient_similarity.domain import ComponentScores, RankingResult


def write_ranking_results_json(
    results: Iterable[RankingResult],
    path: str | Path,
    include_component_scores: bool = False,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        _ranking_result_to_dict(
            result=result,
            include_component_scores=include_component_scores,
        )
        for result in results
    ]

    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _ranking_result_to_dict(
    result: RankingResult,
    include_component_scores: bool,
) -> dict:
    row = {
        "rank": result.rank,
        "patient_id": result.patient_id,
        "final_distance": result.scores.final_distance,
    }

    if include_component_scores:
        row.update(_component_scores_to_dict(result.scores))

    return row


def _component_scores_to_dict(scores: ComponentScores) -> dict:
    return {
        "condition_distance": scores.condition_distance,
        "procedure_distance": scores.procedure_distance,
        "age_penalty": scores.age_penalty,
        "temporal_penalty": scores.temporal_penalty,
        "sequence_penalty": scores.sequence_penalty,
    }