# FAM Reference PDCA Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reference-driven evaluation harness that uses the FAM business-plan PDF and reference workbook to score generated canonical models, model sheets, and PL output, then run one automatic PDCA comparison loop over candidate profiles.

**Architecture:** Build a small `src/evals/` package on top of the canonical model foundation. First extract a normalized benchmark from the reference workbook, then score generated outputs against that benchmark, then add a candidate-profile loop that compares baseline vs candidates and writes artifacts and a summary. Keep this isolated from UI work and avoid prompt self-modification in the first version.

**Tech Stack:** Python, Pydantic models already in repo, openpyxl, pytest, existing canonical/planner/explanation modules

---

## File Map

- Create: `src/evals/__init__.py`
- Create: `src/evals/reference_workbook.py`
- Create: `src/evals/scoring.py`
- Create: `src/evals/candidate_profiles.py`
- Create: `src/evals/pdca_loop.py`
- Modify: `src/cli/main.py`
- Create: `tests/evals/test_reference_workbook.py`
- Create: `tests/evals/test_scoring.py`
- Create: `tests/evals/test_pdca_loop.py`
- Create: `tests/fixtures/evals/reference_workbook_minimal.xlsx`
- Create: `tests/fixtures/evals/baseline_result.json`
- Create: `tests/fixtures/evals/candidate_result.json`

---

## Chunk 1: Reference Workbook Extraction

### Task 1: Add failing tests for reference workbook normalization

**Files:**
- Create: `tests/evals/test_reference_workbook.py`
- Create: `tests/fixtures/evals/reference_workbook_minimal.xlsx`
- Create: `src/evals/reference_workbook.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from src.evals.reference_workbook import extract_reference_workbook


def test_extract_reference_workbook_reads_named_model_sections():
    fixture = Path("tests/fixtures/evals/reference_workbook_minimal.xlsx")
    reference = extract_reference_workbook(fixture)

    assert set(reference.segment_names) == {"アカデミー", "コンサル", "ミール"}
    assert reference.model_sheets["ミール"]["price_per_item"][0] == 500
    assert reference.pl_lines["売上"][0] == 9700000


def test_extract_reference_workbook_ignores_formatting_and_keeps_series_only():
    fixture = Path("tests/fixtures/evals/reference_workbook_minimal.xlsx")
    reference = extract_reference_workbook(fixture)

    assert reference.model_sheets["コンサル"]["sku_unit_price"][0] == 15000000
    assert reference.model_sheets["アカデミー"]["academy_students"][0] == 127
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_reference_workbook.py -q`
Expected: FAIL because `src/evals/reference_workbook.py` does not exist

- [ ] **Step 3: Implement minimal extraction models and workbook parser**

Create `src/evals/reference_workbook.py` with:

- `ReferenceWorkbook`
- `extract_reference_workbook(path: Path) -> ReferenceWorkbook`
- normalized outputs:
  - `segment_names: list[str]`
  - `model_sheets: dict[str, dict[str, list[float]]]`
  - `pl_lines: dict[str, list[float]]`

Normalization rules:
- prefer semantic keys, not cell addresses
- ignore formatting
- extract only the benchmark rows needed for scoring

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_reference_workbook.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evals/reference_workbook.py tests/evals/test_reference_workbook.py tests/fixtures/evals/reference_workbook_minimal.xlsx
git commit -m "feat: add reference workbook extraction"
```

---

## Chunk 2: Multi-Layer Scoring

### Task 2: Add failing tests for canonical/model-sheet/PL scoring

**Files:**
- Create: `tests/evals/test_scoring.py`
- Create: `tests/fixtures/evals/baseline_result.json`
- Create: `tests/fixtures/evals/candidate_result.json`
- Create: `src/evals/scoring.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import json

from src.evals.reference_workbook import extract_reference_workbook
from src.evals.scoring import score_candidate


