# Canonical Business Model Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repo-native canonical business model, evidence ledger, and evidence-constrained planning foundation that can generalize beyond SaaS and connect to PL, workbook, and Q&A flows.

**Architecture:** Introduce new domain models under `src/domain/` for canonical business structure and assumption provenance, add engine plugins under `src/engines/`, then layer a planner and explanation pack on top before integrating with existing recalc, workbook, and Q&A paths. Keep existing behavior working while progressively moving internals behind the new interfaces.

**Tech Stack:** Python, Pydantic, pytest, existing FastAPI router layer, existing Next.js Q&A data layer.

---

## File Map

### Create

- `src/domain/canonical_model.py`
- `src/domain/evidence_ledger.py`
- `src/domain/model_synthesizer.py`
- `src/engines/base.py`
- `src/engines/subscription.py`
- `src/engines/unit_economics.py`
- `src/engines/progression.py`
- `src/engines/project_capacity.py`
- `src/solver/planner.py`
- `src/solver/constraints.py`
- `src/explain/explanation_pack.py`
- `tests/domain/test_canonical_model.py`
- `tests/domain/test_evidence_ledger.py`
- `tests/domain/test_model_synthesizer.py`
- `tests/engines/test_subscription.py`
- `tests/engines/test_unit_economics.py`
- `tests/engines/test_progression.py`
- `tests/engines/test_project_capacity.py`
- `tests/solver/test_planner.py`
- `tests/solver/test_constraints.py`
- `tests/explain/test_explanation_pack.py`
- `tests/fixtures/canonical/fam_expected.json`
- `tests/fixtures/canonical/saas_expected.json`

### Modify

- `src/agents/business_model_analyzer.py`
- `services/api/app/routers/recalc.py`
- `src/simulation/engine.py`
- `src/excel/template_v2.py`
- `apps/web/src/data/qaTemplates.ts`

---

## Chunk 1: Canonical Domain Layer

### Task 1: Add failing tests for canonical business model schema

**Files:**
- Create: `tests/domain/test_canonical_model.py`
- Create: `tests/fixtures/canonical/fam_expected.json`
- Create: `tests/fixtures/canonical/saas_expected.json`
- Create: `src/domain/canonical_model.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- a FAM-like structure with `meal`, `academy`, `consulting` segments validates
- a SaaS structure with `subscription` engine validates
- each `Driver` supports `source`, `confidence`, `mode`, `decision_required`

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/test_canonical_model.py -q`
Expected: FAIL because `src/domain/canonical_model.py` does not exist

- [ ] **Step 3: Write minimal implementation**

Implement Pydantic models:
- `ModelMetadata`
- `YearValue`
- `BreakevenTarget`
- `FinancialTargets`
- `DriverSeries`
- `Driver`
- `RevenueEngine`
- `BusinessSegment`
- `CostPool`
- `BindingSpec`
- `CanonicalBusinessModel`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/domain/test_canonical_model.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/canonical_model.py tests/domain/test_canonical_model.py tests/fixtures/canonical/
git commit -m "feat: add canonical business model schema"
```

### Task 2: Add failing tests for evidence and assumption ledger

**Files:**
- Create: `tests/domain/test_evidence_ledger.py`
- Create: `src/domain/evidence_ledger.py`

- [ ] **Step 1: Write the failing tests**

Cover:
- `EvidenceRef` validation
- `ValueRange` support for min/base/max
- `AssumptionRecord` requiring provenance fields
- `board_ready` and `review_status` behavior

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/test_evidence_ledger.py -q`
Expected: FAIL because module is missing

- [ ] **Step 3: Write minimal implementation**

Implement:
- `EvidenceRef`
- `ValueRange`
- `AssumptionRecord`
- `AssumptionLedger`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/domain/test_evidence_ledger.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/evidence_ledger.py tests/domain/test_evidence_ledger.py
git commit -m "feat: add evidence ledger models"
```

---

## Chunk 2: Model Synthesizer

### Task 3: Add failing tests for BusinessModelAnalysis -> CanonicalBusinessModel synthesis

**Files:**
- Create: `tests/domain/test_model_synthesizer.py`
- Create: `src/domain/model_synthesizer.py`
- Modify: `src/agents/business_model_analyzer.py`

- [ ] **Step 1: Write the failing tests**

Test that:
- a `BusinessModelAnalysis` with FAM-like segments produces `meal`, `academy`, `consulting` segments
- extracted financial targets are carried into `FinancialTargets`
- driver evidence from proposals lands in the ledger
- missing values become `decision_required` rather than fake defaults

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/test_model_synthesizer.py -q`
Expected: FAIL because synthesizer is missing

