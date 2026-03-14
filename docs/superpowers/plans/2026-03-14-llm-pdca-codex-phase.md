# LLM Improvement PDCA Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a same-repo, Codex-owned PDCA foundation that can create experiments, import baseline/candidate outputs, compare Phase 5 results, and record decisions without depending on the current API/worker experiment path.

**Architecture:** Keep repository-coupled assets in `docs/llm-pdca/`, add a focused `src/pdca/` module for manifests, storage, importing, comparison, and reporting, and expose the workflow through `plgen pdca ...` subcommands in the existing CLI. Runtime artifacts live under `artifacts/llm-pdca/` and are intentionally ignored from Git.

**Tech Stack:** Python 3.9+, Typer, Pydantic v2, pytest

---

## File Map

- Create: `docs/llm-pdca/README.md`
- Create: `docs/llm-pdca/workflow.md`
- Create: `docs/llm-pdca/evaluation-criteria.md`
- Create: `docs/llm-pdca/templates/hypothesis.md`
- Create: `docs/llm-pdca/templates/review.md`
- Create: `src/pdca/__init__.py`
- Create: `src/pdca/models.py`
- Create: `src/pdca/storage.py`
- Create: `src/pdca/importer.py`
- Create: `src/pdca/compare.py`
- Create: `src/pdca/report.py`
- Create: `src/pdca/criteria/__init__.py`
- Create: `src/pdca/criteria/phase5_extraction.py`
- Create: `tests/pdca/test_models.py`
- Create: `tests/pdca/test_storage.py`
- Create: `tests/pdca/test_importer.py`
- Create: `tests/pdca/test_compare.py`
- Create: `tests/pdca/test_report.py`
- Modify: `.gitignore`
- Modify: `src/cli/main.py`

## Chunk 1: Foundation Models And Storage

### Task 1: Ignore Runtime Artifacts

**Files:**
- Modify: `.gitignore`
- Test: none

- [ ] **Step 1: Add runtime artifact ignore rules**

Add ignore rules for:

```gitignore
artifacts/llm-pdca/campaigns/
artifacts/llm-pdca/experiments/
```

- [ ] **Step 2: Verify the ignore rules**

Run: `git check-ignore -v artifacts/llm-pdca/experiments/foo/manifest.json`
Expected: a `.gitignore` rule is reported

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore llm pdca runtime artifacts"
```

### Task 2: Define PDCA Data Models

**Files:**
- Create: `src/pdca/__init__.py`
- Create: `src/pdca/models.py`
- Test: `tests/pdca/test_models.py`

- [ ] **Step 1: Write failing tests for manifests and prompt snapshots**

Add tests covering:

```python
def test_experiment_manifest_requires_core_fields():
    ...

def test_prompt_snapshot_accepts_prompt_provenance():
    ...

def test_imported_output_meta_allows_optional_usage_fields():
    ...
```

- [ ] **Step 2: Run the model tests to verify failure**

Run: `.venv/bin/python -m pytest tests/pdca/test_models.py -v`
Expected: FAIL because `src.pdca.models` does not exist yet

- [ ] **Step 3: Implement minimal Pydantic models**

Create `Campaign`, `ExperimentManifest`, `PromptSnapshot`, `LLMConfigSnapshot`, `InputDocumentRef`, `ImportedOutputMeta`, and a small `DecisionStatus` literal set.

- [ ] **Step 4: Re-run the model tests**

Run: `.venv/bin/python -m pytest tests/pdca/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdca/__init__.py src/pdca/models.py tests/pdca/test_models.py
git commit -m "feat: add llm pdca data models"
```

### Task 3: Add Artifact Storage Helpers

**Files:**
- Create: `src/pdca/storage.py`
- Test: `tests/pdca/test_storage.py`

- [ ] **Step 1: Write failing tests for campaign/experiment directory creation**

Cover:

```python
def test_create_campaign_writes_campaign_json(tmp_path):
    ...

def test_create_experiment_writes_manifest_and_hypothesis(tmp_path):
    ...

