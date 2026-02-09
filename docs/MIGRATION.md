# PL Generator: Streamlit → Next.js Migration Design Document

## Version: 1.0 | Date: 2026-02-08

---

## 1. Recommended Cloud Configuration

### Primary Stack (1 recommendation)

| Layer | Service | Reason |
|-------|---------|--------|
| **Frontend** | **Vercel** (Next.js) | Zero-config deploy, edge CDN, preview deploys, free tier covers 10 users/day |
| **API** | **Render** (FastAPI) | Simple Docker deploy, free tier has 750h/month, easy env vars, auto-deploy from Git |
| **Queue/Cache** | **Upstash Redis** | Serverless Redis, pay-per-request, Celery-compatible, < $1/month at this scale |
| **DB** | **Supabase Postgres** | Free 500MB, built-in Auth (optional), REST API, realtime subscriptions |
| **File Storage** | **Supabase Storage** | Integrated with Supabase Auth, signed URLs for downloads, 1GB free |

**Why this stack for a 10-user/day product:**
- All services have generous free tiers → monthly cost ~$0-15
- Minimal configuration (no Terraform/k8s needed)
- Git-push-to-deploy on both Vercel and Render
- Supabase dashboard gives DB visibility without pgAdmin

### Alternatives Comparison

| Alternative | Pros | Cons | Verdict |
|------------|------|------|---------|
| **Railway** (instead of Render) | Nicer UI, usage-based billing | More expensive at idle, less mature | OK alternative |
| **Fly.io** (instead of Render) | Global edge, Machines API | Steeper learning curve, YAML config | Overkill for 10 users |
| **Neon** (instead of Supabase PG) | Serverless PG, branching | No built-in Auth/Storage, separate service | Use if Supabase PG limits hit |
| **Cloudflare R2** (instead of Supabase Storage) | Zero egress fees, S3-compatible | Separate service to manage | Use if >1GB files |

---

## 2. Screen Design (UX)

### 2.1 Screen List

| # | Screen | Route | Core Experience |
|---|--------|-------|-----------------|
| 1 | **Upload & Scan** | `/projects/new` | Drag-drop PDF/text, see scan progress, template preview |
| 2 | **BM Proposal Select** | `/projects/[id]/phase2` | Card-based proposal comparison (3-5 options), evidence sidebar |
| 3 | **Template Map** | `/projects/[id]/phase3` | Sheet→Segment visual mapping, drag-drop reassignment |
| 4 | **Model Design Grid** | `/projects/[id]/phase4` | AG Grid with cell→concept assignments, confidence badges |
| 5 | **Parameter Grid** | `/projects/[id]/phase5` | AG Grid with extracted values, source badges, evidence panel |
| 6 | **Scenario Playground** | `/projects/[id]/scenarios` | Sliders + live PL chart, Base/Best/Worst tabs, waterfall |
| 7 | **Export** | `/projects/[id]/export` | Download Excel (3 scenarios), needs_review preview, validation |
| 8 | **Dashboard** | `/` | Project list, resume past runs, status overview |

### 2.2 Component Architecture Per Screen

#### Screen 1: Upload & Scan (`/projects/new`)
```
┌─────────────────────────────────────────────┐
│  Header: "新しいプロジェクト"                    │
│                                             │
│  ┌─────────────────────┐  ┌──────────────┐ │
│  │   Drop Zone         │  │  Text Paste  │ │
│  │   (PDF/DOCX/PPTX)   │  │  Tab         │ │
│  └─────────────────────┘  └──────────────┘ │
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │  Scan Progress Bar                      ││
│  │  [████████░░░░░░░░] 45% - Scanning...   ││
│  └─────────────────────────────────────────┘│
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │  Template Preview (mini Excel grid)     ││
│  │  Yellow cells: 42 input cells found     ││
│  │  Blue cells: 18 formula cells preserved ││
│  └─────────────────────────────────────────┘│
│                                             │
│  [Next: Analyze Business Model →]           │
└─────────────────────────────────────────────┘
```

