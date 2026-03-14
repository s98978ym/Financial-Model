# Evaluation Criteria

The first version of the PDCA foundation only scores Phase 5 output.

## Phase 5 Criteria

### `extraction_count`

How many extraction records were produced.

Interpretation:

- higher can mean broader coverage
- but higher is not always better if data quality drops

### `avg_confidence`

Average of `confidence` across `extractions`.

Interpretation:

- higher suggests the model is more certain
- compare together with coverage, not alone

### `mapped_target_rate`

Ratio of extraction records that include both `sheet` and `cell`.

Interpretation:

- close to `1.0` means the output is mostly placeable into the workbook

### `missing_required_fields`

Total missing values across required fields:

- `sheet`
- `cell`
- `label`
- `concept`
- `period`

Interpretation:

- lower is better

### `json_validity`

Whether the imported payload has a dictionary root and a valid `extractions` list.

Interpretation:

- `False` means the output is not safely comparable

## What The First Version Does Not Judge

Not yet automated:

- evidence grounding quality
- business plausibility
- cross-year consistency
- domain-specific correctness

Those still require human review in `compare/review.md`.