- [ ] **Step 3: Write minimal implementation**

Create functions:
- `synthesize_canonical_model(analysis: BusinessModelAnalysis) -> CanonicalBusinessModel`
- `build_assumption_ledger(analysis: BusinessModelAnalysis) -> AssumptionLedger`

Mapping rules:
- segment `model_type` -> `engine_type`
- `RevenueDriver` -> `Driver`
- `CostItem` -> `CostPool` seed records
- financial targets -> `FinancialTargets`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/domain/test_model_synthesizer.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/model_synthesizer.py src/agents/business_model_analyzer.py tests/domain/test_model_synthesizer.py
git commit -m "feat: synthesize canonical model from discovery analysis"
```

---

## Chunk 3: Revenue Engine Plugins

### Task 4: Add a common engine interface

**Files:**
- Create: `src/engines/base.py`
- Create: `tests/engines/test_subscription.py`
- Create: `tests/engines/test_unit_economics.py`
- Create: `tests/engines/test_progression.py`
- Create: `tests/engines/test_project_capacity.py`

- [ ] **Step 1: Write failing tests for engine interface**

Define expectations for engine output:
- `revenue`
- `variable_cost`
- `gross_profit`
- `warnings`

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/engines/test_subscription.py -q`
Expected: FAIL because interface and engines are missing

- [ ] **Step 3: Write minimal implementation**

Add:
- `EngineInput`
- `EngineOutput`
- `RevenueEnginePlugin` protocol / base class

- [ ] **Step 4: Run tests to verify partial pass/fail**

Run: `python -m pytest tests/engines/test_subscription.py -q`
Expected: still FAIL because concrete engine not implemented yet

- [ ] **Step 5: Commit**

```bash
git add src/engines/base.py tests/engines/
git commit -m "feat: add revenue engine interface"
```

### Task 5: Extract and implement the `subscription` engine

**Files:**
- Create: `src/engines/subscription.py`
- Modify: `services/api/app/routers/recalc.py`
- Test: `tests/engines/test_subscription.py`

- [ ] **Step 1: Add a failing subscription engine test**

Cover:
- monthly price x subscribers x 12
- 5-year series behavior
- missing plan data returns warning

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/engines/test_subscription.py -q`
Expected: FAIL

- [ ] **Step 3: Implement minimal engine**

Move the core logic from `_compute_archetype_revenue(..., "subscription")` into `src/engines/subscription.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/engines/test_subscription.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/engines/subscription.py services/api/app/routers/recalc.py tests/engines/test_subscription.py
git commit -m "refactor: extract subscription revenue engine"
```

### Task 6: Extract and implement the `unit_economics` engine

**Files:**
- Create: `src/engines/unit_economics.py`
- Modify: `services/api/app/routers/recalc.py`
- Test: `tests/engines/test_unit_economics.py`

- [ ] **Step 1: Add failing tests**

Cover:
- price x quantity x frequency
- variable cost by cost ratio or explicit cost drivers
- meal-like case from FAM fixture

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/engines/test_unit_economics.py -q`
Expected: FAIL

- [ ] **Step 3: Implement minimal engine**

Add explicit support for:
- `price_per_item`
- `items_per_meal`
- `meals_per_year`
- `unit_count`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/engines/test_unit_economics.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/engines/unit_economics.py services/api/app/routers/recalc.py tests/engines/test_unit_economics.py
git commit -m "feat: add unit economics engine"
```

### Task 7: Extract and implement the `progression` and `project_capacity` engines

**Files:**
- Create: `src/engines/progression.py`
- Create: `src/engines/project_capacity.py`
- Modify: `services/api/app/routers/recalc.py`
- Test: `tests/engines/test_progression.py`
- Test: `tests/engines/test_project_capacity.py`

- [ ] **Step 1: Add failing tests**

Progression should cover:
- entrants
- completion rate
- certification/progression
- price

Project capacity should cover:
- unit price
- project count
- capacity or headcount limit warnings

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/engines/test_progression.py tests/engines/test_project_capacity.py -q`
Expected: FAIL

