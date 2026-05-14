# Running the example

This repository does not include the SNOMED CT RF2 relationship snapshot. Provide the path to your local relationship snapshot file.

Example paths below are placeholders.

## Run with module execution

```bash
python -m patient_similarity.cli \
  --patients examples/cohort.example.json \
  --relationships /path/to/sct2_Relationship_Snapshot_INT_20251201.txt \
  --seed-patient-id 1001 \
  --output outputs/ranked.example.json