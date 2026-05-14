from __future__ import annotations

from patient_similarity.domain import Patient, PatientEvent
from patient_similarity.ontology import Ontology


def normalize_patient_event_codes(
    patient: Patient,
    ontology: Ontology,
) -> tuple[Patient, int]:
    normalized_events = []
    dropped_empty_codes = 0

    for event in patient.events:
        normalized_code = ontology.normalize_code(event.code)

        if normalized_code is None:
            dropped_empty_codes += 1
            continue

        normalized_events.append(
            PatientEvent(
                event_type=event.event_type,
                code=normalized_code,
                date=event.date,
            )
        )

    return patient.with_events(normalized_events), dropped_empty_codes