- [ ] **Step 3: Implement minimal engines**

Model:
- academy-like progression engine
- consulting-like project capacity engine

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/engines/test_progression.py tests/engines/test_project_capacity.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/engines/progression.py src/engines/project_capacity.py services/api/app/routers/recalc.py tests/engines/test_progression.py tests/engines/test_project_capacity.py
git commit -m "feat: add progression and project capacity engines"
```

---

## Chunk 4: Evidence-Constrained Planner

### Task 8: Add failing constraint and planner tests

**Files:**
- Create: `tests/solver/test_constraints.py`
- Create: `tests/solver/test_planner.py`
- Create: `src/solver/constraints.py`
- Create: `src/solver/planner.py`

- [ ] **Step 1: Write failing tests**

Cover:
- planner only moves `solve_for` and `bounded` drivers
- planner rejects movement outside `allowed_range`
- infeasible plans return explicit violations
- FAM-like consulting capacity case fails when required projects exceed staffing

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/solver/test_constraints.py tests/solver/test_planner.py -q`
Expected: FAIL because planner is missing

- [ ] **Step 3: Implement minimal constraint layer**

Add:
- range constraint check
- simple capacity check
- target feasibility enum

- [ ] **Step 4: Implement minimal planner**

Support:
- single-engine solve
- portfolio target allocation by weight
- explanation and violation output

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/solver/test_constraints.py tests/solver/test_planner.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/solver/constraints.py src/solver/planner.py tests/solver/test_constraints.py tests/solver/test_planner.py
git commit -m "feat: add evidence constrained planner"
```

---

## Chunk 5: Explanation Pack And Q&A Context

### Task 9: Add failing explanation pack tests

**Files:**
- Create: `src/explain/explanation_pack.py`
- Create: `tests/explain/test_explanation_pack.py`
- Modify: `apps/web/src/data/qaTemplates.ts`

- [ ] **Step 1: Write failing tests**

Cover:
- top driver summary generation
- explanation includes provenance
- explanation includes constraints and downside hints
- board-ready flag becomes false when major assumptions are ungrounded

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/explain/test_explanation_pack.py -q`
Expected: FAIL because module is missing

- [ ] **Step 3: Implement minimal explanation pack**

Return:
- headline summary
- top drivers
- evidence summary
- constraint summary
- sensitivity hints
- board-ready result

- [ ] **Step 4: Extend Q&A input shape**

Modify `apps/web/src/data/qaTemplates.ts` so future UI work can accept:
- `assumptionLedger`
- `plannerSummary`
- `explanationPack`

Do not rewrite the full UI in this chunk.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/explain/test_explanation_pack.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/explain/explanation_pack.py tests/explain/test_explanation_pack.py apps/web/src/data/qaTemplates.ts
git commit -m "feat: add explanation pack foundation"
```

---

## Chunk 6: Integration Path

### Task 10: Wire recalc to canonical inputs without removing legacy support

**Files:**
- Modify: `services/api/app/routers/recalc.py`
- Modify: `src/simulation/engine.py`
- Modify: `src/excel/template_v2.py`

- [ ] **Step 1: Write failing integration tests**

Add tests that prove:
- recalc can accept canonical-derived segment configs
- simulation can consume canonical planner outputs
- workbook generation can be driven from `segment_model_types` derived from canonical engines

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest services/api/tests -q`
Expected: targeted integration tests FAIL

- [ ] **Step 3: Add an adapter layer**

Create minimal adapter functions inside existing files:
- canonical -> recalc segment inputs
- canonical -> template segment model types
- canonical -> simulation parameter ranges

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest services/api/tests -q`
Expected: targeted tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/api/app/routers/recalc.py src/simulation/engine.py src/excel/template_v2.py services/api/tests
git commit -m "feat: add canonical model adapters"
```

---

## Final Verification

- [ ] Run full targeted foundation suite

Run:

```bash
python -m pytest tests/domain tests/engines tests/solver tests/explain tests/test_agents.py services/api/tests/test_health.py -q
```

Expected:
- all new foundational tests PASS
- existing health and agent compatibility tests PASS

- [ ] Run compile check

Run:

```bash
python -m py_compile src/domain/*.py src/engines/*.py src/solver/*.py src/explain/*.py
```

Expected:
- no syntax errors

- [ ] Final commit

```bash
git add .
git commit -m "docs: record canonical model implementation plan progress"
```
