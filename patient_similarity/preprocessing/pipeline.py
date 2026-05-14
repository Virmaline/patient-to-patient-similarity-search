from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from patient_similarity.config import PreprocessingConfig, SimilarityConfig
from patient_similarity.domain import Patient, PatientEvent
from patient_similarity.ontology import Ontology
from patient_similarity.preprocessing.deduplicate import deduplicate_exact_patient_events
from patient_similarity.preprocessing.hierarchy_pruning import prune_hierarchical_patient_events
from patient_similarity.preprocessing.normalize import normalize_patient_event_codes


@dataclass(frozen=True)
class PreprocessingReport:
    input_patient_count: int
    output_patient_count: int
    input_event_count: int
    output_event_count: int
    empty_code_dropped: int = 0
    unknown_dropped: int = 0
    unknown_kept: int = 0
    duplicate_dropped: int = 0
    hierarchy_pruned: int = 0
    patients_without_events: int = 0
    unknown_codes: Mapping[str, int] = field(default_factory=dict)

    @property
    def total_dropped(self) -> int:
        return self.input_event_count - self.output_event_count


def preprocess_patients(
    patients: Iterable[Patient],
    ontology: Ontology,
    config: SimilarityConfig | PreprocessingConfig,
) -> tuple[tuple[Patient, ...], PreprocessingReport]:
    preprocessing_config = _get_preprocessing_config(config)
    preprocessing_config.validate()

    patients = tuple(patients)

    input_event_count = sum(len(patient.events) for patient in patients)

    retained_patients = []

    empty_code_dropped = 0
    unknown_dropped = 0
    unknown_kept = 0
    duplicate_dropped = 0
    hierarchy_pruned = 0
    unknown_codes: Counter[str] = Counter()

    for patient in patients:
        current_patient, dropped_empty = normalize_patient_event_codes(
            patient=patient,
            ontology=ontology,
        )
        empty_code_dropped += dropped_empty

        current_patient, patient_unknown_dropped, patient_unknown_kept, patient_unknown_codes = (
            _apply_unknown_code_policy(
                patient=current_patient,
                ontology=ontology,
                unknown_code_policy=preprocessing_config.unknown_code_policy,
            )
        )

        unknown_dropped += patient_unknown_dropped
        unknown_kept += patient_unknown_kept
        unknown_codes.update(patient_unknown_codes)

        if preprocessing_config.deduplicate_exact_codes:
            current_patient, patient_duplicate_dropped = deduplicate_exact_patient_events(
                current_patient
            )
            duplicate_dropped += patient_duplicate_dropped

        if preprocessing_config.hierarchical_pruning:
            current_patient, patient_hierarchy_pruned = prune_hierarchical_patient_events(
                patient=current_patient,
                ontology=ontology,
            )
            hierarchy_pruned += patient_hierarchy_pruned

        retained_patients.append(current_patient)

    retained_patients = tuple(retained_patients)
    output_event_count = sum(len(patient.events) for patient in retained_patients)

    report = PreprocessingReport(
        input_patient_count=len(patients),
        output_patient_count=len(retained_patients),
        input_event_count=input_event_count,
        output_event_count=output_event_count,
        empty_code_dropped=empty_code_dropped,
        unknown_dropped=unknown_dropped,
        unknown_kept=unknown_kept,
        duplicate_dropped=duplicate_dropped,
        hierarchy_pruned=hierarchy_pruned,
        patients_without_events=sum(
            1 for patient in retained_patients if len(patient.events) == 0
        ),
        unknown_codes=dict(unknown_codes),
    )

    return retained_patients, report


def _get_preprocessing_config(
    config: SimilarityConfig | PreprocessingConfig,
) -> PreprocessingConfig:
    if isinstance(config, PreprocessingConfig):
        return config

    return config.preprocessing


def _apply_unknown_code_policy(
    patient: Patient,
    ontology: Ontology,
    unknown_code_policy: str,
) -> tuple[Patient, int, int, Counter[str]]:
    retained_events = []
    unknown_dropped = 0
    unknown_kept = 0
    unknown_codes: Counter[str] = Counter()

    for event in patient.events:
        if ontology.has_concept(event.code):
            retained_events.append(event)
            continue

        unknown_codes[event.code] += 1

        if unknown_code_policy == "drop":
            unknown_dropped += 1
            continue

        if unknown_code_policy == "keep":
            retained_events.append(event)
            unknown_kept += 1
            continue

        if unknown_code_policy == "error":
            raise ValueError(
                f"Unknown SNOMED concept for patient {patient.patient_id}: {event.code}"
            )

        raise ValueError(
            "unknown_code_policy must be one of: 'drop', 'keep', 'error'."
        )

    return patient.with_events(retained_events), unknown_dropped, unknown_kept, unknown_codes