#### Screen 4: Model Design Grid (`/projects/[id]/phase4`)
```
┌──────────────────────────────────────────────────────────┐
│  Phase 4: モデル設計  │  Progress: ██████████░░ 78%       │
│                                                          │
│  ┌────────────────────────────────────┐ ┌──────────────┐│
│  │ AG Grid: Cell Assignments          │ │  Evidence     ││
│  │ ┌────┬───────┬────────┬──────┬───┐ │ │  Panel       ││
│  │ │Cell│Label  │Concept │Conf. │Src│ │ │              ││
│  │ ├────┼───────┼────────┼──────┼───┤ │ │ "売上高は    ││
│  │ │B5  │売上高 │revenue │ 🟢92%│doc│ │ │  初年度3億..."││
│  │ │B6  │原価率 │cogs_rat│ 🟡65%│inf│ │ │              ││
│  │ │B7  │人件費 │opex_hr │ 🔴30%│def│ │ │ [Full Quote] ││
│  │ │... │       │        │      │   │ │ │              ││
│  │ └────┴───────┴────────┴──────┴───┘ │ └──────────────┘│
│  │  Filter: [All ▼] [Unmapped ▼]      │                  │
│  └────────────────────────────────────┘                  │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Completion Checklist                               │ │
│  │  ✅ 34/42 cells mapped  │  ⚠ 3 low confidence      │ │
│  │  📋 Next: Map B12 (広告費), Review B6 evidence      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  [← Back]  [Save Draft]  [Next: Extract Parameters →]   │
└──────────────────────────────────────────────────────────┘
```

#### Screen 6: Scenario Playground (`/projects/[id]/scenarios`)
```
┌──────────────────────────────────────────────────────────┐
│  Scenario Playground                                     │
│  [Base] [Best] [Worst]  ← Tab Switcher                   │
│                                                          │
│  ┌──────────────────┐  ┌────────────────────────────────┐│
│  │ Driver Sliders    │  │  PL Summary Chart              ││
│  │                  │  │  (Recharts BarChart)            ││
│  │ 成長率  [====|==] │  │  ┌──┐                          ││
│  │         15% → 20% │  │  │  │ ┌──┐                     ││
│  │ 単価   [===|===]  │  │  │  │ │  │ ┌──┐                ││
│  │        ¥5,000     │  │  │  │ │  │ │  │                ││
│  │ 解約率  [=|=====] │  │  │売│ │原│ │営│                ││
│  │         3%        │  │  │上│ │価│ │利│                ││
│  │ 採用   [====|==]  │  │  └──┘ └──┘ └──┘                ││
│  │         5人/年    │  │  FY1  FY2  FY3  FY4  FY5       ││
│  │                  │  └────────────────────────────────┘│
│  └──────────────────┘                                    │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Scenario Comparison Table                           │ │
│  │ ┌──────────┬──────┬──────┬──────┬────────┐         │ │
│  │ │ KPI      │ Base │ Best │Worst │ Δ B-W  │         │ │
│  │ ├──────────┼──────┼──────┼──────┼────────┤         │ │
│  │ │ 売上 FY5 │ 15億 │ 18億 │ 12億 │ +6億   │         │ │
│  │ │ OP FY5   │ 2億  │ 3.2億│ 0.5億│ +2.7億 │         │ │
│  │ │ 累積FCF  │ 5億  │ 8億  │ 1億  │ +7億   │         │ │
│  │ │ 黒字化   │ FY3  │ FY2  │ FY5  │ -      │         │ │
│  │ └──────────┴──────┴──────┴──────┴────────┘         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Target vs Model (v2 Template Layer A)               │ │
│  │  Revenue: ████████████░░  85% of target             │ │
│  │  OP:      ██████░░░░░░░░  52% of target             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  [Export Excel →]                                        │
└──────────────────────────────────────────────────────────┘
```

### 2.3 "Fun" Design Elements (Gamification Light)

| Element | Location | Implementation |
|---------|----------|---------------|
| **Completion Ring** | Top-right of every phase screen | Animated SVG ring: 0→100% as cells are mapped/filled |
| **Confidence Heatmap** | Grid cell backgrounds | Green(>80%) / Yellow(50-80%) / Red(<50%) gradient |
| **"Next 3 Actions"** | Bottom checklist panel | Auto-generated from: unmapped cells, low confidence, missing evidence |
| **Target Achievement** | Scenario Playground | Progress bars: model vs target for revenue/OP/break-even |
| **Phase Progress** | Sidebar stepper | Vertical stepper with checkmarks, current phase highlighted |
| **Streak Counter** | Grid editing | "12 cells reviewed in a row!" toast notification |

### 2.4 Tech Stack (Frontend)

| Library | Purpose | License |
|---------|---------|---------|
| **Next.js 14** (App Router) | Framework | MIT |
| **AG Grid Community** | Excel-like grid | MIT (Community Edition) |
| **Recharts** | Charts (bar, line, waterfall) | MIT |
| **Tailwind CSS** | Styling | MIT |
| **shadcn/ui** | Component library | MIT |
| **Zustand** | Client state management | MIT |
| **TanStack Query** | Server state, caching, polling | MIT |
| **Framer Motion** | Animations (completion ring, transitions) | MIT |

**AG Grid License Note:** Community Edition (MIT) covers all required features: cell editing, copy/paste, filtering, sorting, column pinning, row selection. Enterprise features (Excel export, row grouping, pivoting) are NOT needed since Excel export is handled by the Python backend.

