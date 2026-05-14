from __future__ import annotations

from statistics import median

from patient_similarity.domain import Patient, PatientEvent


def event_age_years(patient: Patient, event: PatientEvent) -> float:
    age_years = (event.date - patient.date_of_birth).days / 365.25

    if age_years < 0.0:
        raise ValueError(
            f"Patient {patient.patient_id} has an event before date_of_birth: "
            f"event_date={event.date}, date_of_birth={patient.date_of_birth}"
        )

    return age_years


def median_event_age_years(patient: Patient) -> float:
    if not patient.events:
        raise ValueError(
            f"Patient {patient.patient_id} has no retained events for median age."
        )

    return float(
        median(
            event_age_years(patient=patient, event=event)
            for event in patient.events
        )
    )


def patient_age_penalty(
    seed_patient: Patient,
    candidate_patient: Patient,
    age_scale_years: float,
) -> float:
    if age_scale_years <= 0.0:
        raise ValueError("age_scale_years must be greater than 0.0.")

    seed_median_age = median_event_age_years(seed_patient)
    candidate_median_age = median_event_age_years(candidate_patient)

    difference = abs(seed_median_age - candidate_median_age)

    if difference == 0.0:
        return 0.0

    return difference / (difference + age_scale_years)