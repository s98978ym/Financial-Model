# LLM PDCA Foundation

`LLM PDCA Foundation` is a lightweight experiment ledger for improving prompt and output quality inside `Financial-Model`.

This first version is intentionally `import-first`:

- use `plgen pdca ...` to create and track experiments
- obtain baseline and candidate outputs outside the PDCA module
- import those outputs into artifacts
- compare them with Phase 5 criteria
- record a decision

## Why It Exists

The current repository has prompt definitions, prompt version storage, and provider primitives, but the existing execution path is not yet a stable experiment runner. The PDCA layer therefore focuses on reproducible records first, not automatic prompt deployment.

## Shortest Working Flow

```bash
plgen pdca campaign create --campaign-id camp-20260314-001 --name "Phase 5 quality" --phase 5
plgen pdca init --experiment-id exp-20260314-001 --campaign-id camp-20260314-001 --phase 5 --hypothesis "evidence guidance improves extraction quality"
plgen pdca import-output --experiment-id exp-20260314-001 --role baseline --payload-file /path/to/baseline.json
plgen pdca import-output --experiment-id exp-20260314-001 --role candidate --payload-file /path/to/candidate.json
plgen pdca compare --experiment-id exp-20260314-001
plgen pdca report --experiment-id exp-20260314-001
plgen pdca promote --experiment-id exp-20260314-001 --decision adopted --reason "confidence improved without losing coverage"
```

## Artifact Layout

- `artifacts/llm-pdca/campaigns/`
- `artifacts/llm-pdca/experiments/`

Each experiment keeps:

- `manifest.json`
- `hypothesis.md`
- `inputs/`
- `outputs/`
- `compare/`

## Current Scope

Supported now:

- campaign creation/listing
- experiment creation/listing/show
- prompt snapshot saving
- output importing
- Phase 5 comparison
- markdown report generation
- decision recording

Deferred:

- DB capture from existing runs
- automatic prompt application
- Claude Code skill automation
- Phase 2/3/4 criteria

## Baseline Lineage

Use `baseline_source` to show where a new experiment starts from:

- `default`
- `experiment:<exp-id>`

That makes it possible to trace which adopted candidate became the next baseline.
