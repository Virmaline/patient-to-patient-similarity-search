from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Tuple, Union

from patient_similarity.domain.events import PatientEvent


PatientId = Union[str, int]


@dataclass(frozen=True)
class Patient:
    patient_id: PatientId
    date_of_birth: date
    events: Tuple[PatientEvent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))

    @property
    def condition_events(self) -> Tuple[PatientEvent, ...]:
        return tuple(event for event in self.events if event.is_condition)

    @property
    def procedure_events(self) -> Tuple[PatientEvent, ...]:
        return tuple(event for event in self.events if event.is_procedure)

    def with_events(self, events: Iterable[PatientEvent]) -> "Patient":
        return Patient(
            patient_id=self.patient_id,
            date_of_birth=self.date_of_birth,
            events=tuple(events),
        )