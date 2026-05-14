from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from patient_similarity.domain import Patient, PatientEvent


def load_patients_json(path: str | Path) -> tuple[Patient, ...]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not isinstance(raw_data, list):
        raise ValueError("Patient JSON must contain a top-level list of patients.")

    return tuple(
        _parse_patient(raw_patient=raw_patient, row_index=row_index)
        for row_index, raw_patient in enumerate(raw_data)
    )


def _parse_patient(raw_patient: Any, row_index: int) -> Patient:
    if not isinstance(raw_patient, dict):
        raise ValueError(f"Patient at index {row_index} must be an object.")

    if "patient_id" not in raw_patient:
        raise ValueError(f"Patient at index {row_index} is missing 'patient_id'.")

    patient_id = raw_patient["patient_id"]
    date_of_birth = _parse_date_of_birth(raw_patient, row_index=row_index)

    raw_events = raw_patient.get("events")
    if not isinstance(raw_events, list):
        raise ValueError(f"Patient {patient_id} must have an 'events' list.")

    events = tuple(
        _parse_event(
            raw_event=raw_event,
            patient_id=patient_id,
            event_index=event_index,
        )
        for event_index, raw_event in enumerate(raw_events)
    )

    return Patient(
        patient_id=patient_id,
        date_of_birth=date_of_birth,
        events=events,
    )


def _parse_date_of_birth(raw_patient: dict, row_index: int) -> date:
    raw_date_of_birth = raw_patient.get("date_of_birth")

    if raw_date_of_birth is None:
        raise ValueError(
            f"Patient at index {row_index} is missing 'date_of_birth'."
        )

    try:
        return date.fromisoformat(str(raw_date_of_birth))
    except ValueError as exc:
        raise ValueError(
            f"Patient at index {row_index} has invalid date_of_birth: "
            f"{raw_date_of_birth!r}. Expected YYYY-MM-DD."
        ) from exc


def _parse_event(raw_event: Any, patient_id: object, event_index: int) -> PatientEvent:
    if not isinstance(raw_event, dict):
        raise ValueError(
            f"Event {event_index} for patient {patient_id} must be an object."
        )

    event_type = raw_event.get("type")
    if event_type not in {"C", "P"}:
        raise ValueError(
            f"Event {event_index} for patient {patient_id} has unsupported type: "
            f"{event_type!r}. Expected 'C' or 'P'."
        )

    code = raw_event.get("code")
    if code is None or not str(code).strip():
        raise ValueError(
            f"Event {event_index} for patient {patient_id} is missing 'code'."
        )

    raw_date = raw_event.get("date")
    if raw_date is None:
        raise ValueError(
            f"Event {event_index} for patient {patient_id} is missing 'date'."
        )

    try:
        event_date = date.fromisoformat(str(raw_date))
    except ValueError as exc:
        raise ValueError(
            f"Event {event_index} for patient {patient_id} has invalid date: "
            f"{raw_date!r}. Expected YYYY-MM-DD."
        ) from exc

    return PatientEvent(
        event_type=event_type,
        code=str(code).strip(),
        date=event_date,
    )