---

## 3. API Specification

### 3.1 Base URL & Auth

```
Base URL: https://api.plgenerator.example/v1
Auth: Bearer token (Supabase JWT or simple API key for MVP)
Content-Type: application/json (except file upload: multipart/form-data)
```

### 3.2 Endpoints

#### POST /v1/projects
Create a new project.

**Request:**
```json
{
  "name": "SaaS事業計画 2026",
  "template_id": "v2_ib_grade"
}
```

**Response (201):**
```json
{
  "id": "proj_abc123",
  "name": "SaaS事業計画 2026",
  "template_id": "v2_ib_grade",
  "status": "created",
  "current_phase": 1,
  "created_at": "2026-02-08T10:00:00Z"
}
```

#### POST /v1/documents/upload
Upload a document (PDF/DOCX/PPTX) or paste text.

**Request (multipart/form-data):**
```
project_id: proj_abc123
file: <binary>           # OR
text: "事業計画書のテキスト..."
kind: "file" | "text"
```

**Response (201):**
```json
{
  "id": "doc_xyz789",
  "project_id": "proj_abc123",
  "kind": "file",
  "filename": "business_plan.pdf",
  "size_bytes": 1048576,
  "status": "uploaded",
  "extracted_chars": 15000
}
```

#### POST /v1/phase1/scan
Scan template + extract document text. Synchronous for small files, job for large.

**Request:**
```json
{
  "project_id": "proj_abc123",
  "document_id": "doc_xyz789",
  "template_id": "v2_ib_grade",
  "colors": {
    "input_color": "FFFFF2CC",
    "formula_color": "FF0000FF"
  }
}
```

**Response (200 — sync) or (202 — job):**
```json
{
  "catalog": {
    "items": [
      {
        "sheet": "PL設計",
        "cell": "B5",
        "labels": ["売上高", "Revenue"],
        "units": "円",
        "period": "FY1",
        "block": "pl_revenue",
        "current_value": null,
        "data_type": "n",
        "is_formula": false
      }
    ],
    "block_index": {
      "PL設計::pl_revenue": ["B5", "B6", "B7"],
      "PL設計::pl_opex": ["B12", "B13", "B14", "B15", "B16"]
    },
    "total_items": 42
  },
  "document_summary": {
    "total_chars": 15000,
    "pages": 12,
    "preview": "株式会社ABC 事業計画書..."
  }
}
```

#### POST /v1/phase2/analyze
Business Model Analysis (LLM — job).

**Request:**
```json
{
  "project_id": "proj_abc123",
  "document_id": "doc_xyz789",
  "feedback": ""
}
```

**Response (202 — async job):**
```json
{
  "job_id": "job_phase2_001",
  "status": "queued",
  "phase": 2,
  "poll_url": "/v1/jobs/job_phase2_001"
}
```

**Job Result (when complete):**
```json
{
  "proposals": [
    {
      "label": "SaaS_3seg",
      "description": "3セグメント SaaS モデル",
      "confidence": 0.85,
      "segments": [
        {
          "name": "エンタープライズ",
          "revenue_drivers": [
            {"type": "subscription", "unit": "月額", "evidence": {"quote": "月額50万円のエンタープライズプラン", "page": 3}}
          ]
        }
      ],
      "cost_items": [...],
      "risk_factors": [...]
    }
  ],
  "financial_targets": {
    "horizon_years": 5,
    "revenue_targets": [
      {"year": "FY1", "value": 100000000, "evidence": {"quote": "初年度売上1億円", "page": 5}}
    ],
    "op_targets": [...],
    "break_even_year": "FY3",
    "cumulative_break_even_year": "FY4"
  },
  "industry": "SaaS",
  "business_model_type": "B2B"
}
```

#### POST /v1/phase3/map
Template Structure Mapping (LLM — job).

**Request:**
```json
{
  "project_id": "proj_abc123",
  "selected_proposal": "SaaS_3seg",
  "catalog_summary": {
    "sheets": ["シミュレーション分析", "PL設計", "収益モデル1", "収益モデル2", "収益モデル3"],
    "total_input_cells": 42,
    "blocks": ["pl_revenue", "pl_opex", "seg1_drivers", "seg2_drivers", "seg3_drivers"]
  }
}
```

**Response (202):**
```json
{
  "job_id": "job_phase3_001",
  "status": "queued"
}
```

**Job Result:**
```json
{
  "sheet_mappings": [
    {
      "sheet_name": "PL設計",
      "purpose": "pl_summary",
      "mapped_segment": null,
      "confidence": 0.95
    },
    {
      "sheet_name": "収益モデル1",
      "purpose": "revenue_model",
      "mapped_segment": "エンタープライズ",
      "confidence": 0.88
    }
  ],
  "suggestions": ["収益モデル3はセグメントが2つのため未使用です"]
}
```

