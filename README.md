# Patient-to-Patient Similarity Search

This project implements patient-to-patient similarity ranking using SNOMED CT condition and procedure histories.

Given a patient cohort, a SNOMED CT relationship snapshot, and a seed patient id, the program ranks the remaining patients by increasing distance from the seed patient. Lower distance means greater similarity.

The method uses:

- SNOMED CT `is-a` hierarchy traversal
- within-patient hierarchical pruning
- patient-level information-content fitting
- Lin semantic distance
- seed-side event weighting
- asymmetric assignment-based event matching
- condition/procedure score combination
- patient-level life-stage adjustment

## Installation

From the repository root:

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e .
```

This installs the required Python dependencies:

- `numpy`
- `pandas`
- `scipy`

The command-line entry point is installed as:

```bash
patient-similarity
```

You can also run the CLI as a Python module:

```bash
python -m patient_similarity.cli --help
```

## Required input files

### 1. Patient cohort JSON

The patient cohort must already be converted into the expected JSON format.

The input file must contain a top-level list of patients:

```json
[
  {
    "patient_id": 1001,
    "date_of_birth": "1950-01-01",
    "events": [
      {
        "type": "C",
        "code": "26929004",
        "date": "2020-01-15"
      },
      {
        "type": "P",
        "code": "80146002",
        "date": "2021-05-20"
      }
    ]
  }
]
```

Patient fields:

| Field | Description |
|---|---|
| `patient_id` | Patient identifier. May be numeric or string. |
| `date_of_birth` | Patient date of birth in `YYYY-MM-DD` format. |
| `events` | List of condition/procedure events. |

Event fields:

| Field | Description |
|---|---|
| `type` | Event type. Use `"C"` for condition and `"P"` for procedure. |
| `code` | SNOMED CT concept id. |
| `date` | Event date in `YYYY-MM-DD` format. |

### 2. SNOMED CT relationship snapshot

The SNOMED CT RF2 relationship snapshot file must be provided separately.

Expected file type:

```text
sct2_Relationship_Snapshot_INT_YYYYMMDD.txt
```

The program uses active `is-a` relationships from this file.

The SNOMED CT relationship snapshot is not included in this repository.

## Basic usage

Run the ranking with module execution:

```bash
python -m patient_similarity.cli \
  --patients /path/to/patients.json \
  --relationships /path/to/sct2_Relationship_Snapshot_INT_20251201.txt \
  --seed-patient-id 1001 \
  --output /path/to/ranked_patients.json
```

Or, after installation:

```bash
patient-similarity \
  --patients /path/to/patients.json \
  --relationships /path/to/sct2_Relationship_Snapshot_INT_20251201.txt \
  --seed-patient-id 1001 \
  --output /path/to/ranked_patients.json
```

The seed patient is excluded from the returned ranking.

Patients with no retained condition or procedure events after preprocessing are skipped.

## Output format

By default, the output is compact:

```json
[
  {
    "rank": 1,
    "patient_id": 1002,
    "final_distance": 0.2413
  },
  {
    "rank": 2,
    "patient_id": 1003,
    "final_distance": 0.7928
  }
]
```

Output fields:

| Field | Description |
|---|---|
| `rank` | Rank position, starting from 1. |
| `patient_id` | Candidate patient identifier. |
| `final_distance` | Final patient-level distance from the seed patient. Lower means more similar. |

## Configuration

A JSON config file can be supplied with `--config`.

Example:

```bash
patient-similarity \
  --patients /path/to/patients.json \
  --relationships /path/to/sct2_Relationship_Snapshot_INT_20251201.txt \
  --seed-patient-id 1001 \
  --output /path/to/ranked_patients.json \
  --config /path/to/config.json
