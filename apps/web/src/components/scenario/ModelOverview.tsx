'use client'

import { useState, useRef, useEffect } from 'react'
import type { IndustryKey } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS } from '@/data/industryBenchmarks'

interface ModelOverviewProps {
  parameters: Record<string, number>
  kpis?: {
    break_even_year?: string | null
    revenue_cagr?: number
    fy5_op_margin?: number
  }
  plSummary?: {
    revenue: number[]
    cogs: number[]
    gross_profit: number[]
    opex: number[]
    operating_profit: number[]
    fcf: number[]
    cumulative_fcf: number[]
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
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center my-1">
          <div className="w-px h-4 bg-gray-300" />
        </div>

        {/* Profit / KPI Summary */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">収益性</span>
          </div>
          <div className="ml-4 bg-green-50 rounded-lg p-3 border border-green-100">
            {kpis ? (
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="text-xs text-gray-500 mb-0.5">黒字化</div>
                  <div className={'text-sm font-bold ' + (kpis.break_even_year ? 'text-green-700' : 'text-red-500')}>
                    {kpis.break_even_year || '未達'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-0.5">売上CAGR</div>
                  <div className="text-sm font-bold text-gray-900">
                    {kpis.revenue_cagr != null ? formatPct(kpis.revenue_cagr) : '-'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-0.5">FY5営業利益率</div>
                  <div className={'text-sm font-bold ' + ((kpis.fy5_op_margin || 0) >= 0 ? 'text-green-700' : 'text-red-500')}>
                    {kpis.fy5_op_margin != null ? formatPct(kpis.fy5_op_margin) : '-'}
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
          </div>
        )}
      </div>
    </div>
  )
}
