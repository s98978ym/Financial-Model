# Workflow

## Goal

Run prompt and output improvement experiments without depending on the production pipeline.

## Happy Path

1. Create a campaign

```bash
plgen pdca campaign create --campaign-id camp-20260314-001 --name "Phase 5 quality" --phase 5
```

2. Create an experiment

```bash
plgen pdca init \
  --experiment-id exp-20260314-001 \
  --campaign-id camp-20260314-001 \
  --phase 5 \
  --hypothesis "evidence guidance improves extraction quality"
```

3. Optionally save prompt snapshots

```bash
plgen pdca snapshot \
  --experiment-id exp-20260314-001 \
  --baseline-system-file /path/to/baseline-system.md \
  --baseline-user-file /path/to/baseline-user.md \
  --candidate-system-file /path/to/candidate-system.md \
  --candidate-user-file /path/to/candidate-user.md \
  --context-file /path/to/context.json
```

4. Produce baseline and candidate outputs outside the PDCA module

- Codex output
- Claude Code output
- manually exported JSON from another controlled path

5. Import both outputs

```bash
plgen pdca import-output --experiment-id exp-20260314-001 --role baseline --payload-file /path/to/baseline.json
plgen pdca import-output --experiment-id exp-20260314-001 --role candidate --payload-file /path/to/candidate.json
```

6. Compare

```bash
plgen pdca compare --experiment-id exp-20260314-001
```

7. Generate report

```bash
plgen pdca report --experiment-id exp-20260314-001
```

8. Record the decision

```bash
plgen pdca promote \
  --experiment-id exp-20260314-001 \
  --decision adopted \
  --reason "confidence improved without losing extraction coverage"
```

## Decision Meanings

- `adopted`: candidate is good enough to become the preferred next baseline
- `rejected`: candidate should not be reused
- `hold`: experiment is complete, but a human wants more review before deciding

## Starting The Next Experiment

When an experiment is `adopted`, use its candidate as the conceptual source for the next baseline and set `baseline_source` accordingly during the next `init`.

Recommended convention:

- previous winner: `exp-20260314-001`
- next experiment baseline source: `experiment:exp-20260314-001`

## Common Mistakes

- Importing only the candidate output
- Comparing outputs from different documents
- Forgetting to save prompt snapshots before comparing
- Recording `adopted` without a human-readable reason