#### POST /v1/phase4/design
Model Design — cell assignments (LLM — job).

**Request:**
```json
{
  "project_id": "proj_abc123",
  "bm_result_ref": "phase2_result_id",
  "ts_result_ref": "phase3_result_id",
  "catalog_ref": "phase1_result_id",
  "edits": []
}
```

**Job Result:**
```json
{
  "cell_assignments": [
    {
      "sheet": "PL設計",
      "cell": "B5",
      "concept": "total_revenue",
      "category": "revenue",
      "segment": null,
      "period": "FY1",
      "unit": "円",
      "confidence": 0.92,
      "label_match": "売上高"
    }
  ],
  "unmapped_cells": [
    {"sheet": "PL設計", "cell": "B20", "reason": "ラベルが曖昧"}
  ]
}
```

#### POST /v1/phase5/extract
Parameter Extraction (LLM — job).

**Request:**
```json
{
  "project_id": "proj_abc123",
  "md_result_ref": "phase4_result_id",
  "document_excerpt_chars": 10000,
  "edits": []
}
```

**Job Result:**
```json
{
  "extractions": [
    {
      "sheet": "収益モデル1",
      "cell": "C8",
      "value": 50000,
      "original_text": "月額5万円",
      "source": "document",
      "confidence": 0.91,
      "evidence": {
        "quote": "エンタープライズプランは月額5万円から",
        "page": 3,
        "rationale": "直接記載"
      }
    },
    {
      "sheet": "収益モデル1",
      "cell": "C10",
      "value": 0.05,
      "original_text": "月次解約率5%",
      "source": "inferred",
      "confidence": 0.55,
      "evidence": {
        "quote": "業界平均の解約率を想定",
        "page": null,
        "rationale": "SaaS業界の平均値から推定"
      }
    }
  ],
  "warnings": ["C15: 文書に記載なし、デフォルト値を使用"],
  "stats": {
    "total": 42,
    "document_source": 25,
    "inferred_source": 12,
    "default_source": 5,
    "avg_confidence": 0.72
  }
}
```

#### POST /v1/recalc
Recalculate PL from parameters (synchronous — fast path).

**Request:**
```json
{
  "project_id": "proj_abc123",
  "parameters": {
    "収益モデル1::C8": 50000,
    "収益モデル1::C10": 0.05,
    "PL設計::B12": 3000000
  },
  "edited_cells": {
    "収益モデル1::C8": 60000
  },
  "scenario": "base"
}
```

**Response (200):**
```json
{
  "pl_summary": {
    "revenue": [100000000, 200000000, 350000000, 500000000, 700000000],
    "cogs": [30000000, 60000000, 105000000, 150000000, 210000000],
    "gross_profit": [70000000, 140000000, 245000000, 350000000, 490000000],
    "opex": [80000000, 100000000, 120000000, 140000000, 160000000],
    "operating_profit": [-10000000, 40000000, 125000000, 210000000, 330000000],
    "fcf": [-15000000, 35000000, 115000000, 200000000, 320000000],
    "cumulative_fcf": [-15000000, 20000000, 135000000, 335000000, 655000000]
  },
  "kpis": {
    "break_even_year": "FY2",
    "cumulative_break_even_year": "FY2",
    "revenue_cagr": 0.63,
    "fy5_op_margin": 0.47
  },
  "charts_data": {
    "waterfall": [...],
    "revenue_stack": [...]
  },
  "scenario": "base"
}
```

#### POST /v1/export/excel
Generate Excel file(s) (job — heavy).

**Request:**
```json
{
  "project_id": "proj_abc123",
  "parameters": {...},
  "scenarios": ["base", "best", "worst"],
  "options": {
    "include_needs_review": true,
    "include_case_diff": true,
    "best_multipliers": {"revenue": 1.2, "cost": 0.9},
    "worst_multipliers": {"revenue": 0.8, "cost": 1.15}
  }
}
```

**Job Result:**
```json
{
  "files": [
    {"scenario": "base", "url": "https://storage.../base.xlsx", "expires_at": "2026-02-08T11:00:00Z"},
    {"scenario": "best", "url": "https://storage.../best.xlsx", "expires_at": "2026-02-08T11:00:00Z"},
    {"scenario": "worst", "url": "https://storage.../worst.xlsx", "expires_at": "2026-02-08T11:00:00Z"}
  ],
  "needs_review_url": "https://storage.../needs_review.csv",
  "validation": {
    "formulas_preserved": true,
    "no_excel_errors": true,
    "full_calc_on_load": true,
    "changed_cells": 37
  }
}
```

