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

function formatYen(v: number): string {
  if (Math.abs(v) >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(v) >= 10_000) return (v / 10_000).toFixed(0) + '万円'
  return v.toLocaleString() + '円'
}

function formatPct(v: number): string {
  return (v * 100).toFixed(0) + '%'
}

/** Inline editable value component */
function EditableValue({
  value,
  displayValue,
  paramKey,
  parseInput,
  onCommit,
}: {
  value: number
  displayValue: string
  paramKey: string
  parseInput: (raw: string) => number | null
  onCommit: (key: string, value: number) => void
}) {
  var [editing, setEditing] = useState(false)
  var [draft, setDraft] = useState('')
  var inputRef = useRef<HTMLInputElement>(null)

  useEffect(function() {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  function handleClick() {
    setDraft(displayValue)
    setEditing(true)
  }

  function handleBlur() {
    var parsed = parseInput(draft)
    if (parsed !== null && !isNaN(parsed)) {
      onCommit(paramKey, parsed)
    }
    setEditing(false)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      (e.target as HTMLInputElement).blur()
    } else if (e.key === 'Escape') {
      setEditing(false)
    }
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={function(e) { setDraft(e.target.value) }}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="inline-block w-24 px-1.5 py-0.5 text-sm font-bold text-blue-700 bg-blue-50 border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
    )
  }

  return (
    <button
      onClick={handleClick}
      className="inline-block px-1.5 py-0.5 text-sm font-bold text-blue-700 bg-blue-50 rounded border border-transparent hover:border-blue-300 hover:bg-blue-100 cursor-pointer transition-colors"
      title="クリックして編集"
    >
      {displayValue}
    </button>
  )
}

function parseYenInput(raw: string): number | null {
  var cleaned = raw.replace(/[,\s円]/g, '')
  if (cleaned.includes('億')) {
    var num = parseFloat(cleaned.replace('億', ''))
    return isNaN(num) ? null : num * 100_000_000
  }
  if (cleaned.includes('万')) {
    var num2 = parseFloat(cleaned.replace('万', ''))
    return isNaN(num2) ? null : num2 * 10_000
  }
  var result = parseFloat(cleaned)
  return isNaN(result) ? null : result
}

function parsePctInput(raw: string): number | null {
  var cleaned = raw.replace(/[%％\s]/g, '')
  var num = parseFloat(cleaned)
  if (isNaN(num)) return null
  return num > 1 ? num / 100 : num
}

var SGA_LABELS: Record<string, string> = {
  payroll: '人件費',
  marketing: 'マーケ',
  office: 'オフィス',
  system: 'システム',
  other: 'その他',
}

var SGA_COLORS: Record<string, string> = {
  payroll: 'bg-orange-400',
  marketing: 'bg-purple-400',
  office: 'bg-gray-400',
  system: 'bg-cyan-400',
  other: 'bg-gray-300',
}

