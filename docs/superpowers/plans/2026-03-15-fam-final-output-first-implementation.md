# FAM Final Output First Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every FAM PDCA iteration emit workbook artifacts so users can judge the actual spreadsheet output instead of scores alone.

**Architecture:** Add a focused workbook exporter under `src/evals/`, call it from `run_reference_pdca()`, write baseline and best-practical workbooks into an `exports/` folder, and surface those paths in `summary.md` and CLI output.

**Tech Stack:** Python, openpyxl, existing `src/evals` PDCA pipeline

---

## File Map

- Create: `/Users/yasunorimotani/.config/superpowers/worktrees/Financial-Model/codex-fam-pdca-eval/src/evals/workbook_export.py`
- Modify: `/Users/yasunorimotani/.config/superpowers/worktrees/Financial-Model/codex-fam-pdca-eval/src/evals/pdca_loop.py`
- Modify: `/Users/yasunorimotani/.config/superpowers/worktrees/Financial-Model/codex-fam-pdca-eval/src/cli/main.py`
- Test: `/Users/yasunorimotani/.config/superpowers/worktrees/Financial-Model/codex-fam-pdca-eval/tests/evals/test_workbook_export.py`
- Test: `/Users/yasunorimotani/.config/superpowers/worktrees/Financial-Model/codex-fam-pdca-eval/tests/evals/test_pdca_loop.py`

## Chunk 1: Workbook Exporter

### Task 1: Add failing test for workbook export

- [ ] **Step 1: Write the failing test**

Create `tests/evals/test_workbook_export.py` asserting that a candidate payload can be exported to an xlsx with expected sheet names.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_workbook_export.py -q`
Expected: FAIL because exporter module does not exist.

- [ ] **Step 3: Write minimal exporter**

Add `src/evals/workbook_export.py` with:

- `export_candidate_workbook(...)`
- sheets: `Summary`, `PL設計`, `ミールモデル`, `アカデミーモデル`, `コンサルモデル`, `Assumptions`, `Artifacts`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_workbook_export.py -q`
Expected: PASS

## Chunk 2: PDCA Integration

### Task 2: Add failing test for PDCA workbook artifacts

- [ ] **Step 1: Extend `tests/evals/test_pdca_loop.py`**

Add assertions that `run_reference_pdca()` writes:

- `exports/baseline.xlsx`
- `exports/best-practical.xlsx`

- [ ] **Step 2: Run targeted test to verify it fails**

Run: `python -m pytest tests/evals/test_pdca_loop.py::test_run_reference_pdca_writes_workbook_exports -q`
Expected: FAIL because exports are not written yet.

- [ ] **Step 3: Integrate exporter into `pdca_loop.py`**

After scores are computed:

- create `run_root / "exports"`
- export baseline workbook
- select best practical candidate (non-upper-bound)
- export best-practical workbook

- [ ] **Step 4: Run targeted test to verify it passes**

Run: `python -m pytest tests/evals/test_pdca_loop.py::test_run_reference_pdca_writes_workbook_exports -q`
Expected: PASS

## Chunk 3: User-Facing Paths

### Task 3: Surface workbook paths in summary and CLI

- [ ] **Step 1: Add failing test for summary/CLI path visibility**

Extend tests so `summary.md` mentions workbook export paths and CLI JSON includes them.

- [ ] **Step 2: Run targeted tests to verify they fail**

Run:

- `python -m pytest tests/evals/test_pdca_loop.py::test_summary_mentions_workbook_exports -q`
- `python -m pytest tests/evals/test_pdca_loop.py::test_fam_reference_cli_returns_workbook_paths -q`

- [ ] **Step 3: Implement path surfacing**

Modify:

- `src/evals/pdca_loop.py`
- `src/cli/main.py`

so users can see workbook paths immediately.

- [ ] **Step 4: Re-run targeted tests**

Expected: PASS

## Chunk 4: Full Verification

### Task 4: Run full verification

- [ ] **Step 1: Run eval tests**

Run: `python -m pytest tests/evals -q`

- [ ] **Step 2: Run compile check**

Run: `python -m py_compile src/evals/*.py src/cli/main.py`

- [ ] **Step 3: Re-run one fixture PDCA**

Run:

```bash
python -m src.cli.main eval fam-reference \
  --plan-pdf /tmp/fake.pdf \
  --reference-workbook tests/fixtures/evals/reference_workbook_minimal.xlsx \
  --artifact-root artifacts/fam-eval \
  --runner fixture
```

Verify:

- `exports/baseline.xlsx`
- `exports/best-practical.xlsx`
- `summary.md` contains workbook paths

- [ ] **Step 4: Commit**

```bash
git add src/evals/workbook_export.py src/evals/pdca_loop.py src/cli/main.py tests/evals/test_workbook_export.py tests/evals/test_pdca_loop.py docs/superpowers/specs/2026-03-15-fam-final-output-first-design.md docs/superpowers/plans/2026-03-15-fam-final-output-first-implementation.md
git commit -m "feat: export workbook artifacts for FAM eval iterations"
```