#### GET /v1/jobs/{job_id}
Poll job status.

**Response:**
```json
{
  "id": "job_phase2_001",
  "status": "running",
  "progress": 65,
  "phase": 2,
  "logs": [
    {"ts": "2026-02-08T10:01:00Z", "msg": "文書解析開始 (15,000文字)"},
    {"ts": "2026-02-08T10:01:05Z", "msg": "ビジネスモデル分析中..."},
    {"ts": "2026-02-08T10:01:30Z", "msg": "提案3件を生成中..."}
  ],
  "result": null,
  "created_at": "2026-02-08T10:01:00Z",
  "updated_at": "2026-02-08T10:01:30Z"
}
```

#### GET /v1/projects/{id}/state
Get full project state (for resuming).

#### POST /v1/projects/{id}/edits
Save incremental edits (patch).

#### GET /v1/projects/{id}/history
List change history for rollback.

### 3.3 Error Schema

All errors follow:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": {...}
  }
}
```

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 422 | Invalid request body |
| `GROUNDING_LOW` | 200 (in result) | Evidence quality below threshold |
| `LLM_FAILED` | 502 | LLM API call failed |
| `LLM_JSON_INVALID` | 502 | LLM returned non-JSON |
| `JOB_TIMEOUT` | 504 | Job exceeded time limit |
| `FILE_TOO_LARGE` | 413 | Upload exceeds 20MB limit |
| `PROJECT_NOT_FOUND` | 404 | Invalid project_id |
| `JOB_NOT_FOUND` | 404 | Invalid job_id |
| `TEMPLATE_NOT_FOUND` | 404 | Invalid template_id |
| `PHASE_DEPENDENCY` | 409 | Previous phase not completed |

### 3.4 CORS Configuration

```python
origins = [
    "https://plgenerator.vercel.app",
    "http://localhost:3000",  # development
]
```

---

## 4. Data Model (DB)

### 4.1 Schema

```sql
-- Projects table
CREATE TABLE projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    template_id TEXT NOT NULL DEFAULT 'v2_ib_grade',
    owner       TEXT,  -- Supabase auth user_id (optional for MVP)
    status      TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN ('created','active','completed','archived')),
    current_phase INT NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documents (uploaded files or pasted text)
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('file','text')),
    filename        TEXT,
    storage_path    TEXT,          -- Supabase Storage path
    extracted_text   TEXT,          -- Full extracted text (cached)
    meta_json       JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Runs (each attempt through the pipeline)
CREATE TABLE runs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    current_phase    INT NOT NULL DEFAULT 1,
    bm_selected_label TEXT,        -- Which proposal was selected in Phase 2
    status           TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active','completed','failed')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Phase results (raw JSON preserved for re-editing)
CREATE TABLE phase_results (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase       INT NOT NULL CHECK (phase BETWEEN 1 AND 6),
    raw_json    JSONB NOT NULL,    -- Full phase output
    metrics_json JSONB DEFAULT '{}', -- Stats: confidence avg, coverage, etc.
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_id, phase)
);

