from __future__ import annotations

from patient_similarity.domain import Patient, PatientEvent


def deduplicate_exact_patient_events(patient: Patient) -> tuple[Patient, int]:
    """
    Deduplicate exact same event type + code within one patient.

    If the same code appears multiple times for the same patient and event type,
    keep the earliest occurrence by date.
    """
    retained_by_key: dict[tuple[str, str], tuple[PatientEvent, int]] = {}
    dropped_count = 0

    for original_index, event in enumerate(patient.events):
        key = (event.event_type, event.code)
        existing = retained_by_key.get(key)

        if existing is None:
            retained_by_key[key] = (event, original_index)
            continue

        existing_event, existing_index = existing

        new_sort_key = (event.date, original_index)
        existing_sort_key = (existing_event.date, existing_index)

        if new_sort_key < existing_sort_key:
            retained_by_key[key] = (event, original_index)

        dropped_count += 1

    retained_events = sorted(
        (event for event, _index in retained_by_key.values()),
        key=lambda event: (event.date, event.event_type, event.code),
    )

    return patient.with_events(retained_events), dropped_count