export function ModelOverview({ parameters, kpis, plSummary, industry, onParameterChange }: ModelOverviewProps) {
  var industryInfo = INDUSTRY_BENCHMARKS[industry]
  var revFy1 = parameters.revenue_fy1 || 100_000_000
  var growthRate = parameters.growth_rate || 0.3
  var cogsRate = parameters.cogs_rate || 0.3
  var opexBase = parameters.opex_base || 80_000_000
  var opexGrowth = parameters.opex_growth || 0.1

  // Calculate derived values for display
  var revFy5 = revFy1 * Math.pow(1 + growthRate, 4)
  var grossMargin = 1 - cogsRate
  var opexFy5 = opexBase * Math.pow(1 + opexGrowth, 4)

  var segments = plSummary?.segments
  var hasMultipleSegments = segments && segments.length > 1
  var sgaBreakdown = plSummary?.sga_breakdown
  var sgaDetail = plSummary?.sga_detail

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-blue-50">
        <h3 className="font-medium text-gray-900 text-sm">モデル全体像</h3>
        <p className="text-xs text-gray-500 mt-0.5">数値をクリックして直接編集できます</p>
      </div>

      {/* Visual Flow Diagram */}
      <div className="px-5 py-4">
        {/* Revenue Structure */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">収益構造</span>
          </div>
          <div className="ml-4 bg-blue-50 rounded-lg p-3 border border-blue-100">
            <p className="text-sm text-gray-700 leading-relaxed">
              初年度売上{' '}
              <EditableValue
                value={revFy1}
                displayValue={formatYen(revFy1)}
                paramKey="revenue_fy1"
                parseInput={parseYenInput}
                onCommit={onParameterChange}
              />
              {' '}から年率{' '}
              <EditableValue
                value={growthRate}
                displayValue={formatPct(growthRate)}
                paramKey="growth_rate"
                parseInput={parsePctInput}
                onCommit={onParameterChange}
              />
              {' '}で成長し、FY5には{' '}
              <span className="font-bold text-blue-700">{formatYen(revFy5)}</span>
              {' '}に到達する見込みです。
            </p>

            {/* Segment breakdown */}
            {hasMultipleSegments && (
              <div className="mt-3 pt-2 border-t border-blue-200">
                <div className="text-[11px] text-blue-600 font-medium mb-1.5">セグメント別売上（FY1→FY5）</div>
                <div className="space-y-1">
                  {segments!.map(function(seg, i) {
                    var revShare = revFy1 > 0 ? (seg.revenue[0] / revFy1) * 100 : 0
                    return (
                      <div key={i} className="flex items-center gap-2">
                        <div className="w-20 text-[11px] text-gray-600 truncate">{seg.name}</div>
                        <div className="flex-1 h-2 bg-blue-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-400 rounded-full"
                            style={{ width: Math.min(revShare, 100) + '%' }}
                          />
                        </div>
                        <div className="text-[11px] font-mono text-gray-700 w-16 text-right">
                          {formatYen(seg.revenue[0])}
                        </div>
                        <div className="text-[10px] text-gray-400">→</div>
                        <div className="text-[11px] font-mono text-blue-700 w-16 text-right">
                          {formatYen(seg.revenue[4])}
                        </div>
                        <div className="text-[10px] text-green-600 w-10 text-right">
                          粗利{((1 - seg.cogs_rate) * 100).toFixed(0)}%
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center my-1">
          <div className="w-px h-4 bg-gray-300" />
        </div>

        {/* Cost Structure */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">コスト構造</span>
          </div>
          <div className="ml-4 bg-red-50 rounded-lg p-3 border border-red-100">
            <p className="text-sm text-gray-700 leading-relaxed">
              売上原価率{' '}
              <EditableValue
                value={cogsRate}
                displayValue={formatPct(cogsRate)}
                paramKey="cogs_rate"
                parseInput={parsePctInput}
                onCommit={onParameterChange}
              />
              {' '}(粗利率 {formatPct(grossMargin)})。
              販管費は初年度{' '}
              <EditableValue
                value={opexBase}
                displayValue={formatYen(opexBase)}
                paramKey="opex_base"
                parseInput={parseYenInput}
                onCommit={onParameterChange}
              />
              {' '}から年率{' '}
              <EditableValue
                value={opexGrowth}
                displayValue={formatPct(opexGrowth)}
                paramKey="opex_growth"
                parseInput={parsePctInput}
                onCommit={onParameterChange}
              />
              {' '}で増加し、FY5には{' '}
              <span className="font-bold text-red-600">{formatYen(opexFy5)}</span>
              {' '}になります。
            </p>

            {/* SGA breakdown bar */}
            {sgaBreakdown != null && (
              <SGABreakdownBar breakdown={sgaBreakdown} detail={sgaDetail} />
            )}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center my-1">
          <div className="w-px h-4 bg-gray-300" />
        </div>

        {/* Profit / KPI Summary with Breakeven Targets */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">収益性・目標設定</span>
          </div>
          <div className="ml-4 bg-green-50 rounded-lg p-3 border border-green-100">
            {kpis ? (
              <div className="space-y-3">
                {/* Breakeven target selectors */}
                <div className="grid grid-cols-2 gap-3">
                  <BreakevenTargetSelector
                    label="単年黒字化"
                    paramKey="target_breakeven_fy"
                    actualYear={kpis.break_even_year}
                    targetFy={parameters.target_breakeven_fy}
                    gap={kpis.breakeven_gap}
                    onParameterChange={onParameterChange}
                  />
                  <BreakevenTargetSelector
                    label="累積黒字化"
                    paramKey="target_cum_breakeven_fy"
                    actualYear={kpis.cumulative_break_even_year}
                    targetFy={parameters.target_cum_breakeven_fy}
                    gap={kpis.cum_breakeven_gap}
                    onParameterChange={onParameterChange}
                  />
                </div>

                {/* Compact KPI row */}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-green-200">
                  <div className="text-center">
                    <div className="text-[10px] text-gray-500">売上CAGR</div>
                    <div className="text-sm font-bold text-gray-900">
                      {kpis.revenue_cagr != null ? formatPct(kpis.revenue_cagr) : '-'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-gray-500">粗利率</div>
                    <div className="text-sm font-bold text-gray-900">
                      {kpis.gp_margin != null ? formatPct(kpis.gp_margin) : '-'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-gray-500">FY5営業利益率</div>
                    <div className={'text-sm font-bold ' + ((kpis.fy5_op_margin || 0) >= 0 ? 'text-green-700' : 'text-red-500')}>
                      {kpis.fy5_op_margin != null ? formatPct(kpis.fy5_op_margin) : '-'}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">パラメータを調整するとKPIが表示されます</p>
            )}
          </div>
        </div>

        {/* 5-Year Mini Waterfall */}
        {plSummary && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="text-xs font-medium text-gray-500 mb-2">5年間P&Lサマリー</div>
            <div className="flex gap-1.5">
              {['FY1', 'FY2', 'FY3', 'FY4', 'FY5'].map(function(fy, i) {
                var op = plSummary.operating_profit[i] || 0
                var rev = plSummary.revenue[i] || 1
                var margin = op / rev
                var barHeight = Math.min(Math.abs(margin) * 100, 60)
                var isPositive = op >= 0

                return (
                  <div key={fy} className="flex-1 text-center">
                    <div className="relative h-12 flex items-end justify-center">
                      <div
                        className={'w-full rounded-t ' + (isPositive ? 'bg-green-400' : 'bg-red-400')}
                        style={{ height: Math.max(barHeight, 4) + '%' }}
                      />
                    </div>
                    <div className="text-[10px] text-gray-500 mt-0.5">{fy}</div>
                    <div className={'text-[10px] font-medium ' + (isPositive ? 'text-green-600' : 'text-red-500')}>
                      {formatPct(margin)}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Depreciation & CAPEX summary */}
            {plSummary.depreciation && plSummary.capex && (
              <div className="mt-2 pt-2 border-t border-gray-50 flex gap-4 text-[10px] text-gray-500">
                <div>
                  減価償却: {formatYen(plSummary.depreciation[0])}
                  {plSummary.depreciation[4] !== plSummary.depreciation[0] && (
                    <span> → {formatYen(plSummary.depreciation[4])}</span>
                  )}
                </div>
                <div>
                  CAPEX: {formatYen(plSummary.capex[0])}/年
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/** Breakeven target FY selector with gap analysis */
function BreakevenTargetSelector({
  label,
  paramKey,
  actualYear,
  targetFy,
  gap,
  onParameterChange,
}: {
  label: string
  paramKey: string
  actualYear?: string | null
  targetFy?: number
  gap?: BreakevenGapData | null
  onParameterChange: (key: string, value: number) => void
}) {
  var actualFy = actualYear ? parseInt(actualYear.replace('FY', ''), 10) : null
  var currentTarget = targetFy || 0  // 0 = not set

  // Status determination
  var hasTarget = currentTarget >= 1 && currentTarget <= 5
  var achieved = gap ? gap.achieved : (actualFy !== null && hasTarget && actualFy <= currentTarget)
  var opexChangePct = gap?.required_opex_change_pct

  return (
    <div className="bg-white rounded-lg p-2.5 border border-green-200">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11px] font-medium text-gray-700">{label}</span>
        <span className={'text-xs font-bold ' + (actualFy ? 'text-green-700' : 'text-red-500')}>
          {actualFy ? 'FY' + actualFy : '未達'}
        </span>
      </div>

      {/* FY selector buttons */}
      <div className="flex gap-1 mb-1.5">
        {[1, 2, 3, 4, 5].map(function(fy) {
          var isTarget = currentTarget === fy
          var isActual = actualFy === fy
          var isPast = actualFy !== null && fy > actualFy  // already profitable before this FY

          var btnClass = 'flex-1 py-1 text-[10px] rounded border transition-all '
          if (isTarget && achieved) {
            btnClass += 'bg-green-500 text-white border-green-500 font-bold'
          } else if (isTarget && !achieved) {
            btnClass += 'bg-amber-400 text-white border-amber-400 font-bold'
          } else if (isActual) {
            btnClass += 'bg-green-100 text-green-700 border-green-300 font-medium'
          } else {
            btnClass += 'bg-gray-50 text-gray-500 border-gray-200 hover:border-gray-400 hover:bg-gray-100'
          }

          return (
            <button
              key={fy}
              onClick={function() { onParameterChange(paramKey, fy) }}
              className={btnClass}
              title={
                isActual ? 'FY' + fy + '（実績）'
                : isTarget ? 'FY' + fy + '（目標）'
                : 'FY' + fy + 'を目標に設定'
              }
            >
              {fy}
            </button>
          )
        })}
      </div>

      {/* Status indicator */}
      {hasTarget && (
        <div className="text-[10px]">
          {achieved ? (
            <span className="text-green-600 font-medium">
              目標達成 (FY{currentTarget}以前に黒字化)
            </span>
          ) : (
            <div>
              <span className="text-amber-600 font-medium">
                目標FY{currentTarget}
                {actualFy ? ' — 実績FY' + actualFy + ' (' + (actualFy - currentTarget) + '年遅延)' : ' — 5年間未達'}
              </span>
              {opexChangePct != null && opexChangePct < 0 && (
                <div className="text-red-500 mt-0.5">
                  達成には販管費を{Math.abs(opexChangePct * 100).toFixed(0)}%削減が必要
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* No target set hint */}
      {!hasTarget && (
        <div className="text-[10px] text-gray-400">
          FYボタンで目標年度を設定
        </div>
      )}
    </div>
  )
}

function SGABreakdownBar({ breakdown, detail }: { breakdown: SGABreakdown; detail?: SGADetail }) {
  var cats = ['payroll', 'marketing', 'office', 'system', 'other'] as const
  var total = cats.reduce(function(s: number, cat) { return s + (breakdown[cat][0] || 0) }, 0)

  var payrollRoles = detail?.payroll?.roles
  var hasRoles = payrollRoles && Object.keys(payrollRoles).length > 0

  return (
    <div className="mt-3 pt-2 border-t border-red-200">
      <div className="text-[11px] text-red-600 font-medium mb-1.5">販管費内訳（FY1）</div>
      <div className="h-4 rounded-full overflow-hidden flex mb-1">
        {cats.map(function(cat) {
          var val = breakdown[cat][0] || 0
          var pct = total > 0 ? (val / total) * 100 : 20
          return (
            <div
              key={cat}
              className={SGA_COLORS[cat] + ' transition-all relative group'}
              style={{ width: pct + '%' }}
            >
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-[9px] text-white font-bold drop-shadow">{pct.toFixed(0)}%</span>
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {cats.map(function(cat) {
          var val = breakdown[cat][0] || 0
          return (
            <div key={cat} className="flex items-center gap-1">
              <div className={'w-1.5 h-1.5 rounded-full ' + SGA_COLORS[cat]} />
              <span className="text-[10px] text-gray-500">{SGA_LABELS[cat]}</span>
              <span className="text-[10px] font-mono text-gray-700">{formatYen(val)}</span>
            </div>
          )
        })}
      </div>

      {/* Role-level payroll detail */}
      {hasRoles && (
        <div className="mt-2 pt-1.5 border-t border-red-100">
          <div className="text-[10px] text-orange-600 font-medium mb-1">人件費: 平均年収 x 人数</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {Object.entries(payrollRoles!).map(function([key, role]) {
              return (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-500">{role.label}</span>
                  <span className="text-[10px] font-mono text-gray-600">
                    {(role.salary / 10_000).toFixed(0)}万 x {role.headcount[0] || 0}人
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