-- User edits (patches applied on top of phase results)
CREATE TABLE edits (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase       INT NOT NULL,
    patch_json  JSONB NOT NULL,    -- JSON Patch format
    author      TEXT DEFAULT 'user',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Async job tracking
CREATE TABLE jobs (
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
CREATE TABLE llm_audits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    phase           INT NOT NULL,
    provider        TEXT NOT NULL,  -- 'anthropic', 'openai', 'google'
    model           TEXT NOT NULL,  -- 'claude-sonnet-4-5-20250929'
    prompt_hash     TEXT NOT NULL,  -- SHA256 of system+user prompt
    token_usage     JSONB NOT NULL, -- {"input": 1500, "output": 3200}
    latency_ms      INT NOT NULL,
    temperature     REAL DEFAULT 0.1,
    max_tokens      INT DEFAULT 32768,
    result_hash     TEXT,           -- SHA256 of response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_runs_project ON runs(project_id);
CREATE INDEX idx_phase_results_run ON phase_results(run_id);
CREATE INDEX idx_edits_run ON edits(run_id);
CREATE INDEX idx_jobs_run ON jobs(run_id);
CREATE INDEX idx_jobs_status ON jobs(status) WHERE status IN ('queued','running');
CREATE INDEX idx_llm_audits_run ON llm_audits(run_id);
```

### 4.2 Save → Restore → Rollback Flow

1. **Save**: Each phase completion writes to `phase_results`. User edits write to `edits`.
2. **Restore**: Load `phase_results` for the run, apply `edits` in order → reconstructed state.
3. **Rollback**: Create a new run from the same project, copy `phase_results` up to the desired phase, discard later phases. User can re-run from any phase.

---

## 5. Implementation Milestones

### Week 1: Foundation

| # | Task | DoD (Definition of Done) |
|---|------|--------------------------|
| 1 | Set up monorepo structure (`apps/web`, `services/api`, `core`, `shared/schemas`) | Directories created, READMEs, root scripts |
| 2 | Extract `core/` package from `src/` (remove Streamlit deps) | `core/` imports work without streamlit installed |
| 3 | Implement Provider abstraction (`core/providers/`) | Claude provider works, interface defined, audit logging |
| 4 | Create shared Pydantic schemas (`shared/schemas/`) | API request/response models defined |
| 5 | FastAPI app skeleton with `/health`, `/v1/projects` CRUD | `uvicorn` starts, POST/GET projects works |
| 6 | Implement `/v1/phase1/scan` endpoint (wraps existing scanner) | Upload file → get catalog JSON |
| 7 | Job infrastructure (Celery + Redis) | Job created, polled, completed with test task |
| 8 | Implement `/v1/phase2/analyze` as async job | Job queued → BM analysis runs → result stored |
| 9 | Next.js app init (App Router, Tailwind, shadcn/ui) | `next dev` starts, landing page renders |
| 10 | Docker Compose for local dev (API + Redis + Worker + Postgres) | `docker compose up` → all services running |

### Week 2: Grid Editing & Core UX

| # | Task | DoD |
|---|------|-----|
| 11 | Implement Phase 3-5 API endpoints | All phase endpoints accept/return correct JSON |
| 12 | AG Grid integration in Next.js | Grid renders with mock data, cell editing works |
| 13 | Phase 4 Model Design Grid screen | AG Grid shows cell assignments with confidence badges |
| 14 | Phase 5 Parameter Grid screen with evidence panel | Click cell → see evidence in sidebar |
| 15 | `/v1/recalc` endpoint (sync PL recalculation) | Parameter change → updated PL returned in <500ms |
| 16 | Scenario Playground screen (Base/Best/Worst tabs) | Tab switch → different parameters, chart updates |
| 17 | Driver sliders with live recalc | Drag slider → API call → chart updates |
| 18 | Completion checklist component | Shows mapped/total, confidence distribution, next actions |
| 19 | Job progress polling UI (TanStack Query) | Phase 2/3 show progress bar with log messages |
| 20 | Upload & Scan screen | File drop → progress → catalog preview |

### Week 3: Polish & Deploy

| # | Task | DoD |
|---|------|-----|
| 21 | BM Proposal selection screen (Phase 2) | Card layout, evidence sidebar, select → proceed |
| 22 | Export screen with download links | Click export → job runs → download Excel files |
| 23 | DB persistence (Supabase integration) | Projects/runs/results saved and restored |
| 24 | Project dashboard (list, resume, delete) | Landing page shows past projects |
| 25 | Waterfall chart + sensitivity display | Scenario playground shows waterfall, delta columns |
| 26 | Error handling & retry UX | LLM failures show retry button, validation errors inline |
| 27 | CORS, Auth (API key or Supabase JWT), rate limiting | Production-ready security |
| 28 | Vercel + Render deployment configs | `vercel.json`, `render.yaml`, env var docs |
| 29 | E2E smoke test (upload → scan → analyze → export) | Full flow works on staging |
| 30 | Migration guide from Streamlit (for existing users) | README updated with new usage instructions |

---

## 6. Risks and Countermeasures

| Risk | Impact | Likelihood | Countermeasure |
|------|--------|-----------|----------------|
| **AG Grid Community lacks feature X** | Medium | Low | Community covers editing/filtering/sorting. Only pivot/Excel-export need Enterprise (we don't need them). Fallback: MUI DataGrid Pro ($15/dev/month). |
| **LLM cost spike** | High | Medium | Audit log tracks token usage per request. Set per-project token budget in DB. Phase 2 truncation (70%+25% = 95% coverage, saves tokens). Cache repeated prompts (prompt_hash lookup). |
| **Job queue stalls (Celery)** | High | Low | Job timeout: 5 min for LLM phases, 2 min for Excel. Dead letter queue with Upstash. Health check endpoint monitors queue depth. Alert if queue depth > 10. |
| **PDF extraction quality** | Medium | Medium | 5-backend fallback chain already implemented. Add OCR quality score to scan result. Show "extraction confidence" in UI so user can paste text instead. |
| **Evidence insufficient** | Medium | Medium | `GROUNDING_LOW` warning in API response. UI highlights cells with low evidence. "Next actions" suggests manual review for these cells. |
| **Formula destruction** | Critical | Low | **Absolute rule**: `data_type=='f'` and `startswith('=')` cells are NEVER written. Validator checks post-generation. CI test verifies formula preservation. |
| **CORS issues in production** | Low | Medium | Explicit origin whitelist. Vercel preview URLs pattern-matched. Preflight caching (max-age: 3600). |
| **File download failures** | Low | Low | Signed URLs with 1-hour expiry. Retry download button in UI. Fallback: inline base64 for small files. |
| **Upstash Redis connection limits** | Low | Low | 10 users/day ≈ 100 jobs/day. Upstash free tier: 10K commands/day. Connection pooling in Celery. |
| **Supabase free tier limits** | Low | Low | 500MB DB, 1GB storage. At 10 users/day, ~10MB/month of data. Monitor with Supabase dashboard. |

---

## 7. Existing Prompt Guard Implementation

### 7.1 JSON Output Enforcement

```python
# In Provider abstraction layer
class JSONOutputGuard:
    """Ensure LLM output is valid JSON starting with '{'."""

    @staticmethod
    def enforce(raw_text: str) -> dict:
        # Strip markdown wrappers
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()

        # Find first '{'
        brace_pos = text.find("{")
        if brace_pos < 0:
            raise LLMOutputError("Response does not contain JSON object")
        text = text[brace_pos:]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return JSONRepair.repair_truncated(text)  # existing repair logic

    @staticmethod
    def system_prompt_suffix() -> str:
        return (
            "\n\n【出力形式の厳守】JSONのみを返してください。"
            "```json等のマークダウン記法で囲まないでください。"
            "説明文やコメントも不要です。最初の文字は { で始めてください。"
        )
```

### 7.2 Evidence Verification Guard

```python
class EvidenceGuard:
    """Verify that evidence quotes actually appear in the source document."""

    @staticmethod
    def verify(extractions: list, document_text: str, threshold: float = 0.6) -> list:
        for ext in extractions:
            if not ext.get("evidence") or not ext["evidence"].get("quote"):
                ext["confidence"] = min(ext.get("confidence", 0), 0.3)
                ext["warnings"] = ext.get("warnings", []) + ["evidence_missing"]
                continue

            quote = ext["evidence"]["quote"]
            # Fuzzy match: check if quote (or 60%+ of its chars) appears in document
            if not _fuzzy_match(quote, document_text, threshold):
                ext["confidence"] *= 0.5  # Penalty for ungrounded evidence
                ext["warnings"] = ext.get("warnings", []) + ["evidence_not_found_in_document"]

        return extractions
```

### 7.3 Confidence Penalty Rules

```python
class ConfidencePenalty:
    """Apply confidence penalties based on source and evidence quality."""

    RULES = {
        "no_evidence": -0.4,          # No evidence quote provided
        "evidence_not_grounded": -0.3, # Quote not found in document
        "source_default": -0.2,        # Using default/assumed value
        "source_inferred": -0.1,       # Inferred, not directly stated
        "numeric_label": -0.15,        # Label contains a number (potential hallucination)
    }

    @staticmethod
    def apply(extraction: dict) -> dict:
        conf = extraction.get("confidence", 0.5)
        for rule, penalty in ConfidencePenalty.RULES.items():
            if rule in extraction.get("flags", []):
                conf += penalty
        extraction["confidence"] = max(0.0, min(1.0, conf))
        return extraction
```

### 7.4 Numeric Label Detection

```python
class NumericLabelGuard:
    """Prevent LLM from embedding numeric values in label fields."""

    NUMERIC_PATTERN = re.compile(r'^\d[\d,\.]*[万億千百]?[円%]?$')

    @staticmethod
    def check(cell_assignments: list) -> list:
        for assignment in cell_assignments:
            label = assignment.get("concept", "")
            if NumericLabelGuard.NUMERIC_PATTERN.match(label):
                assignment["warnings"] = assignment.get("warnings", []) + [
                    f"numeric_label_detected: '{label}' looks like a value, not a concept"
                ]
                assignment["concept"] = "NEEDS_REVIEW"
                assignment["confidence"] = min(assignment.get("confidence", 0), 0.2)
        return cell_assignments
```

### 7.5 Empty Extractions Prevention

```python
class ExtractionCompleteness:
    """Ensure Phase 5 always returns extractions (never empty)."""

    @staticmethod
    def ensure(result: dict, catalog_items: list) -> dict:
        if not result.get("extractions"):
            # Generate default extractions for all catalog items
            result["extractions"] = [
                {
                    "sheet": item["sheet"],
                    "cell": item["cell"],
                    "value": item.get("current_value"),
                    "source": "default",
                    "confidence": 0.1,
                    "evidence": {"quote": "文書に記載なし", "rationale": "デフォルト値を使用"},
                }
                for item in catalog_items
            ]
            result["warnings"] = result.get("warnings", []) + [
                "LLM returned empty extractions; populated with defaults"
            ]
        return result
```

### 7.6 Truncation Rules (Fixed)

```python
class DocumentTruncation:
    """Fixed truncation strategies per phase."""

    @staticmethod
    def for_phase2(text: str, max_chars: int = 30000) -> str:
        """Phase 2: First 70% + Last 25% (with overlap marker)."""
        if len(text) <= max_chars:
            return text
        head = int(max_chars * 0.70)
        tail = int(max_chars * 0.25)
        return text[:head] + "\n\n[...中略...]\n\n" + text[-tail:]

    @staticmethod
    def for_phase5(text: str, max_chars: int = 10000) -> str:
        """Phase 5: First 10,000 characters only."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[...以降省略...]"
```

---

## 8. Repository Structure (Monorepo)

```
Financial-Model/
├── apps/
│   └── web/                          # Next.js (Vercel)
│       ├── src/
│       │   ├── app/                   # App Router pages
│       │   │   ├── layout.tsx
│       │   │   ├── page.tsx           # Dashboard
│       │   │   └── projects/
│       │   │       ├── new/page.tsx    # Upload & Scan
│       │   │       └── [id]/
│       │   │           ├── phase2/page.tsx
│       │   │           ├── phase3/page.tsx
│       │   │           ├── phase4/page.tsx
│       │   │           ├── phase5/page.tsx
│       │   │           ├── scenarios/page.tsx
│       │   │           └── export/page.tsx
│       │   ├── components/
│       │   │   ├── ui/                # shadcn/ui components
│       │   │   ├── grid/              # AG Grid wrappers
│       │   │   ├── charts/            # Recharts components
│       │   │   ├── scenario/          # Sliders, comparison
│       │   │   └── progress/          # Completion ring, checklist
│       │   ├── lib/
│       │   │   ├── api.ts             # API client (TanStack Query)
│       │   │   └── store.ts           # Zustand stores
│       │   └── types/                 # TypeScript types (mirror Pydantic)
│       ├── package.json
│       ├── next.config.js
│       ├── tailwind.config.ts
│       └── tsconfig.json
│
├── services/
│   ├── api/                           # FastAPI (Render)
│   │   ├── app/
│   │   │   ├── main.py               # FastAPI app, CORS, routes
│   │   │   ├── routers/
│   │   │   │   ├── projects.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── phases.py
│   │   │   │   ├── recalc.py
│   │   │   │   ├── export.py
│   │   │   │   └── jobs.py
│   │   │   ├── deps.py               # Dependency injection
│   │   │   ├── db.py                  # Supabase/Postgres client
│   │   │   └── storage.py            # File storage client
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── render.yaml
│   │
│   └── worker/                        # Celery worker
│       ├── tasks/
│       │   ├── phase2.py
│       │   ├── phase3.py
│       │   ├── phase4.py
│       │   ├── phase5.py
│       │   └── export.py
│       ├── celery_app.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── core/                              # Shared Python logic (no Streamlit)
│   ├── __init__.py
│   ├── agents/                        # Existing agents (cleaned)
│   ├── catalog/                       # Template scanner
│   ├── config/                        # Data models
│   ├── excel/                         # Excel generation
│   ├── extract/                       # LLM extraction
│   ├── ingest/                        # Document ingestion
│   ├── mapping/                       # Parameter mapping
│   ├── modelmap/                      # Formula analysis
│   ├── providers/                     # NEW: LLM provider abstraction
│   │   ├── __init__.py
│   │   ├── base.py                    # Provider interface
│   │   ├── anthropic_provider.py      # Claude implementation
│   │   ├── openai_provider.py         # OpenAI (stub)
│   │   ├── google_provider.py         # Gemini (stub)
│   │   ├── guards.py                  # JSON/evidence/confidence guards
│   │   └── audit.py                   # Audit logging
│   └── simulation/                    # Monte Carlo
│
├── shared/
│   └── schemas/                       # Pydantic models for API contracts
│       ├── __init__.py
│       ├── projects.py
│       ├── documents.py
│       ├── phases.py
│       ├── jobs.py
│       ├── recalc.py
│       └── export.py
│
├── infra/
│   ├── docker-compose.yml             # Local dev: API + Worker + Redis + PG
│   ├── docker-compose.prod.yml        # Production overrides
│   └── init.sql                       # DB schema
│
├── src/                               # LEGACY: Streamlit app (preserved)
│   └── ...                            # Untouched for backward compat
│
├── templates/                         # Excel templates
├── tests/                             # Existing tests
├── config.yaml
├── pyproject.toml
└── README.md
```
