/**
 * TypeScript type definitions mirroring the Pydantic schemas.
 */

// Projects
export interface Project {
  id: string
  name: string
  template_id: string
  status: 'created' | 'active' | 'completed' | 'archived'
  current_phase: number
  created_at: string
  updated_at: string
}

// Documents
export interface Document {
  id: string
  project_id: string
  kind: 'file' | 'text'
  filename?: string
  size_bytes: number
  status: string
  extracted_chars: number
}

// Catalog
export interface CatalogItem {
  sheet: string
  cell: string
  labels: string[]
  units: string
  period: string
  block: string
  current_value: any
  data_type: string
  is_formula: boolean
}

// Phase 2
export interface BusinessModelProposal {
  label: string
  description: string
  confidence: number
  segments: any[]
  cost_items: any[]
  risk_factors: any[]
}

export interface FinancialTargets {
  horizon_years: number
  revenue_targets: { year: string; value: number; evidence?: Evidence }[]
  op_targets: { year: string; value: number; evidence?: Evidence }[]
  break_even_year: string
  cumulative_break_even_year: string
}

// Phase 4
export interface CellAssignment {
  sheet: string
  cell: string
  concept: string
  category: string
  segment?: string
  period: string
  unit: string
  confidence: number
  label_match: string
  warnings: string[]
  evidence?: Evidence
}

// Phase 5
export interface Extraction {
  sheet: string
  cell: string
  value: any
  original_text: string
  source: 'document' | 'inferred' | 'default'
  confidence: number
  evidence?: Evidence
  warnings: string[]
}

// Common
export interface Evidence {
  quote: string
  page?: number | null
  rationale: string
}

// Jobs
export interface Job {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'timeout'
  progress: number
  phase: number
  logs: { ts: string; msg: string }[]
  result: any
  error_msg?: string
  created_at: string
  updated_at: string
}

// Recalc
export interface PLSummary {
  revenue: number[]
  cogs: number[]
  gross_profit: number[]
  opex: number[]
  operating_profit: number[]
  fcf: number[]
  cumulative_fcf: number[]
}

export interface KPIs {
  break_even_year?: string
  cumulative_break_even_year?: string
  revenue_cagr: number
  fy5_op_margin: number
}

export interface RecalcResult {
  pl_summary: PLSummary
  kpis: KPIs
  charts_data: any
  scenario: string
}
