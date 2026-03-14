# FAM Diagnosis Report Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the FAM evaluation output so every run emits hypothesis details, verification verdicts, evidence summaries, and score deltas across `summary.md`, `scores.json`, and a new `diagnosis.json`.

**Architecture:** Keep the current scoring logic intact and enrich the reporting layer. First extend candidate profile metadata, then add failing tests around summary/JSON shape, then implement a diagnosis builder that produces structured per-candidate records, and finally wire those records into markdown and CLI-facing artifacts.

**Tech Stack:** Python, pytest, dataclasses, existing `src/evals/` package, JSON/Markdown artifact generation

---

## File Map

- Modify: `src/evals/candidate_profiles.py`
- Modify: `src/evals/pdca_loop.py`
- Create: `src/evals/diagnosis.py`
- Modify: `tests/evals/test_pdca_loop.py`
- Create: `tests/evals/test_diagnosis.py`

---

## Chunk 1: Candidate Metadata

### Task 1: Extend `CandidateProfile` with diagnosis metadata

**Files:**
- Modify: `src/evals/candidate_profiles.py`
- Test: `tests/evals/test_diagnosis.py`

- [ ] **Step 1: Write the failing test**

```python
from src.evals.candidate_profiles import revenue_combination_profiles


def test_candidate_profile_exposes_hypothesis_metadata():
    profile = next(p for p in revenue_combination_profiles() if p.candidate_id == "candidate-revenue-staged-sales")

    assert profile.hypothesis_title
    assert "staged" in profile.toggles_on
    assert "sales" in profile.toggles_on
    assert profile.logic_steps
    assert "pl" in profile.expected_impacts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_diagnosis.py::test_candidate_profile_exposes_hypothesis_metadata -q`
Expected: FAIL because the metadata fields do not exist yet

- [ ] **Step 3: Implement minimal metadata expansion**

Update `CandidateProfile` to add:
- `hypothesis_title`
- `hypothesis_detail`
- `toggles_on`
- `toggles_off`
- `logic_steps`
- `expected_impacts`
- `evidence_source_types`
- `next_if_success`
- `next_if_fail`

Populate at least the currently used live profiles with meaningful defaults.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_diagnosis.py::test_candidate_profile_exposes_hypothesis_metadata -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evals/candidate_profiles.py tests/evals/test_diagnosis.py
git commit -m "feat: add diagnosis metadata to candidate profiles"
```

---

## Chunk 2: Structured Diagnosis Builder

### Task 2: Add failing tests for `diagnosis.json`

**Files:**
- Create: `src/evals/diagnosis.py`
- Create: `tests/evals/test_diagnosis.py`

- [ ] **Step 1: Write the failing tests**

```python
from src.evals.diagnosis import build_candidate_diagnosis
from src.evals.scoring import ScoreResult
from src.evals.candidate_profiles import CandidateProfile


