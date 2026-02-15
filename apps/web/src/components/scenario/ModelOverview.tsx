'use client'

import { useState, useRef, useEffect } from 'react'
import type { IndustryKey } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS } from '@/data/industryBenchmarks'

interface SegmentData {
  name: string
  revenue: number[]
  cogs: number[]
  gross_profit: number[]
  cogs_rate: number
  growth_rate: number
}

interface SGABreakdown {
  payroll: number[]
  marketing: number[]
  office: number[]
  system: number[]
  other: number[]
}

interface PayrollRoleDetail {
  label: string
  salary: number
  headcount: number[]
  cost: number[]
}

interface SGADetail {
  payroll: {
    roles: Record<string, PayrollRoleDetail>
    total: number[]
  }
  marketing: {
    categories: Record<string, number[]>
    total: number[]
  }
  office: number[]
  system: number[]
  other: number[]
}

interface BreakevenGapData {
  target_fy: number
  actual_fy: number | null
  achieved: boolean
  gap_years: number
  required_opex_change_pct: number | null
}

interface ModelOverviewProps {
  parameters: Record<string, number>
  kpis?: {
    break_even_year?: string | null
    cumulative_break_even_year?: string | null
    revenue_cagr?: number
    fy5_op_margin?: number
    gp_margin?: number
    breakeven_gap?: BreakevenGapData | null
    cum_breakeven_gap?: BreakevenGapData | null
  }
  plSummary?: {
    revenue: number[]
    cogs: number[]
    gross_profit: number[]
    opex: number[]
    depreciation?: number[]
    capex?: number[]
    operating_profit: number[]
    fcf: number[]
    cumulative_fcf: number[]
    segments?: SegmentData[]
    sga_breakdown?: SGABreakdown
    sga_detail?: SGADetail
  }
  industry: IndustryKey
  onParameterChange: (key: string, value: number) => void
}

// ─── Helpers ───────────────────────────────────────────────
function formatYen(v: number): string {
  if (Math.abs(v) >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(v) >= 10_000) return (v / 10_000).toFixed(0) + '万円'
  return v.toLocaleString() + '円'
}
function formatPct(v: number): string { return (v * 100).toFixed(0) + '%' }

function parseYenInput(raw: string): number | null {
  var cleaned = raw.replace(/[,\s円]/g, '')
  if (cleaned.includes('億')) { var n = parseFloat(cleaned.replace('億', '')); return isNaN(n) ? null : n * 1e8 }
  if (cleaned.includes('万')) { var n2 = parseFloat(cleaned.replace('万', '')); return isNaN(n2) ? null : n2 * 1e4 }
  var r = parseFloat(cleaned); return isNaN(r) ? null : r
}
function parsePctInput(raw: string): number | null {
  var n = parseFloat(raw.replace(/[%％\s]/g, '')); if (isNaN(n)) return null; return n > 1 ? n / 100 : n
}

/** Trend arrow */
function Trend({ from, to }: { from: number; to: number }) {
  if (to > from * 1.01) return <span className="text-green-500 text-[10px] ml-0.5">▲</span>
  if (to < from * 0.99) return <span className="text-red-500 text-[10px] ml-0.5">▼</span>
  return <span className="text-gray-400 text-[10px] ml-0.5">─</span>
}

/** Mini 5-year sparkline */
function Spark({ values, color }: { values: number[]; color: string }) {
  if (!values || values.length < 5) return null
  var max = Math.max(...values.map(Math.abs)) || 1
  return (
    <div className="flex items-end gap-px h-3">
      {values.map(function(v, i) {
        var h = Math.max((Math.abs(v) / max) * 100, 8)
        var neg = v < 0
        return <div key={i} className={'w-1.5 rounded-sm ' + (neg ? 'bg-red-300' : color)} style={{ height: h + '%' }} />
      })}
    </div>
  )
}

