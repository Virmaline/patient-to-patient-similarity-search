from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


EventType = Literal["C", "P"]


@dataclass(frozen=True)
class PatientEvent:
    event_type: EventType
    code: str
    date: date

    def __post_init__(self) -> None:
        if self.event_type not in {"C", "P"}:
            raise ValueError(f"Unsupported event type: {self.event_type}")

        normalized_code = str(self.code).strip()
        if not normalized_code:
            raise ValueError("Event code cannot be empty.")

        object.__setattr__(self, "code", normalized_code)

    @property
    def is_condition(self) -> bool:
        return self.event_type == "C"

    @property
    def is_procedure(self) -> bool:
        return self.event_type == "P"