def test_build_candidate_diagnosis_includes_logic_evidence_and_verdict():
    profile = CandidateProfile(
        candidate_id="candidate-demo",
        label="Demo",
        hypothesis_title="営業効率を重ねる",
        hypothesis_detail="PL改善を狙う",
        toggles_on=["sales_efficiency"],
        toggles_off=["partner_strategy"],
        logic_steps=["consulting系列に営業効率を反映する"],
        expected_impacts={"pl": 0.03},
        evidence_source_types=["pdf", "external"],
        next_if_success=["consulting bridge を強化する"],
        next_if_fail=["sales overlay を見直す"],
    )
    baseline = ScoreResult(layer_scores={"structure": 1.0, "model_sheets": 0.9, "pl": 0.5, "explainability": 0.9}, total_score=0.825)
    score = ScoreResult(layer_scores={"structure": 1.0, "model_sheets": 0.9, "pl": 0.56, "explainability": 0.91}, total_score=0.8425)

    diagnosis = build_candidate_diagnosis(profile, score, baseline, evidence_summary={"pdf_facts": ["3年間検証"], "external_sources": []})

    assert diagnosis["hypothesis"]["title"] == "営業効率を重ねる"
    assert diagnosis["logic"]["toggles_on"] == ["sales_efficiency"]
    assert diagnosis["score"]["layers"]["pl"]["delta"] == 0.06
    assert diagnosis["verdict"]["status"] in {"hit", "partial_hit", "miss"}
    assert diagnosis["next_actions"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_diagnosis.py::test_build_candidate_diagnosis_includes_logic_evidence_and_verdict -q`
Expected: FAIL because `src/evals/diagnosis.py` does not exist

- [ ] **Step 3: Implement minimal diagnosis builder**

Create `src/evals/diagnosis.py` with:
- layer delta computation
- verdict calculation
- diagnosis payload assembly

Use simple verdict rules:
- hit: primary expected layer improved at or above threshold
- partial_hit: improved but below threshold
- miss: no improvement or regression

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_diagnosis.py::test_build_candidate_diagnosis_includes_logic_evidence_and_verdict -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evals/diagnosis.py tests/evals/test_diagnosis.py
git commit -m "feat: add diagnosis builder for FAM candidates"
```

---

## Chunk 3: JSON Artifact Expansion

### Task 3: Expand `scores.json` and add `diagnosis.json`

**Files:**
- Modify: `src/evals/pdca_loop.py`
- Test: `tests/evals/test_pdca_loop.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from src.evals.pdca_loop import run_reference_pdca


def test_run_reference_pdca_writes_diagnosis_and_score_deltas(tmp_path):
    result = run_reference_pdca(
        plan_pdf=Path("/tmp/fake.pdf"),
        reference_workbook=Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"),
        artifact_root=tmp_path,
        runner="fixture",
    )

    run_root = tmp_path / result.run_id
    scores = json.loads((run_root / "scores.json").read_text())
    diagnosis = json.loads((run_root / "diagnosis.json").read_text())

    candidate = next(iter(scores["candidates"].values()))
    assert "layer_deltas" in candidate
    assert "rank" in candidate
    assert diagnosis["candidates"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_pdca_loop.py::test_run_reference_pdca_writes_diagnosis_and_score_deltas -q`
Expected: FAIL because these keys/files do not exist yet

- [ ] **Step 3: Implement minimal JSON expansion**

Update `src/evals/pdca_loop.py` to:
- compute `layer_deltas`
- compute candidate rank
- mark upper-bound candidates
- write `diagnosis.json`

Do not change existing score semantics.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_pdca_loop.py::test_run_reference_pdca_writes_diagnosis_and_score_deltas -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evals/pdca_loop.py tests/evals/test_pdca_loop.py
git commit -m "feat: emit detailed diagnosis artifacts"
```

---

## Chunk 4: Summary Markdown Diagnosis Cards

### Task 4: Upgrade `summary.md` with hypothesis, logic, evidence, and next actions

**Files:**
- Modify: `src/evals/pdca_loop.py`
- Test: `tests/evals/test_pdca_loop.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from src.evals.pdca_loop import run_reference_pdca


def test_summary_contains_hypothesis_logic_evidence_and_next_actions(tmp_path):
    result = run_reference_pdca(
        plan_pdf=Path("/tmp/fake.pdf"),
        reference_workbook=Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"),
        artifact_root=tmp_path,
        runner="fixture",
    )

    summary = (tmp_path / result.run_id / "summary.md").read_text(encoding="utf-8")

    assert "## 仮説内容" in summary
    assert "## 仮説検証結果" in summary
    assert "## ロジック" in summary
    assert "## 根拠ファクトとデータ" in summary
    assert "## 次の改善施策" in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_pdca_loop.py::test_summary_contains_hypothesis_logic_evidence_and_next_actions -q`
Expected: FAIL because the new sections do not exist yet

- [ ] **Step 3: Implement minimal markdown enhancement**

Update `src/evals/pdca_loop.py` summary writer to add per-candidate diagnosis cards with:
- hypothesis title/detail
- toggles on/off
- logic summary
- evidence summary
- score detail with layer deltas
- verdict
- next actions

Keep existing headings where practical, but add the new explicit diagnosis sections.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_pdca_loop.py::test_summary_contains_hypothesis_logic_evidence_and_next_actions -q`
Expected: PASS

- [ ] **Step 5: Run focused eval tests**

Run: `python -m pytest tests/evals -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/evals/pdca_loop.py tests/evals/test_pdca_loop.py
git commit -m "feat: upgrade FAM summary to diagnosis report"
```

---

## Chunk 5: End-to-End Verification

### Task 5: Re-run one live FAM evaluation and verify artifact readability

**Files:**
- Modify: none unless bug fixes are needed

- [ ] **Step 1: Run the live evaluation**

Run:

```bash
python -m src.cli.main eval fam-reference \
  --plan-pdf "/Users/yasunorimotani/Library/CloudStorage/GoogleDrive-s98978ym@gmail.com/マイドライブ/Claude Code Backup/Claude/Outputs/FAM経企対応/LLM_FAM事業計画説明20260128_ビジネスプラン説明.pdf" \
  --reference-workbook "/Users/yasunorimotani/Claude/Research/FAM/明治PL説明/【井樋追加】[1_29渡部さん]費用修正本番Mostlikely【FAM】meiji_収益計画_20260121v6-2.xlsx" \
  --artifact-root "artifacts/fam-eval" \
  --runner live
```

Expected:
- command exits 0
- new run directory contains `summary.md`, `scores.json`, `diagnosis.json`

- [ ] **Step 2: Inspect artifacts for required sections**

Verify:
- `summary.md` shows hypothesis, logic, evidence, result, and next actions
- `scores.json` contains `layer_deltas`
- `diagnosis.json` contains candidate verdicts and evidence summaries

- [ ] **Step 3: Run final verification**

Run:

```bash
python -m pytest tests/evals -q
python -m py_compile src/evals/*.py src/cli/main.py
```

Expected:
- all eval tests pass
- compile succeeds

- [ ] **Step 4: Commit**

```bash
git add src/evals tests/evals
git commit -m "feat: add explainable diagnosis reports for FAM evals"
```