/** Inline editable value */
function EV({ value, display, paramKey, parse, onCommit, className }: {
  value: number; display: string; paramKey: string
  parse: (r: string) => number | null; onCommit: (k: string, v: number) => void
  className?: string
}) {
  var [editing, setEditing] = useState(false)
  var [draft, setDraft] = useState('')
  var ref = useRef<HTMLInputElement>(null)
  useEffect(function() { if (editing && ref.current) { ref.current.focus(); ref.current.select() } }, [editing])
  if (editing) return (
    <input ref={ref} type="text" value={draft}
      onChange={function(e) { setDraft(e.target.value) }}
      onBlur={function() { var p = parse(draft); if (p !== null && !isNaN(p)) onCommit(paramKey, p); setEditing(false) }}
      onKeyDown={function(e) { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); else if (e.key === 'Escape') setEditing(false) }}
      className="inline-block w-20 px-1 py-0 text-xs font-bold text-blue-700 bg-blue-50 border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
    />
  )
  return (
    <button onClick={function() { setDraft(display); setEditing(true) }}
      className={'inline-block px-1 py-0 text-xs font-bold text-blue-700 bg-blue-50/80 rounded border border-transparent hover:border-blue-300 cursor-pointer transition-colors ' + (className || '')}
      title="クリックして編集">
      {display}
    </button>
  )
}

/** Expandable section wrapper */
function Section({ color, label, summary, badge, expanded, onToggle, children }: {
  color: string; label: string; summary: React.ReactNode; badge?: React.ReactNode
  expanded: boolean; onToggle: () => void; children: React.ReactNode
}) {
  return (
    <div>
      <button onClick={onToggle} className="w-full text-left group">
        <div className="flex items-center gap-2 mb-1">
          <div className={'w-2 h-2 rounded-full ' + color} />
          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
          {badge}
          <svg className={'w-3.5 h-3.5 text-gray-400 ml-auto transition-transform ' + (expanded ? 'rotate-180' : '')}
            fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
        <div className="ml-4 text-xs text-gray-600">{summary}</div>
      </button>
      {expanded && <div className="ml-4 mt-2">{children}</div>}
    </div>
  )
}

/** Row inside a detail panel */
function DetailRow({ label, value, sub, spark, sparkColor, children }: {
  label: string; value: string; sub?: string; spark?: number[]; sparkColor?: string; children?: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-gray-50 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="text-[11px] text-gray-600 truncate">{label}</div>
        {sub && <div className="text-[9px] text-gray-400">{sub}</div>}
      </div>
      {spark && <Spark values={spark} color={sparkColor || 'bg-blue-400'} />}
      <div className="text-xs font-mono font-medium text-gray-900 text-right whitespace-nowrap">{value}</div>
      {children}
    </div>
  )
}

// ─── SGA label/color maps ──────────────────────────────────
var SGA_META: Record<string, { label: string; color: string; textColor: string }> = {
  payroll:   { label: '人件費',     color: 'bg-orange-400', textColor: 'text-orange-700' },
  marketing: { label: 'マーケ費',   color: 'bg-purple-400', textColor: 'text-purple-700' },
  office:    { label: 'オフィス',   color: 'bg-gray-400',   textColor: 'text-gray-600' },
  system:    { label: 'システム',   color: 'bg-cyan-400',   textColor: 'text-cyan-700' },
  other:     { label: 'その他',     color: 'bg-gray-300',   textColor: 'text-gray-500' },
}
var SGA_KEYS = ['payroll', 'marketing', 'office', 'system', 'other'] as const