```

See:

```text
examples/config.example.json
```

for a full example.

Configuration values are optional. Missing values use the built-in defaults.

Unknown config fields raise an error. This is intentional so misspelled parameter names are not silently ignored.

### Component-score output

To include component distances and penalties in the output, set:

```json
{
  "output": {
    "include_component_scores": true
  }
}
```

Then the output includes additional fields:

```json
[
  {
    "rank": 1,
    "patient_id": 1002,
    "final_distance": 0.2413,
    "condition_distance": 0.1802,
    "procedure_distance": 0.4015,
    "age_penalty": 0.0951,
    "temporal_penalty": null,
    "sequence_penalty": null
  }
]
```

The event-level temporal and sequence terms are included inside event matching costs, so the top-level `temporal_penalty` and `sequence_penalty` fields are currently `null`.

### Limit result count

To return only the top N candidates:

```json
{
  "output": {
    "max_results": 25
  }
}
```

## Configurable parameters

Configuration is provided as JSON. All fields are optional. Missing fields use the built-in defaults.

The config is grouped into six sections:

```json
{
  "preprocessing": {},
  "distance": {},
  "matching": {},
  "event_weighting": {},
  "scoring": {},
  "output": {}
}
```

Unknown config fields raise an error, so misspelled parameter names are not silently ignored.

### Preprocessing parameters

| Parameter | Default | Valid values | Description |
|---|---:|---|---|
| `preprocessing.hierarchical_pruning` | `true` | `true` / `false` | If enabled, removes broader SNOMED concepts when a more specific descendant concept is present for the same patient and event type. |
| `preprocessing.deduplicate_exact_codes` | `true` | `true` / `false` | If enabled, removes repeated exact same concept codes within the same patient and event type. |
| `preprocessing.unknown_code_policy` | `"drop"` | `"drop"`, `"keep"`, `"error"` | Controls how events with codes not found in the loaded SNOMED hierarchy are handled. `"drop"` removes them, `"keep"` retains them with fallback distance behavior, and `"error"` stops execution. |

### Distance parameters

| Parameter | Default | Valid values | Description |
|---|---:|---|---|
| `distance.method` | `"lin"` | `"lin"` | Concept-level semantic distance method. Currently only Lin distance is supported. |
| `distance.unknown_distance` | `1.0` | Number `>= 0.0` | Distance assigned when an unknown concept is compared and unknown concepts have been retained. With the default preprocessing policy, unknown concepts are dropped before distance calculation. |

### Matching parameters

| Parameter | Default | Valid values | Description |
|---|---:|---|---|
| `matching.method` | `"assignment"` | `"assignment"` | Event matching method. Currently only assignment-based matching is supported. |
| `matching.unmatched_penalty` | `1.0` | Number `>= 0.0` | Cost assigned when a seed event is unmatched. The default `1.0` corresponds to the maximum concept-level distance scale. |
| `matching.semantic_threshold` | `0.30` | Number from `0.0` to `1.0`, or `null` | Maximum semantic distance allowed for a real event match. If a concept pair has distance greater than this threshold, it is treated as unmatched. Use `null` to disable thresholding. |

### Event-weighting parameters

| Parameter | Default | Valid values | Description |
|---|---:|---|---|
| `event_weighting.rarity_strength` | `6.0` | Number `>= 0.0` | Controls how strongly rare, high-information seed events are weighted. Set to `0.0` to disable rarity weighting. |
| `event_weighting.semantic_support_threshold` | `0.30` | Number `>= 0.0` and `< 1.0` | Minimum semantic support required before a condition receives support-based boosting. |
| `event_weighting.semantic_support_strength` | `1.50` | Number `>= 0.0` | Controls the strength of condition semantic-support boosting. Set to `0.0` to disable semantic support weighting. |
| `event_weighting.semantic_support_max_multiplier` | `1.75` | Number `>= 1.0` | Maximum multiplier allowed for condition semantic-support boosting. |

Rarity weighting is applied to both condition and procedure seed events.

Semantic support weighting is applied only to condition seed events. Procedure events are weighted by rarity only.

### Scoring parameters

| Parameter | Default | Valid values | Description |
|---|---:|---|---|
| `scoring.condition_weight` | `0.75` | Number `>= 0.0` | Weight of the condition matching distance when combining condition and procedure modalities. Set to `0.0` to disable condition scoring. |
| `scoring.procedure_weight` | `0.25` | Number `>= 0.0` | Weight of the procedure matching distance when combining condition and procedure modalities. Set to `0.0` to disable procedure scoring. |
| `scoring.age_weight` | `0.40` | Number from `0.0` to `1.0` | Weight of the patient-level age penalty in the final score. Set to `0.0` to disable patient-level age adjustment. |
| `scoring.age_scale_years` | `20.0` | Number `> 0.0` | Scale parameter for the patient-level median event age penalty. Larger values make age differences less influential. |
| `scoring.temporal_weight` | `0.05` | Number `>= 0.0` | Weight of the event-level age-at-event tie-breaker inside accepted event matches. Set to `0.0` to disable this tie-breaker. |
| `scoring.sequence_weight` | `0.05` | Number `>= 0.0` | Weight of the event-level sequence-position tie-breaker inside accepted event matches. Set to `0.0` to disable this tie-breaker. |
| `scoring.match_age_scale_years` | `10.0` | Number `> 0.0` | Scale parameter for the event-level age-at-event tie-breaker. Larger values make event-age differences less influential. |
| `scoring.sequence_scale` | `0.25` | Number `> 0.0` | Scale parameter for the normalized sequence-position tie-breaker. Larger values make sequence-position differences less influential. |

If the seed patient has only one active modality, for example condition events but no procedure events, the available modality receives full event-distance weight.

If both condition and procedure modalities are active, their weights are normalized by their active weight sum.

### Output parameters

| Parameter | Default | Valid values | Description |
|---|---:|---|---|
| `output.include_component_scores` | `false` | `true` / `false` | If enabled, output rows include component distances such as condition distance, procedure distance, and age penalty. |
| `output.include_matches` | `false` | `true` / `false` | Reserved for detailed match output. Leave as `false` for normal ranking output. |
| `output.max_results` | `null` | Positive integer, or `null` | Limits the number of ranked candidates returned. Use `null` to return all ranked candidates. |

### Example configuration

```json
{
  "preprocessing": {
    "hierarchical_pruning": true,
    "deduplicate_exact_codes": true,
    "unknown_code_policy": "drop"
  },
  "distance": {
    "method": "lin",
    "unknown_distance": 1.0
  },
  "matching": {
    "method": "assignment",
    "unmatched_penalty": 1.0,
    "semantic_threshold": 0.3
  },
  "event_weighting": {
    "rarity_strength": 6.0,
    "semantic_support_threshold": 0.3,
    "semantic_support_strength": 1.5,
    "semantic_support_max_multiplier": 1.75
  },
  "scoring": {
    "condition_weight": 0.75,
    "procedure_weight": 0.25,
    "age_weight": 0.4,
    "age_scale_years": 20.0,
    "temporal_weight": 0.05,
    "sequence_weight": 0.05,
    "match_age_scale_years": 10.0,
    "sequence_scale": 0.25
  },
  "output": {
    "include_component_scores": false,
    "include_matches": false,
    "max_results": null
  }
}
```

## Example files

The `examples/` directory contains:

```text
examples/
├── cohort.example.json
├── config.example.json
└── run_example.md
```

The example cohort is intentionally tiny and artificial. It is meant to show the required JSON structure, not to produce meaningful similarity rankings.
