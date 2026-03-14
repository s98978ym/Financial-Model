# API Bootstrap And Dashboard Error Handling Design

## Goal

Prevent the production dashboard from hanging indefinitely when the API database is partially configured, and make the underlying failure recoverable without manual schema bootstrapping.

## Problem Summary

- The Next.js dashboard requests `GET /v1/projects` on first render.
- The deployed API responds `500 Internal Server Error` for `/v1/projects` while `/health` still responds `200 OK`.
- The browser surfaces this as a CORS-style failure because the error response does not include the expected CORS header.
- The API currently performs only lightweight column/table migrations after a PostgreSQL connection succeeds. It does not create the base schema when core tables such as `projects` are missing.
- The dashboard treats the query as loading until retries are exhausted and does not present a clear failure state.

## Constraints

- Keep the existing PostgreSQL + in-memory fallback model intact.
- Do not require operators to manually run `infra/init.sql` for a clean production boot.
- Preserve the existing dashboard visual language.
- Add tests before behavior changes.

## Recommended Approach

### 1. Backend schema bootstrap

Extend `services/api/app/db.py` so that once PostgreSQL connectivity is confirmed, startup logic can detect whether the base schema exists. If required tables are missing, the API should load and execute a bootstrap SQL asset before continuing with the existing lightweight migrations.

Design details:

- Add a helper that checks `information_schema.tables` for a core table such as `projects`.
- Add a helper that reads `infra/init.sql` from disk and executes it against the active connection.
- Run bootstrap before the existing column-level migration logic.
- Keep bootstrap idempotent by relying on the existing `CREATE TABLE IF NOT EXISTS` / guarded `ALTER TABLE` statements inside `infra/init.sql`.
- If bootstrap fails, keep the exception visible so the API still fails loudly instead of masking a broken production DB.

### 2. Frontend dashboard error state

Update `apps/web/src/app/page.tsx` to render an explicit error panel when the projects query fails instead of leaving the user on a spinner.

Design details:

- Read `isError` and `error` from the dashboard query.
- Render a retry-friendly panel with a short explanation and the API error message when available.
- Keep the existing loading state for genuine in-flight requests.
- Avoid broad refactors; only touch the dashboard page.

### 3. Test strategy

Backend:

- Add a focused unit test around the new schema bootstrap helper(s).
- Validate that when table inspection reports `projects` missing, the bootstrap SQL asset is executed before regular migrations continue.

Frontend:

- Add a minimal component test harness for `apps/web`.
- Add a dashboard test proving that a rejected `listProjects` query eventually renders an error message rather than the loading state.

## Risks

- Executing a large SQL asset on startup can hide syntax/path issues until runtime, so the helper must have a deterministic file path and good test coverage.
- Adding frontend test tooling increases scope slightly, but keeping it limited to `vitest` + Testing Library should minimize churn.

## Verification

- Backend targeted pytest for the new bootstrap behavior.
- Frontend targeted vitest for dashboard error rendering.
- Manual smoke check of the affected production endpoints remains useful after deployment:
  - `GET /health`
  - `GET /v1/projects`
  - dashboard root page