// ─── Main Component ────────────────────────────────────────
export function ModelOverview({ parameters, kpis, plSummary, industry, onParameterChange }: ModelOverviewProps) {
  var [revExpanded, setRevExpanded] = useState(false)
  var [costExpanded, setCostExpanded] = useState(false)
  var [sgaExpanded, setSgaExpanded] = useState(false)
  var [payrollOpen, setPayrollOpen] = useState(false)
  var [investExpanded, setInvestExpanded] = useState(false)

  var revFy1 = parameters.revenue_fy1 || 1e8
  var growthRate = parameters.growth_rate || 0.3
  var cogsRate = parameters.cogs_rate || 0.3
  var opexBase = parameters.opex_base || 8e7
  var opexGrowth = parameters.opex_growth || 0.1
  var revFy5 = revFy1 * Math.pow(1 + growthRate, 4)
  var grossMargin = 1 - cogsRate
  var opexFy5 = opexBase * Math.pow(1 + opexGrowth, 4)

  var segments = plSummary?.segments
  var sgaBreakdown = plSummary?.sga_breakdown
  var sgaDetail = plSummary?.sga_detail
  var sgaTotal = sgaBreakdown ? SGA_KEYS.reduce(function(s, k) { return s + (sgaBreakdown![k][0] || 0) }, 0) : opexBase

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-blue-50 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900 text-sm">モデル全体像</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">各セクションをクリックで詳細展開 / 青字は直接編集可</p>
        </div>
        {kpis && (
          <div className="flex gap-3">
            <div className="text-center">
              <div className="text-[9px] text-gray-400">黒字化</div>
              <div className={'text-xs font-bold ' + (kpis.break_even_year ? 'text-green-700' : 'text-red-500')}>
                {kpis.break_even_year || '未達'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-[9px] text-gray-400">FY5営業利益率</div>
              <div className={'text-xs font-bold ' + ((kpis.fy5_op_margin || 0) >= 0 ? 'text-green-700' : 'text-red-500')}>
                {kpis.fy5_op_margin != null ? formatPct(kpis.fy5_op_margin) : '-'}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="px-4 py-3 space-y-1">
        {/* ═══════ 1. REVENUE ═══════ */}
        <Section
          color="bg-blue-500" label="売上高"
          summary={
            <span>
              FY1 <EV value={revFy1} display={formatYen(revFy1)} paramKey="revenue_fy1" parse={parseYenInput} onCommit={onParameterChange} />
              <span className="text-gray-400 mx-1">→</span>
              FY5 <span className="font-bold text-blue-700">{formatYen(revFy5)}</span>
              <span className="text-gray-400 ml-1.5">年率</span>
              <EV value={growthRate} display={formatPct(growthRate)} paramKey="growth_rate" parse={parsePctInput} onCommit={onParameterChange} />
            </span>
          }
          badge={plSummary ? <Spark values={plSummary.revenue} color="bg-blue-400" /> : undefined}
          expanded={revExpanded} onToggle={function() { setRevExpanded(!revExpanded) }}
        >
          <div className="bg-blue-50 rounded-lg p-3 border border-blue-100 space-y-3">
            {/* Segment cards */}
            {segments && segments.length > 0 && (
              <div>
                <div className="text-[10px] font-semibold text-blue-600 mb-2">
                  セグメント別 ({segments.length}事業)
                </div>
                {/* Composition bar */}
                <div className="h-2.5 rounded-full overflow-hidden flex mb-2">
                  {segments.map(function(seg, i) {
                    var pct = revFy1 > 0 ? (seg.revenue[0] / revFy1) * 100 : 100 / segments!.length
                    var colors = ['bg-blue-500', 'bg-indigo-400', 'bg-sky-400', 'bg-teal-400', 'bg-violet-400']
                    return <div key={i} className={colors[i % colors.length] + ' transition-all'} style={{ width: Math.max(pct, 2) + '%' }} title={seg.name + ': ' + formatYen(seg.revenue[0])} />
                  })}
                </div>
                {/* Segment detail rows */}
                <div className="space-y-2">
                  {segments.map(function(seg, i) {
                    var share = revFy1 > 0 ? seg.revenue[0] / revFy1 : 0
                    return (
                      <div key={i} className="bg-white rounded p-2 border border-blue-100">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[11px] font-medium text-gray-800">{seg.name}</span>
                          <span className="text-[10px] text-gray-400">{(share * 100).toFixed(0)}%</span>
                        </div>
                        <div className="grid grid-cols-4 gap-1 text-[10px]">
                          <div>
                            <div className="text-gray-400">FY1売上</div>
                            <div className="font-mono font-medium text-gray-800">{formatYen(seg.revenue[0])}</div>
                          </div>
                          <div>
                            <div className="text-gray-400">FY5売上</div>
                            <div className="font-mono font-medium text-blue-700">{formatYen(seg.revenue[4])}</div>
                          </div>
                          <div>
                            <div className="text-gray-400">成長率</div>
                            <div className="font-mono font-medium text-green-700">{formatPct(seg.growth_rate)}</div>
                          </div>
                          <div>
                            <div className="text-gray-400">粗利率</div>
                            <div className="font-mono font-medium text-emerald-700">{formatPct(1 - seg.cogs_rate)}</div>
                          </div>
                        </div>
                        <Spark values={seg.revenue} color="bg-blue-300" />
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
            {/* Single segment fallback */}
            {(!segments || segments.length <= 1) && (
              <div className="text-[11px] text-gray-500">
                単一セグメント: 売上 {formatYen(revFy1)} x (1+{formatPct(growthRate)})^n
              </div>
            )}
          </div>
        </Section>

        {/* Arrow */}
        <div className="flex justify-center"><div className="w-px h-3 bg-gray-200" /></div>

        {/* ═══════ 2. COGS & GROSS PROFIT ═══════ */}
        <Section
          color="bg-amber-500" label="原価・粗利"
          summary={
            <span>
              原価率 <EV value={cogsRate} display={formatPct(cogsRate)} paramKey="cogs_rate" parse={parsePctInput} onCommit={onParameterChange} />
              <span className="text-gray-400 mx-1">→</span>
              粗利率 <span className="font-bold text-emerald-700">{formatPct(grossMargin)}</span>
              {plSummary && <span className="text-gray-400 ml-1">(FY1粗利 {formatYen(plSummary.gross_profit[0])})</span>}
            </span>
          }
          badge={plSummary ? <Spark values={plSummary.gross_profit} color="bg-emerald-400" /> : undefined}
          expanded={costExpanded} onToggle={function() { setCostExpanded(!costExpanded) }}
        >
          <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
            {/* Per-segment COGS comparison */}
            {segments && segments.length > 1 && (
              <div className="space-y-1.5 mb-3">
                <div className="text-[10px] font-semibold text-amber-700 mb-1">セグメント別原価率</div>
                {segments.map(function(seg, i) {
                  return (
                    <div key={i} className="flex items-center gap-2">
                      <div className="w-20 text-[10px] text-gray-600 truncate">{seg.name}</div>
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-400 rounded-full" style={{ width: (seg.cogs_rate * 100) + '%' }} />
                      </div>
                      <div className="text-[10px] font-mono text-gray-700 w-8 text-right">{formatPct(seg.cogs_rate)}</div>
                      <div className="text-[10px] text-emerald-600 w-12 text-right">粗利{formatPct(1 - seg.cogs_rate)}</div>
                    </div>
                  )
                })}
              </div>
            )}
            {/* Gross profit 5-year */}
            {plSummary && (
              <div>
                <div className="text-[10px] font-semibold text-emerald-700 mb-1">粗利推移 (5年)</div>
                <div className="flex gap-1">
                  {['FY1','FY2','FY3','FY4','FY5'].map(function(fy, i) {
                    var gp = plSummary!.gross_profit[i] || 0
                    var rev = plSummary!.revenue[i] || 1
                    return (
                      <div key={fy} className="flex-1 text-center">
                        <div className="text-[9px] text-gray-400">{fy}</div>
                        <div className="text-[10px] font-mono font-medium text-gray-800">{formatYen(gp)}</div>
                        <div className="text-[9px] text-emerald-600">{formatPct(gp / rev)}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </Section>

        {/* Arrow */}
        <div className="flex justify-center"><div className="w-px h-3 bg-gray-200" /></div>

        {/* ═══════ 3. SGA / OPEX ═══════ */}
        <Section
          color="bg-red-500" label="販管費 (SGA)"
          summary={
            <span>
              FY1 <EV value={opexBase} display={formatYen(opexBase)} paramKey="opex_base" parse={parseYenInput} onCommit={onParameterChange} />
              <span className="text-gray-400 mx-1">→</span>
              FY5 <span className="font-bold text-red-600">{formatYen(opexFy5)}</span>
              <span className="text-gray-400 ml-1.5">年率+</span>
              <EV value={opexGrowth} display={formatPct(opexGrowth)} paramKey="opex_growth" parse={parsePctInput} onCommit={onParameterChange} />
            </span>
          }
          badge={plSummary ? <Spark values={plSummary.opex} color="bg-red-400" /> : undefined}
          expanded={sgaExpanded} onToggle={function() { setSgaExpanded(!sgaExpanded) }}
        >
          <div className="bg-red-50 rounded-lg p-3 border border-red-100 space-y-3">
            {/* Composition bar */}
            {sgaBreakdown && (
              <div>
                <div className="h-3 rounded-full overflow-hidden flex mb-1.5">
                  {SGA_KEYS.map(function(k) {
                    var val = sgaBreakdown![k][0] || 0
                    var pct = sgaTotal > 0 ? (val / sgaTotal) * 100 : 20
                    return <div key={k} className={SGA_META[k].color + ' transition-all relative group'} style={{ width: Math.max(pct, 1) + '%' }}>
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100">
                        <span className="text-[8px] text-white font-bold drop-shadow">{pct.toFixed(0)}%</span>
                      </div>
                    </div>
                  })}
                </div>

                {/* Category detail rows */}
                <div className="space-y-1">
                  {SGA_KEYS.map(function(k) {
                    var meta = SGA_META[k]
                    var vals = sgaBreakdown![k]
                    var fy1 = vals[0] || 0
                    var fy5 = vals[4] || 0
                    var pct = sgaTotal > 0 ? (fy1 / sgaTotal) * 100 : 20
                    var isPayroll = k === 'payroll'

                    return (
                      <div key={k}>
                        <div className="flex items-center gap-1.5 py-1 border-b border-red-100 last:border-0">
                          <div className={'w-2 h-2 rounded-full ' + meta.color} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1">
                              <span className="text-[11px] font-medium text-gray-700">{meta.label}</span>
                              <span className="text-[9px] text-gray-400">{pct.toFixed(0)}%</span>
                              {isPayroll && sgaDetail && (
                                <button onClick={function(e) { e.stopPropagation(); setPayrollOpen(!payrollOpen) }}
                                  className="text-[9px] text-orange-500 hover:text-orange-700 ml-0.5">
                                  {payrollOpen ? '▲' : '▼詳細'}
                                </button>
                              )}
                            </div>
                          </div>
                          <Spark values={vals} color={meta.color} />
                          <div className="text-right">
                            <div className="text-[11px] font-mono font-medium text-gray-800">{formatYen(fy1)}</div>
                            {fy5 !== fy1 && <div className="text-[9px] text-gray-400">→ {formatYen(fy5)}</div>}
                          </div>
                        </div>

                        {/* Payroll role drill-down */}
                        {isPayroll && payrollOpen && sgaDetail && (
                          <div className="ml-4 mt-1 mb-2 bg-orange-50 rounded p-2 border border-orange-100">
                            <div className="text-[10px] text-orange-700 font-semibold mb-1.5">職種別人件費 (平均年収 x 人数)</div>
                            {Object.entries(sgaDetail.payroll.roles).map(function([rk, role]) {
                              var sal = parameters['pr_' + rk + '_salary'] != null ? parameters['pr_' + rk + '_salary'] : role.salary
                              var hc = parameters['pr_' + rk + '_hc'] != null ? parameters['pr_' + rk + '_hc'] : (role.headcount[0] || 0)
                              var cost = sal * hc
                              return (
                                <div key={rk} className="flex items-center gap-1 py-0.5 border-b border-orange-100 last:border-0">
                                  <div className="w-16 text-[10px] text-gray-600 truncate">{role.label}</div>
                                  <div className="flex-1 text-[10px] font-mono text-gray-500">
                                    <EV value={sal} display={(sal / 1e4).toFixed(0) + '万'} paramKey={'pr_' + rk + '_salary'} parse={parseYenInput} onCommit={onParameterChange} />
                                    <span className="text-gray-400"> x </span>
                                    <EV value={hc} display={hc + '人'} paramKey={'pr_' + rk + '_hc'}
                                      parse={function(r) { var n = parseInt(r); return isNaN(n) ? null : n }}
                                      onCommit={onParameterChange} />
                                  </div>
                                  <div className="text-[10px] font-mono font-medium text-orange-800 w-14 text-right">
                                    {formatYen(cost)}
                                  </div>
                                  <Spark values={role.cost} color="bg-orange-300" />
                                  <div className="text-[9px] text-gray-400 w-12 text-right">
                                    →{role.headcount[4] || Math.round(hc * 1.2 ** 4)}人
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </Section>

        {/* Arrow */}
        <div className="flex justify-center"><div className="w-px h-3 bg-gray-200" /></div>

        {/* ═══════ 4. INVESTMENT / DEPRECIATION ═══════ */}
        <Section
          color="bg-slate-500" label="投資・償却"
          summary={
            plSummary && plSummary.depreciation && plSummary.capex ? (
              <span>
                CAPEX {formatYen(plSummary.capex[0])}/年
                <span className="text-gray-400 mx-1">|</span>
                償却 {formatYen(plSummary.depreciation[0])}/年
                {plSummary.depreciation[4] !== plSummary.depreciation[0] && (
                  <span className="text-gray-400"> → {formatYen(plSummary.depreciation[4])}</span>
                )}
              </span>
            ) : <span className="text-gray-400">CAPEX・減価償却なし</span>
          }
          expanded={investExpanded} onToggle={function() { setInvestExpanded(!investExpanded) }}
        >
          <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 space-y-2">
            <DetailRow label="年間CAPEX" value={formatYen(parameters.capex || 0)}
              spark={plSummary?.capex} sparkColor="bg-slate-400" />
            <DetailRow label="減価償却費" value={formatYen(parameters.depreciation || 0)}
              sub={parameters.depreciation_mode === 1 ? 'CAPEX連動(自動)' : '手動入力'}
              spark={plSummary?.depreciation} sparkColor="bg-slate-300" />
            {parameters.depreciation_mode === 1 && (
              <DetailRow label="耐用年数" value={(parameters.useful_life || 5) + '年'}
                sub={parameters.depreciation_method === 1 ? '定率法' : '定額法'} />
            )}
            {(parameters.existing_depreciation || 0) > 0 && (
              <DetailRow label="既存資産償却" value={formatYen(parameters.existing_depreciation)} />
            )}
          </div>
        </Section>

        {/* Arrow */}
        <div className="flex justify-center"><div className="w-px h-3 bg-gray-200" /></div>

        {/* ═══════ 5. PROFITABILITY & TARGETS ═══════ */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">収益性・目標</span>
          </div>

          {/* 5-year waterfall */}
          {plSummary && (
            <div className="ml-4 mb-2">
              <div className="flex gap-1">
                {['FY1','FY2','FY3','FY4','FY5'].map(function(fy, i) {
                  var op = plSummary!.operating_profit[i] || 0
                  var rev = plSummary!.revenue[i] || 1
                  var margin = op / rev
                  var barH = Math.min(Math.abs(margin) * 150, 100)
                  var pos = op >= 0
                  return (
                    <div key={fy} className="flex-1 text-center">
                      <div className="relative h-10 flex items-end justify-center">
                        <div className={'w-full rounded-t ' + (pos ? 'bg-green-400' : 'bg-red-400')}
                          style={{ height: Math.max(barH, 6) + '%' }} />
                      </div>
                      <div className="text-[9px] text-gray-400">{fy}</div>
                      <div className={'text-[9px] font-mono font-medium ' + (pos ? 'text-green-600' : 'text-red-500')}>
                        {formatYen(op)}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* KPI + Breakeven targets */}
          <div className="ml-4 bg-green-50 rounded-lg p-3 border border-green-100">
            {kpis ? (
              <div className="space-y-3">
                {/* Breakeven targets */}
                <div className="grid grid-cols-2 gap-2">
                  <BreakevenTargetSelector
                    label="単年黒字化" paramKey="target_breakeven_fy"
                    actualYear={kpis.break_even_year} targetFy={parameters.target_breakeven_fy}
                    gap={kpis.breakeven_gap} onParameterChange={onParameterChange} />
                  <BreakevenTargetSelector
                    label="累積黒字化" paramKey="target_cum_breakeven_fy"
                    actualYear={kpis.cumulative_break_even_year} targetFy={parameters.target_cum_breakeven_fy}
                    gap={kpis.cum_breakeven_gap} onParameterChange={onParameterChange} />
                </div>
                {/* Compact KPIs */}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-green-200">
                  <div className="text-center">
                    <div className="text-[9px] text-gray-400">売上CAGR</div>
                    <div className="text-xs font-bold text-gray-900">{kpis.revenue_cagr != null ? formatPct(kpis.revenue_cagr) : '-'}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[9px] text-gray-400">粗利率</div>
                    <div className="text-xs font-bold text-gray-900">{kpis.gp_margin != null ? formatPct(kpis.gp_margin) : '-'}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[9px] text-gray-400">FY5営業利益率</div>
                    <div className={'text-xs font-bold ' + ((kpis.fy5_op_margin || 0) >= 0 ? 'text-green-700' : 'text-red-500')}>
                      {kpis.fy5_op_margin != null ? formatPct(kpis.fy5_op_margin) : '-'}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-gray-400">パラメータを調整するとKPIが表示されます</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── BreakevenTargetSelector (unchanged) ───────────────────
function BreakevenTargetSelector({
  label, paramKey, actualYear, targetFy, gap, onParameterChange,
}: {
  label: string; paramKey: string; actualYear?: string | null; targetFy?: number
  gap?: BreakevenGapData | null; onParameterChange: (key: string, value: number) => void
}) {
  var actualFy = actualYear ? parseInt(actualYear.replace('FY', ''), 10) : null
  var currentTarget = targetFy || 0
  var hasTarget = currentTarget >= 1 && currentTarget <= 5
  var achieved = gap ? gap.achieved : (actualFy !== null && hasTarget && actualFy <= currentTarget)
  var opexChangePct = gap?.required_opex_change_pct

  return (
    <div className="bg-white rounded-lg p-2 border border-green-200">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-medium text-gray-700">{label}</span>
        <span className={'text-[10px] font-bold ' + (actualFy ? 'text-green-700' : 'text-red-500')}>
          {actualFy ? 'FY' + actualFy : '未達'}
        </span>
      </div>
      <div className="flex gap-0.5 mb-1">
        {[1,2,3,4,5].map(function(fy) {
          var isTarget = currentTarget === fy
          var isActual = actualFy === fy
          var cls = 'flex-1 py-0.5 text-[9px] rounded border transition-all '
          if (isTarget && achieved) cls += 'bg-green-500 text-white border-green-500 font-bold'
          else if (isTarget) cls += 'bg-amber-400 text-white border-amber-400 font-bold'
          else if (isActual) cls += 'bg-green-100 text-green-700 border-green-300 font-medium'
          else cls += 'bg-gray-50 text-gray-500 border-gray-200 hover:border-gray-400'
          return <button key={fy} onClick={function() { onParameterChange(paramKey, fy) }} className={cls}>{fy}</button>
        })}
      </div>
      {hasTarget && (
        <div className="text-[9px]">
          {achieved ? (
            <span className="text-green-600 font-medium">目標達成</span>
          ) : (
            <div>
              <span className="text-amber-600">{actualFy ? '実績FY' + actualFy + ' (' + (actualFy - currentTarget) + '年遅延)' : '5年間未達'}</span>
              {opexChangePct != null && opexChangePct < 0 && (
                <span className="text-red-500 ml-1">販管費{Math.abs(opexChangePct * 100).toFixed(0)}%削減要</span>
              )}
            </div>
          )}
        </div>
      )}
      {!hasTarget && <div className="text-[9px] text-gray-400">FYを選択して目標設定</div>}
    </div>
  )
}
