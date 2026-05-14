from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from patient_similarity.domain import Patient, PatientEvent


@dataclass(frozen=True)
class EventFeatures:
    event_index: int
    event: PatientEvent
    event_age_years: float
    sequence_position: float


def build_event_features(
    patient: Patient,
    selected_events: Sequence[PatientEvent],
) -> tuple[EventFeatures, ...]:
    """
    Derive age-at-event and normalized sequence position.

    Sequence position is computed over the patient's full retained event list,
    not only over the selected condition/procedure subset.
    """
    selected_events = tuple(selected_events)

    if not selected_events:
        return tuple()

    sequence_positions = _compute_sequence_positions(patient.events)

    fallback_positions = _compute_sequence_positions(selected_events)

    features = []

    for event_index, event in enumerate(selected_events):
        event_age_years = _years_between(
            start=patient.date_of_birth,
            end=event.date,
        )

        sequence_position = sequence_positions.get(
            id(event),
            fallback_positions.get(id(event), 0.0),
        )

        features.append(
            EventFeatures(
                event_index=event_index,
                event=event,
                event_age_years=event_age_years,
                sequence_position=sequence_position,
            )
        )

    return tuple(features)


def _compute_sequence_positions(
    events: Sequence[PatientEvent],
) -> dict[int, float]:
    events = tuple(events)

    if not events:
        return {}

    if len(events) == 1:
        return {id(events[0]): 0.0}

    sorted_events = sorted(
        enumerate(events),
        key=lambda item: (item[1].date, item[0]),
    )

    denominator = len(sorted_events) - 1

    return {
        id(event): sorted_index / denominator
        for sorted_index, (_original_index, event) in enumerate(sorted_events)
    }


def _years_between(start, end) -> float:
    return (end - start).days / 365.25