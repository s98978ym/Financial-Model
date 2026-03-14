# API Bootstrap And Dashboard Error Handling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the API self-bootstrap its base PostgreSQL schema when core tables are missing, and make the dashboard show a clear error state instead of an endless loading spinner.

**Architecture:** The backend will add a schema-bootstrap layer ahead of the existing lightweight migrations in `services/api/app/db.py`, using `infra/init.sql` as the single source of truth for base tables. The frontend dashboard will keep its current query flow but render an explicit failure panel when the initial projects query errors.

**Tech Stack:** FastAPI, psycopg2, pytest, Next.js 14, React Query, Vitest, React Testing Library

---

## Chunk 1: Backend Schema Bootstrap

### Task 1: Add a failing test for missing base schema bootstrap

**Files:**
- Modify: `services/api/tests/test_projects.py`
- Test: `services/api/tests/test_projects.py`

- [ ] **Step 1: Write the failing test**

```python
def test_bootstrap_schema_runs_when_projects_table_missing(monkeypatch):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest services/api/tests/test_projects.py -k bootstrap_schema -v`
Expected: FAIL because the bootstrap helper does not exist or is not called.

- [ ] **Step 3: Write minimal implementation**

Add helper(s) in `services/api/app/db.py` to:
- inspect whether `projects` exists
- execute `infra/init.sql` when missing
- invoke bootstrap before existing lightweight migrations

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/api/tests/test_projects.py -k bootstrap_schema -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/api/app/db.py services/api/tests/test_projects.py
git commit -m "fix: bootstrap api schema when base tables are missing"
```

## Chunk 2: Dashboard Error State

### Task 2: Add a failing dashboard error-state test

**Files:**
- Create: `apps/web/src/app/page.test.tsx`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/vitest.setup.ts`
- Modify: `apps/web/package.json`
- Test: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('shows an error panel when projects loading fails', async () => {
  ...
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run apps/web/src/app/page.test.tsx`
Expected: FAIL because test tooling is missing or the page stays in loading state.

- [ ] **Step 3: Write minimal implementation**

Install/configure `vitest` + Testing Library for `apps/web`, then update `apps/web/src/app/page.tsx` to:
- read `isError` / `error`
- render a concise dashboard failure panel
- preserve current loading and success states

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run apps/web/src/app/page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/package.json apps/web/vitest.config.ts apps/web/vitest.setup.ts apps/web/src/app/page.tsx apps/web/src/app/page.test.tsx
git commit -m "fix: show dashboard error state when api fails"
```

## Chunk 3: Verification

### Task 3: Re-run targeted checks

**Files:**
- Modify: none
- Test: `services/api/tests/test_projects.py`, `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Run backend verification**

Run: `pytest services/api/tests/test_projects.py -k 'bootstrap_schema or list_projects' -v`
Expected: PASS

- [ ] **Step 2: Run frontend verification**

Run: `cd apps/web && npm test -- --run src/app/page.test.tsx`
Expected: PASS

- [ ] **Step 3: Run one broader regression check**

Run: `pytest services/api/tests/test_health.py services/api/tests/test_projects.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "docs: record bootstrap and dashboard verification"
```