def test_score_candidate_returns_layer_scores_and_total():
    reference = extract_reference_workbook(Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"))
    candidate = json.loads(Path("tests/fixtures/evals/candidate_result.json").read_text())

    result = score_candidate(reference, candidate)

    assert set(result.layer_scores) == {"structure", "model_sheets", "pl", "explainability"}
    assert result.total_score > 0


def test_better_candidate_scores_higher_than_baseline():
    reference = extract_reference_workbook(Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"))
    baseline = json.loads(Path("tests/fixtures/evals/baseline_result.json").read_text())
    candidate = json.loads(Path("tests/fixtures/evals/candidate_result.json").read_text())

    baseline_score = score_candidate(reference, baseline)
    candidate_score = score_candidate(reference, candidate)

    assert candidate_score.total_score > baseline_score.total_score
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_scoring.py -q`
Expected: FAIL because `src/evals/scoring.py` does not exist

- [ ] **Step 3: Implement minimal scoring**

Create `src/evals/scoring.py` with:

- `ScoreResult`
- `score_candidate(reference, candidate) -> ScoreResult`

Layer scoring:
- `structure`
  - segment set overlap
  - expected engine types
- `model_sheets`
  - normalized driver error for meal / academy / consulting
- `pl`
  - normalized error for benchmark PL lines
- `explainability`
  - coverage of `source_type`, `evidence_refs`, `review_status`

Keep first version deterministic and weighted. Do not overfit to workbook layout.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_scoring.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evals/scoring.py tests/evals/test_scoring.py tests/fixtures/evals/baseline_result.json tests/fixtures/evals/candidate_result.json
git commit -m "feat: add FAM reference scoring"
```

---

## Chunk 3: Candidate Profiles And PDCA Loop

### Task 3: Add failing tests for candidate-profile comparison loop

**Files:**
- Create: `src/evals/candidate_profiles.py`
- Create: `src/evals/pdca_loop.py`
- Create: `tests/evals/test_pdca_loop.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from src.evals.pdca_loop import run_reference_pdca


def test_run_reference_pdca_selects_highest_scoring_candidate(tmp_path):
    result = run_reference_pdca(
        plan_pdf=Path("/tmp/fake.pdf"),
        reference_workbook=Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"),
        artifact_root=tmp_path,
        runner="fixture",
    )

    assert result.best_candidate_id == "candidate-better"
    assert (tmp_path / result.run_id / "summary.md").exists()


def test_run_reference_pdca_writes_scores_and_summary(tmp_path):
    result = run_reference_pdca(
        plan_pdf=Path("/tmp/fake.pdf"),
        reference_workbook=Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"),
        artifact_root=tmp_path,
        runner="fixture",
    )

    assert (tmp_path / result.run_id / "scores.json").exists()
    assert result.baseline_score is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_pdca_loop.py -q`
Expected: FAIL because `src/evals/pdca_loop.py` does not exist

- [ ] **Step 3: Implement minimal candidate-profile loop**

Create `src/evals/candidate_profiles.py`:
- define baseline profile
- define 2-3 candidate profiles
- each profile contains analyzer/synthesizer/adapter overrides

Create `src/evals/pdca_loop.py`:
- load reference workbook
- run baseline and candidate generations
- score each output
- choose best candidate
- write:
  - `reference.json`
  - `scores.json`
  - `summary.md`

For the first version, support `runner="fixture"` for tests and `runner="live"` for the real run.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_pdca_loop.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evals/candidate_profiles.py src/evals/pdca_loop.py tests/evals/test_pdca_loop.py
git commit -m "feat: add reference PDCA loop"
```

---

## Chunk 4: CLI Integration And Live FAM Run

### Task 4: Add CLI entrypoint for reference evaluation

**Files:**
- Modify: `src/cli/main.py`
- Test: `tests/evals/test_pdca_loop.py`

- [ ] **Step 1: Write the failing CLI test**

Add a focused test that checks:
- the CLI accepts `--plan-pdf`
- the CLI accepts `--reference-workbook`
- the CLI writes artifacts to the requested output directory

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_pdca_loop.py -q`
Expected: FAIL because CLI subcommand does not exist

- [ ] **Step 3: Implement minimal CLI wiring**

Add a command like:

```bash
python -m src.cli.main eval fam-reference \
  --plan-pdf /abs/path/to/plan.pdf \
  --reference-workbook /abs/path/to/reference.xlsx \
  --artifact-root artifacts/fam-eval \
  --runner live
```

The command should call `run_reference_pdca(...)` and print:
- run id
- baseline score
- best candidate id
- best candidate score

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/evals/test_pdca_loop.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cli/main.py tests/evals/test_pdca_loop.py
git commit -m "feat: add FAM reference eval CLI"
```

### Task 5: Run the first live FAM reference evaluation

**Files:**
- Output only under: `artifacts/fam-eval/`

- [ ] **Step 1: Run the live evaluation**

Run:

```bash
python -m src.cli.main eval fam-reference \
  --plan-pdf "/Users/yasunorimotani/Library/CloudStorage/GoogleDrive-s98978ym@gmail.com/マイドライブ/Claude Code Backup/Claude/Outputs/FAM経企対応/LLM_FAM事業計画説明20260128_ビジネスプラン説明.pdf" \
  --reference-workbook "/Users/yasunorimotani/Claude/Research/FAM/明治PL説明/【井樋追加】[1_29渡部さん]費用修正本番Mostlikely【FAM】meiji_収益計画_20260121v6-2.xlsx" \
  --artifact-root artifacts/fam-eval \
  --runner live
```

Expected:
- baseline candidate produced
- at least one candidate profile scored
- `summary.md` written

- [ ] **Step 2: Inspect artifact summary**

Verify that summary includes:
- layer scores
- top mismatches
- best candidate
- recommendation for next hypothesis

- [ ] **Step 3: Run focused verification**

Run:

```bash
python -m pytest tests/evals tests/domain tests/solver tests/explain tests/test_canonical_adapters.py services/api/tests/test_recalc_archetypes.py -q
python -m py_compile src/evals/*.py src/cli/main.py
```

Expected:
- PASS
- no syntax errors

- [ ] **Step 4: Commit**

```bash
git add artifacts/fam-eval src/evals src/cli/main.py tests/evals
git commit -m "feat: run first FAM reference PDCA evaluation"
```

---

## Notes For The Implementer

- Do not depend on the user-provided workbook in tests. Use synthetic fixtures under `tests/fixtures/evals/`.
- Keep workbook parsing semantic. Never hardcode row numbers from the real workbook directly into tests.
- The first iteration is allowed to be profile-based, not prompt-self-editing.
- Favor reproducible artifacts over clever heuristics.
- If the live run reveals that current canonical synthesis cannot produce one of the three segment families, surface that mismatch in `summary.md` instead of hiding it.
