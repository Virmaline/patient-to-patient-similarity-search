from __future__ import annotations

from patient_similarity.domain import Patient, PatientEvent
from patient_similarity.ontology import Ontology


def prune_hierarchical_patient_events(
    patient: Patient,
    ontology: Ontology,
) -> tuple[Patient, int]:
    """
    Remove broader concepts when a more specific concept is present
    for the same patient and same event type.

    Conditions and procedures are pruned separately.
    Unknown concepts are retained here; unknown handling belongs to the
    preprocessing pipeline's unknown_code_policy step.
    """
    retained_events = []
    dropped_count = 0

    for event_type in ("C", "P"):
        event_group = [
            event
            for event in patient.events
            if event.event_type == event_type
        ]

        retained_group, dropped_group_count = _prune_event_group(
            events=event_group,
            ontology=ontology,
        )

        retained_events.extend(retained_group)
        dropped_count += dropped_group_count

    retained_events = sorted(
        retained_events,
        key=lambda event: (event.date, event.event_type, event.code),
    )

    return patient.with_events(retained_events), dropped_count


def _prune_event_group(
    events: list[PatientEvent],
    ontology: Ontology,
) -> tuple[list[PatientEvent], int]:
    known_events = [
        event
        for event in events
        if ontology.has_concept(event.code)
    ]

    unknown_events = [
        event
        for event in events
        if not ontology.has_concept(event.code)
    ]

    dropped_codes = set()

    for broader_event in known_events:
        for narrower_event in known_events:
            if broader_event.code == narrower_event.code:
                continue

            if ontology.subsumes(
                broader_code=broader_event.code,
                narrower_code=narrower_event.code,
            ):
                dropped_codes.add(broader_event.code)
                break

    retained_known_events = [
        event
        for event in known_events
        if event.code not in dropped_codes
    ]

    return retained_known_events + unknown_events, len(dropped_codes)