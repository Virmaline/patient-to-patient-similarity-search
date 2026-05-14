from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

from patient_similarity.config.schema import (
    DistanceConfig,
    EventWeightingConfig,
    MatchingConfig,
    OutputConfig,
    PreprocessingConfig,
    ScoringConfig,
    SimilarityConfig,
    update_config_from_dict,
)


def default_config() -> SimilarityConfig:
    config = SimilarityConfig(
        preprocessing=PreprocessingConfig(),
        distance=DistanceConfig(),
        matching=MatchingConfig(),
        event_weighting=EventWeightingConfig(),
        scoring=ScoringConfig(),
        output=OutputConfig(),
    )
    config.validate()
    return config


def load_config_json(path: Optional[str | Path]) -> SimilarityConfig:
    config = default_config()

    if path is None:
        return config

    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        overrides = json.load(f)

    if not isinstance(overrides, dict):
        raise ValueError("Config JSON must contain a top-level object.")

    return update_config_from_dict(
        config=copy.deepcopy(config),
        values=overrides,
    )