def test_list_experiments_filters_by_status(tmp_path):
    ...
```

- [ ] **Step 2: Run the storage tests to verify failure**

Run: `.venv/bin/python -m pytest tests/pdca/test_storage.py -v`
Expected: FAIL because storage helpers do not exist yet

- [ ] **Step 3: Implement minimal storage utilities**

Include helpers for:

- artifact root resolution
- campaign creation/loading
- experiment creation/loading
- experiment listing
- manifest updates

- [ ] **Step 4: Re-run the storage tests**

Run: `.venv/bin/python -m pytest tests/pdca/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdca/storage.py tests/pdca/test_storage.py
git commit -m "feat: add llm pdca artifact storage"
```

## Chunk 2: Import And Compare Outputs

### Task 4: Import Prompt Snapshots And Outputs

**Files:**
- Create: `src/pdca/importer.py`
- Test: `tests/pdca/test_importer.py`

- [ ] **Step 1: Write failing tests for snapshot and output import**

Cover:

```python
def test_save_prompt_snapshot_writes_json_and_markdown(tmp_path):
    ...

def test_import_output_writes_role_specific_files(tmp_path):
    ...

def test_import_meta_is_optional(tmp_path):
    ...
```

- [ ] **Step 2: Run the importer tests to verify failure**

Run: `.venv/bin/python -m pytest tests/pdca/test_importer.py -v`
Expected: FAIL because importer does not exist yet

- [ ] **Step 3: Implement minimal importer helpers**

Support:

- writing prompt snapshots
- writing `baseline_output.json` / `candidate_output.json`
- writing optional `baseline_meta.json` / `candidate_meta.json`
- storing context payloads

- [ ] **Step 4: Re-run the importer tests**

Run: `.venv/bin/python -m pytest tests/pdca/test_importer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdca/importer.py tests/pdca/test_importer.py
git commit -m "feat: add llm pdca import helpers"
```

### Task 5: Implement Phase 5 Criteria And Compare

**Files:**
- Create: `src/pdca/criteria/__init__.py`
- Create: `src/pdca/criteria/phase5_extraction.py`
- Create: `src/pdca/compare.py`
- Test: `tests/pdca/test_compare.py`

- [ ] **Step 1: Write failing tests for Phase 5 criteria scoring**

Cover:

```python
def test_phase5_compare_computes_expected_criteria_scores():
    ...

def test_compare_flags_invalid_json():
    ...

def test_compare_writes_summary_payload():
    ...
```

- [ ] **Step 2: Run the compare tests to verify failure**

Run: `.venv/bin/python -m pytest tests/pdca/test_compare.py -v`
Expected: FAIL because compare/criteria modules do not exist yet

- [ ] **Step 3: Implement minimal criteria and compare logic**

Support:

- extraction count
- average confidence
- mapped target rate
- missing required fields
- JSON validity

Emit a structured `criteria_scores` payload and a simple diff summary.

- [ ] **Step 4: Re-run the compare tests**

Run: `.venv/bin/python -m pytest tests/pdca/test_compare.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdca/criteria/__init__.py src/pdca/criteria/phase5_extraction.py src/pdca/compare.py tests/pdca/test_compare.py
git commit -m "feat: add phase5 llm pdca comparison"
```

### Task 6: Generate Markdown Reports

**Files:**
- Create: `src/pdca/report.py`
- Test: `tests/pdca/test_report.py`

- [ ] **Step 1: Write failing tests for report generation**

Cover:

```python
def test_report_includes_hypothesis_and_decision_placeholders():
    ...

def test_report_includes_criteria_scores():
    ...
