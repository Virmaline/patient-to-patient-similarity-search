from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Literal, Optional


UnknownCodePolicy = Literal["drop", "keep", "error"]


@dataclass
class PreprocessingConfig:
    hierarchical_pruning: bool = True
    deduplicate_exact_codes: bool = True
    unknown_code_policy: UnknownCodePolicy = "drop"

    def validate(self) -> None:
        if self.unknown_code_policy not in {"drop", "keep", "error"}:
            raise ValueError(
                "preprocessing.unknown_code_policy must be one of: "
                "'drop', 'keep', 'error'."
            )


@dataclass
class DistanceConfig:
    method: str = "lin"
    unknown_distance: float = 1.0

    def validate(self) -> None:
        if self.method != "lin":
            raise ValueError("distance.method currently only supports 'lin'.")

        if self.unknown_distance < 0.0:
            raise ValueError("distance.unknown_distance cannot be negative.")


@dataclass
class MatchingConfig:
    method: str = "assignment"
    unmatched_penalty: float = 1.0
    semantic_threshold: Optional[float] = 0.30
    
    def validate(self) -> None:
        if self.method != "assignment":
            raise ValueError("matching.method currently only supports 'assignment'.")

        if self.unmatched_penalty < 0.0:
            raise ValueError("matching.unmatched_penalty cannot be negative.")

        if self.semantic_threshold is not None:
            if not 0.0 <= self.semantic_threshold <= 1.0:
                raise ValueError(
                    "matching.semantic_threshold must be between 0.0 and 1.0, "
                    "or null."
                )


@dataclass
class EventWeightingConfig:
    rarity_strength: float = 6.0
    semantic_support_threshold: float = 0.30
    semantic_support_strength: float = 1.50
    semantic_support_max_multiplier: float = 1.75

    def validate(self) -> None:
        if self.rarity_strength < 0.0:
            raise ValueError("event_weighting.rarity_strength cannot be negative.")

        if not 0.0 <= self.semantic_support_threshold < 1.0:
            raise ValueError(
                "event_weighting.semantic_support_threshold must be in [0.0, 1.0)."
            )

        if self.semantic_support_strength < 0.0:
            raise ValueError(
                "event_weighting.semantic_support_strength cannot be negative."
            )

        if self.semantic_support_max_multiplier < 1.0:
            raise ValueError(
                "event_weighting.semantic_support_max_multiplier must be at least 1.0."
            )


@dataclass
class ScoringConfig:
    condition_weight: float = 0.75
    procedure_weight: float = 0.25

    age_weight: float = 0.40
    age_scale_years: float = 20.0

    temporal_weight: float = 0.05
    sequence_weight: float = 0.05
    match_age_scale_years: float = 10.0
    sequence_scale: float = 0.25

    def validate(self) -> None:
        weights = {
            "condition_weight": self.condition_weight,
            "procedure_weight": self.procedure_weight,
            "age_weight": self.age_weight,
            "temporal_weight": self.temporal_weight,
            "sequence_weight": self.sequence_weight,
        }

        for name, value in weights.items():
            if value < 0.0:
                raise ValueError(f"scoring.{name} cannot be negative.")

        scales = {
            "age_scale_years": self.age_scale_years,
            "match_age_scale_years": self.match_age_scale_years,
            "sequence_scale": self.sequence_scale,
        }

        for name, value in scales.items():
            if value <= 0.0:
                raise ValueError(f"scoring.{name} must be greater than 0.0.")


@dataclass
class OutputConfig:
    include_component_scores: bool = False
    include_matches: bool = False
    max_results: Optional[int] = None

    def validate(self) -> None:
        if self.max_results is not None and self.max_results <= 0:
            raise ValueError("output.max_results must be positive, or null.")


@dataclass
class SimilarityConfig:
    preprocessing: PreprocessingConfig
    distance: DistanceConfig
    matching: MatchingConfig
    event_weighting: EventWeightingConfig
    scoring: ScoringConfig
    output: OutputConfig

    def validate(self) -> None:
        self.preprocessing.validate()
        self.distance.validate()
        self.matching.validate()
        self.event_weighting.validate()
        self.scoring.validate()
        self.output.validate()


def update_config_from_dict(config: SimilarityConfig, values: dict[str, Any]) -> SimilarityConfig:
    _update_dataclass_from_dict(config, values, path="config")
    config.validate()
    return config


def _update_dataclass_from_dict(instance: object, values: dict[str, Any], path: str) -> None:
    if not isinstance(values, dict):
        raise ValueError(f"{path} must be an object.")

    field_names = {field.name for field in fields(instance)}

    for key, value in values.items():
        if key not in field_names:
            raise ValueError(f"Unknown config field: {path}.{key}")

        current_value = getattr(instance, key)

        if is_dataclass(current_value):
            _update_dataclass_from_dict(
                instance=current_value,
                values=value,
                path=f"{path}.{key}",
            )
        else:
            setattr(instance, key, value)