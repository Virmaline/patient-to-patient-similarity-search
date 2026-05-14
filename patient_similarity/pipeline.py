from __future__ import annotations

from pathlib import Path
from typing import Optional

from patient_similarity.config import load_config_json
from patient_similarity.io import load_patients_json, write_ranking_results_json
from patient_similarity.ontology import SnomedOntology
from patient_similarity.ranking import RankingRunResult, rank_patients


def run_ranking_pipeline(
    patients_json_path: str | Path,
    snomed_relationships_path: str | Path,
    seed_patient_id: str | int,
    output_path: str | Path,
    config_path: Optional[str | Path] = None,
    include_pair_scores: bool = False,
) -> RankingRunResult:
    """
    Run the full file-based patient similarity ranking pipeline.

    This function:
    - loads config defaults plus optional JSON overrides
    - loads patient cohort JSON
    - loads the SNOMED CT relationship snapshot
    - ranks candidates against the seed patient
    - writes ranking output JSON
    - returns the full RankingRunResult for inspection

    It intentionally does not print anything.
    """
    config = load_config_json(config_path)

    patients = load_patients_json(patients_json_path)
    ontology = SnomedOntology(snomed_relationships_path)

    ranking_run = rank_patients(
        patients=patients,
        seed_patient_id=seed_patient_id,
        ontology=ontology,
        config=config,
        include_pair_scores=include_pair_scores,
    )

    write_ranking_results_json(
        results=ranking_run.results,
        path=output_path,
        include_component_scores=config.output.include_component_scores,
    )

    return ranking_run