```

- [ ] **Step 2: Run the report tests to verify failure**

Run: `.venv/bin/python -m pytest tests/pdca/test_report.py -v`
Expected: FAIL because report module does not exist yet

- [ ] **Step 3: Implement minimal report rendering**

Generate readable markdown containing:

- experiment identity
- hypothesis
- baseline source
- criteria summary
- decision section
- reviewer notes section

- [ ] **Step 4: Re-run the report tests**

Run: `.venv/bin/python -m pytest tests/pdca/test_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pdca/report.py tests/pdca/test_report.py
git commit -m "feat: add llm pdca markdown reports"
```

## Chunk 3: CLI And Docs

### Task 7: Wire CLI Commands Into `plgen`

**Files:**
- Modify: `src/cli/main.py`
- Test: `tests/pdca/test_storage.py`
- Test: `tests/pdca/test_importer.py`
- Test: `tests/pdca/test_compare.py`
- Test: `tests/pdca/test_report.py`

- [ ] **Step 1: Add failing CLI tests or smoke assertions**

If there is no CLI test pattern yet, add focused smoke checks that invoke the command handlers directly.

Cover:

```python
def test_pdca_init_creates_experiment_artifacts(tmp_path):
    ...

def test_pdca_import_output_writes_candidate_files(tmp_path):
    ...
```

- [ ] **Step 2: Run the CLI-related tests to verify failure**

Run: `.venv/bin/python -m pytest tests/pdca/test_storage.py tests/pdca/test_importer.py tests/pdca/test_compare.py tests/pdca/test_report.py -v`
Expected: at least one FAIL because CLI wiring is missing

- [ ] **Step 3: Add `pdca` subcommands to the existing Typer/argparse entrypoint**

Include:

- `campaign create`
- `campaign list`
- `init`
- `list`
- `show`
- `snapshot`
- `import-output`
- `compare`
- `report`
- `promote`

- [ ] **Step 4: Re-run the CLI-related tests**

Run: `.venv/bin/python -m pytest tests/pdca/test_storage.py tests/pdca/test_importer.py tests/pdca/test_compare.py tests/pdca/test_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cli/main.py tests/pdca
git commit -m "feat: add llm pdca cli commands"
```

### Task 8: Write Operator Docs

**Files:**
- Create: `docs/llm-pdca/README.md`
- Create: `docs/llm-pdca/workflow.md`
- Create: `docs/llm-pdca/evaluation-criteria.md`
- Create: `docs/llm-pdca/templates/hypothesis.md`
- Create: `docs/llm-pdca/templates/review.md`
- Test: none

- [ ] **Step 1: Write README and workflow docs**

Document:

- what the PDCA foundation is
- import-first philosophy
- shortest working command path
- how `baseline_source` works

- [ ] **Step 2: Write evaluation criteria and templates**

Include:

- Phase 5 metric definitions
- sample hypothesis template
- sample review template

- [ ] **Step 3: Smoke-check docs against implemented CLI names**

Run: `rg -n "plgen pdca" docs/llm-pdca`
Expected: command names match actual CLI surface

- [ ] **Step 4: Commit**

```bash
git add docs/llm-pdca
git commit -m "docs: add llm pdca operator guides"
```

## Chunk 4: Verification

### Task 9: Run Focused Verification

**Files:**
- Modify: none
- Test: `tests/pdca/test_models.py`
- Test: `tests/pdca/test_storage.py`
- Test: `tests/pdca/test_importer.py`
- Test: `tests/pdca/test_compare.py`
- Test: `tests/pdca/test_report.py`

- [ ] **Step 1: Run all PDCA tests**

Run: `.venv/bin/python -m pytest tests/pdca -v`
Expected: PASS

- [ ] **Step 2: Run a small regression slice**

Run: `.venv/bin/python -m pytest tests/test_config.py services/api/tests/test_health.py -v`
Expected: PASS

- [ ] **Step 3: Run a Python syntax pass**

Run: `.venv/bin/python -m py_compile src/cli/main.py src/pdca/*.py src/pdca/criteria/*.py`
Expected: no output, exit code 0

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: verify llm pdca foundation"
```

## Notes For Execution

- Keep the first version strictly Phase 5 only
- Do not implement `capture` or `apply` in this plan
- Treat imported output metadata as optional, not required
- Prefer small commits after each task
- If CLI testing via subprocess becomes awkward, test handler functions directly and keep the CLI wiring thin
