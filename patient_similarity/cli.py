from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from patient_similarity.pipeline import run_ranking_pipeline


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    ranking_run = run_ranking_pipeline(
        patients_json_path=args.patients,
        snomed_relationships_path=args.relationships,
        seed_patient_id=args.seed_patient_id,
        output_path=args.output,
        config_path=args.config,
    )

    _print_summary(
        output_path=args.output,
        ranking_run=ranking_run,
    )


def _parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="patient-similarity",
        description=(
            "Rank candidate patients by similarity to a selected seed patient "
            "using SNOMED CT condition and procedure histories."
        ),
    )

    parser.add_argument(
        "--patients",
        required=True,
        type=Path,
        help="Path to the input patient cohort JSON file.",
    )

    parser.add_argument(
        "--relationships",
        required=True,
        type=Path,
        help="Path to the SNOMED CT RF2 relationship snapshot file.",
    )

    parser.add_argument(
        "--seed-patient-id",
        required=True,
        help="Seed patient id. Parsed as a string; matching also handles numeric JSON ids.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path where ranked output JSON should be written.",
    )

    parser.add_argument(
        "--config",
        required=False,
        type=Path,
        default=None,
        help="Optional JSON config override file.",
    )

    return parser.parse_args(argv)


def _print_summary(output_path: Path, ranking_run) -> None:
    print("Patient similarity ranking completed.")
    print(f"Seed patient id: {ranking_run.seed_patient_id}")
    print(f"Results written: {output_path}")
    print(f"Ranked candidates: {len(ranking_run.results)}")
    print(f"Skipped empty candidates: {ranking_run.skipped_empty_candidate_count}")

    if ranking_run.results:
        top_result = ranking_run.results[0]
        print(
            "Top result: "
            f"rank={top_result.rank}, "
            f"patient_id={top_result.patient_id}, "
            f"final_distance={top_result.scores.final_distance:.6f}"
        )
    else:
        print("Top result: none")


if __name__ == "__main__":
    main()