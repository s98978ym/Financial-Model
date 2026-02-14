-- PL Generator Database Schema
-- ================================

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    template_id TEXT NOT NULL DEFAULT 'v2_ib_grade',
    owner       TEXT,
    status      TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN ('created','active','completed','archived')),
    current_phase INT NOT NULL DEFAULT 1,
    memo        TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documents (uploaded files or pasted text)
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('file','text')),
    filename        TEXT,
    storage_path    TEXT,
    extracted_text  TEXT,
    meta_json       JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Runs (each attempt through the pipeline)
CREATE TABLE IF NOT EXISTS runs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    current_phase    INT NOT NULL DEFAULT 1,
    bm_selected_label TEXT,
    status           TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active','completed','failed')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Phase results (raw JSON preserved for re-editing)
CREATE TABLE IF NOT EXISTS phase_results (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase       INT NOT NULL CHECK (phase BETWEEN 1 AND 6),
    raw_json    JSONB NOT NULL,
    metrics_json JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_id, phase)
);

-- User edits (patches applied on top of phase results)
CREATE TABLE IF NOT EXISTS edits (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase       INT NOT NULL,
    patch_json  JSONB NOT NULL,
    author      TEXT DEFAULT 'user',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Async job tracking
CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase       INT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','completed','failed','timeout')),
    progress    INT DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    logs        JSONB DEFAULT '[]',
    result_ref  UUID REFERENCES phase_results(id),
    error_msg   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LLM audit log
CREATE TABLE IF NOT EXISTS llm_audits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase           INT NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_hash     TEXT NOT NULL,
    token_usage     JSONB NOT NULL,
    latency_ms      INT NOT NULL,
    temperature     REAL DEFAULT 0.1,
    max_tokens      INT DEFAULT 32768,
    result_hash     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
CREATE INDEX IF NOT EXISTS idx_phase_results_run ON phase_results(run_id);
CREATE INDEX IF NOT EXISTS idx_edits_run ON edits(run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_run ON jobs(run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status) WHERE status IN ('queued','running');
CREATE INDEX IF NOT EXISTS idx_llm_audits_run ON llm_audits(run_id);
