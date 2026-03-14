# LLM Improvement PDCA Foundation - Codex Phase Design

## Goal

Build a same-repo, Codex-owned experimentation foundation for iterating on LLM improvements in `Financial-Model` without making the PDCA layer depend on the current API/worker execution path.

## Why This Exists

The repository already contains prompt definitions, API-side prompt version storage, and provider/audit primitives, but the existing production path is not yet a reliable substrate for experiment automation:

- `llm_audits` persistence is not wired end-to-end
- worker execution does not yet provide a stable prompt injection path for experiment candidates
- tying the first PDCA iteration to those gaps would turn this project into a pipeline repair effort

The Codex phase therefore focuses on an experimentation ledger: create experiments, snapshot conditions, import outputs produced elsewhere, compare them consistently, and record decisions.

## Non-Goals

This phase does not include:

- Claude Code skill authoring
- automatic prompt application to production
- worker-side audit persistence fixes
- prompt version injection into existing worker tasks
- fully automated judge or hypothesis generation
- generalized multi-project extraction

## Core Design Decision

Use `import-first, capture-optional`.

Primary path:

1. Create a campaign and experiment
2. Snapshot prompts and experiment conditions
3. Obtain baseline/candidate outputs from Codex, Claude Code, or another controlled execution path
4. Import those outputs into artifacts
5. Compare, report, and record a decision

Secondary path:

- Add `capture` later for compatibility with existing `run` / `phase_results` data once the repository execution path is ready

This keeps the PDCA foundation aligned with the long-term "agent skills + flat-rate human-in-the-loop" direction.

## Repository Placement

Keep the work in the same repository because it is still tightly coupled to `Financial-Model` concepts such as prompt keys, phase semantics, and structured output shapes.

Tracked files:

- `docs/llm-pdca/README.md`
- `docs/llm-pdca/workflow.md`
- `docs/llm-pdca/evaluation-criteria.md`
- `docs/llm-pdca/templates/hypothesis.md`
- `docs/llm-pdca/templates/review.md`
- `src/pdca/models.py`
- `src/pdca/storage.py`
- `src/pdca/importer.py`
- `src/pdca/compare.py`
- `src/pdca/report.py`
- `src/pdca/criteria/__init__.py`
- `src/pdca/criteria/phase5_extraction.py`
- `tests/pdca/...`
- `src/cli/main.py`

Untracked runtime artifacts:

- `artifacts/llm-pdca/campaigns/...`
- `artifacts/llm-pdca/experiments/...`

Artifacts stay in-repo for convenience but should be ignored from Git history.

## Directory Layout

```text
docs/llm-pdca/
  README.md
  workflow.md
  evaluation-criteria.md
  templates/
    hypothesis.md
    review.md

artifacts/llm-pdca/
  campaigns/
    camp-YYYYMMDD-XXX/
      campaign.json
  experiments/
    exp-YYYYMMDD-XXX/
      manifest.json
      hypothesis.md
      inputs/
        system_prompt.md
        user_prompt.md
        baseline_prompt_snapshot.json
        candidate_prompt_snapshot.json
        context.json
      outputs/
        baseline_output.json
        candidate_output.json
        baseline_meta.json
        candidate_meta.json
      compare/
        diff.md
        summary.json
        review.md

src/pdca/
  models.py
  storage.py
  importer.py
  compare.py
  report.py
  criteria/
    __init__.py
    phase5_extraction.py
```

## Data Model Overview

### Campaign

Represents one improvement theme, for example "Phase 5 extraction quality".

Minimum fields:

- `campaign_id`
- `name`
- `target_phase`
- `goal`
- `status`
- `created_at`

### Experiment Manifest

Represents a single hypothesis attempt within a campaign.

Minimum fields:

- `experiment_id`
- `campaign_id`
- `parent_experiment_id`
- `baseline_source`
- `target_phase`
- `hypothesis`
- `status`
- `decision`
- `decision_reason`
- `llm_config`
- `prompt_pair`
- `input_document`
- `created_at`
- `completed_at`

### Prompt Snapshot

Stores the exact prompt pair and provenance used for an experiment.

Minimum fields:

- `system_prompt`
- `user_prompt`
- `prompt_key`
- `source`

### Imported Output Metadata

Optional companion metadata for baseline and candidate outputs.

Minimum fields:

- `provider`
- `model`
- `temperature`
- `max_tokens`
- `latency_ms`
- `input_tokens`
- `output_tokens`
- `notes`

These metadata files are optional in the first version so the design does not depend on missing `llm_audits`.

## CLI Surface

Add a `pdca` subcommand family to the existing `plgen` CLI.

Initial commands:

- `plgen pdca campaign create`
- `plgen pdca campaign list`
- `plgen pdca init`
- `plgen pdca list`
- `plgen pdca show`
- `plgen pdca snapshot`
- `plgen pdca import-output --role baseline|candidate`
- `plgen pdca compare`
- `plgen pdca report`
- `plgen pdca promote --decision adopted|rejected|hold`

Deferred commands:

- `plgen pdca capture`
- `plgen pdca apply`

## User Workflow

1. Create a campaign for an improvement theme
2. Initialize an experiment inside that campaign
3. Snapshot prompts and context
4. Produce baseline and candidate outputs outside the PDCA module
5. Import those outputs into the experiment artifacts
6. Run criteria-based comparison
7. Generate a readable report
8. Record `adopted`, `rejected`, or `hold`
9. Start the next experiment with `baseline_source` pointing to the adopted prior candidate if needed

## Evaluation Strategy

The first implementation targets only Phase 5 to keep scope small and grounded in a clear output shape.

Initial Phase 5 criteria:

- `extraction_count`
- `avg_confidence`
- `mapped_target_rate`
- `missing_required_fields`
- `json_validity`

These scores should be emitted into `compare/summary.json` under a `criteria_scores` section so later Claude Code skills can read them consistently.

## Beginner Experience Requirements

The first version must be usable by a teammate who does not know the codebase:

- `workflow.md` explains the happy path in plain language
- `README.md` shows the shortest viable command sequence
- `list` and `show` make artifacts discoverable without manually opening JSON files
- `report` produces a readable markdown summary without requiring manual assembly

## Extraction Boundary For Future Reuse

Do not create a new repository yet. Instead, isolate generic logic inside `src/pdca/` and keep `Financial-Model`-specific assumptions in the thinnest possible layer.

Good extraction candidates later:

- `src/pdca/models.py`
- `src/pdca/storage.py`
- `src/pdca/importer.py`
- `src/pdca/compare.py`
- generic reporting helpers

Likely repo-specific for now:

- Phase 5 criteria details
- prompt key naming conventions
- workflow docs tied to this application

## Risks Accepted In This Phase

- baseline/candidate outputs are still produced outside the PDCA module
- imported metadata may be partial until audit logging is wired elsewhere
- promotion records decisions but does not mutate production prompt state

These are acceptable because the main goal is a stable experiment ledger, not full production prompt automation.

## Next Step

Write an implementation plan that creates the tracked docs, PDCA module scaffolding, CLI entrypoints, and tests in small TDD-sized tasks.
