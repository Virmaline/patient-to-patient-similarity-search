from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from patient_similarity.config import SimilarityConfig
from patient_similarity.distance import InformationContentModel, LinConceptDistanceModel
from patient_similarity.domain import ComponentScores, Patient, PatientId, RankingResult
from patient_similarity.ontology import Ontology
from patient_similarity.preprocessing import PreprocessingReport, preprocess_patients
from patient_similarity.scoring import PatientPairScore, score_patient_pair


@dataclass(frozen=True)
class RankingModelSummary:
    condition_ic_patient_count: int
    procedure_ic_patient_count: int


@dataclass(frozen=True)
class RankingRunResult:
    seed_patient_id: PatientId
    results: Tuple[RankingResult, ...]
    preprocessing_report: PreprocessingReport
    model_summary: RankingModelSummary
    pair_scores: Tuple[PatientPairScore, ...] = tuple()
    skipped_empty_candidate_count: int = 0

def rank_patients(
    patients: Iterable[Patient],
    seed_patient_id: PatientId,
    ontology: Ontology,
    config: SimilarityConfig,
    include_pair_scores: bool = False,
) -> RankingRunResult:
    """
    Rank all candidate patients against one seed patient.

    This function owns:
    - preprocessing
    - IC fitting
    - Lin distance model construction
    - pair scoring
    - sorting and rank assignment

    It does not read input files or write output files.
    """
    config.validate()

    retained_patients, preprocessing_report = preprocess_patients(
        patients=patients,
        ontology=ontology,
        config=config,
    )

    seed_patient = _find_seed_patient(
        patients=retained_patients,
        seed_patient_id=seed_patient_id,
    )

    if not seed_patient.condition_events and not seed_patient.procedure_events:
        raise ValueError(
            f"Seed patient {seed_patient.patient_id} has no retained condition "
            "or procedure events after preprocessing."
        )

    condition_ic = InformationContentModel(ontology).fit_from_patients(
        patients=retained_patients,
        event_type="C",
    )

    procedure_ic = InformationContentModel(ontology).fit_from_patients(
        patients=retained_patients,
        event_type="P",
    )

    condition_distance = LinConceptDistanceModel(
        ontology=ontology,
        information_content=condition_ic,
        config=config,
    )

    procedure_distance = LinConceptDistanceModel(
        ontology=ontology,
        information_content=procedure_ic,
        config=config,
    )

    pair_scores = []
    skipped_empty_candidate_count = 0

    for candidate_patient in retained_patients:
        if _same_patient_id(candidate_patient.patient_id, seed_patient.patient_id):
            continue

        if not candidate_patient.events:
            skipped_empty_candidate_count += 1
            continue

        pair_score = score_patient_pair(
            seed_patient=seed_patient,
            candidate_patient=candidate_patient,
            condition_information_content=condition_ic,
            procedure_information_content=procedure_ic,
            condition_distance=condition_distance,
            procedure_distance=procedure_distance,
            config=config,
        )

        pair_scores.append(pair_score)

    pair_scores.sort(
        key=lambda pair_score: (
            pair_score.scores.final_distance,
            str(pair_score.candidate_patient_id),
        )
    )

    if config.output.max_results is not None:
        pair_scores = pair_scores[: config.output.max_results]

    ranking_results = tuple(
        RankingResult(
            rank=rank,
            patient_id=pair_score.candidate_patient_id,
            scores=pair_score.scores,
        )
        for rank, pair_score in enumerate(pair_scores, start=1)
    )

    return RankingRunResult(
        seed_patient_id=seed_patient.patient_id,
        results=ranking_results,
        preprocessing_report=preprocessing_report,
        model_summary=RankingModelSummary(
            condition_ic_patient_count=condition_ic.patient_count,
            procedure_ic_patient_count=procedure_ic.patient_count,
        ),
        pair_scores=tuple(pair_scores) if include_pair_scores else tuple(),
        skipped_empty_candidate_count=skipped_empty_candidate_count,
    )


def _find_seed_patient(
    patients: Iterable[Patient],
    seed_patient_id: PatientId,
) -> Patient:
    matches = [
        patient
        for patient in patients
        if _same_patient_id(patient.patient_id, seed_patient_id)
    ]

    if not matches:
        raise ValueError(f"Seed patient not found: {seed_patient_id!r}")

    if len(matches) > 1:
        matching_ids = [patient.patient_id for patient in matches]
        raise ValueError(
            f"Seed patient id is ambiguous: {seed_patient_id!r}. "
            f"Matching patient ids: {matching_ids!r}"
        )

    return matches[0]


def _same_patient_id(left: object, right: object) -> bool:
    return left == right or str(left) == str(right)