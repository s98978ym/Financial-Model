'use client'

import { useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface ScenarioComparisonProps {
  projectId: string
  parameters: Record<string, number>
  onCompletionChange?: (status: Record<string, boolean>) => void
}

function prepareParams(p: Record<string, number>): Record<string, any> {
  var out: Record<string, any> = {}
  Object.keys(p).forEach(function (key) {
    if (key === 'depreciation_mode') {
      out[key] = p[key] === 1 ? 'auto' : 'manual'
    } else if (key === 'depreciation_method') {
      out[key] = p[key] === 1 ? 'declining_balance' : 'straight_line'
    } else {
      out[key] = p[key]
    }
  })
  return out
}

/** A scenario is "complete" when recalc returns valid KPI data without errors */
function isScenarioComplete(data: any, error: any, isFetching: boolean): boolean {
  if (error || isFetching || !data) return false
  return !!(data.kpis && data.pl_summary?.revenue?.length > 0)
}

function CompletionBadge({ complete, loading }: { complete: boolean; loading: boolean }) {
  if (loading) {
    return <span className="inline-flex items-center gap-1 text-[11px] text-gold-500 animate-pulse">...</span>
  }
  if (complete) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-medium">
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        完了
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cream-200 text-sand-500 text-[11px] font-medium">
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="9" />
      </svg>
      未完了
    </span>
  )
}

export function ScenarioComparison({ projectId, parameters, onCompletionChange }: ScenarioComparisonProps) {
  var prepared = useMemo(() => prepareParams(parameters), [parameters])

  // Fetch all three scenarios in parallel
  const { data: baseData, error: baseError, isFetching: baseFetching } = useQuery({
    queryKey: ['recalc', projectId, 'base', prepared],
    queryFn: () => api.recalc({ project_id: projectId, parameters: prepared, scenario: 'base' }),
    staleTime: 30_000,
    retry: 2,
  })

  const { data: bestData, error: bestError, isFetching: bestFetching } = useQuery({
    queryKey: ['recalc', projectId, 'best', prepared],
    queryFn: () => api.recalc({ project_id: projectId, parameters: prepared, scenario: 'best' }),
    staleTime: 30_000,
    retry: 2,
  })

  const { data: worstData, error: worstError, isFetching: worstFetching } = useQuery({
    queryKey: ['recalc', projectId, 'worst', prepared],
    queryFn: () => api.recalc({ project_id: projectId, parameters: prepared, scenario: 'worst' }),
    staleTime: 30_000,
    retry: 2,
  })

  const scenarioError = baseError || bestError || worstError
  const isLoading = baseFetching || bestFetching || worstFetching

  const baseComplete = isScenarioComplete(baseData, baseError, baseFetching)
  const bestComplete = isScenarioComplete(bestData, bestError, bestFetching)
  const worstComplete = isScenarioComplete(worstData, worstError, worstFetching)

  // Notify parent of completion status changes
  useEffect(function() {
    if (onCompletionChange) {
      onCompletionChange({ base: baseComplete, best: bestComplete, worst: worstComplete })
    }
  }, [baseComplete, bestComplete, worstComplete, onCompletionChange])

  const formatYen = (v: number | undefined) => {
    if (v == null) return '-'
    if (Math.abs(v) >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}億`
    if (Math.abs(v) >= 10_000) return `${(v / 10_000).toFixed(0)}万`
    return v.toLocaleString()
  }

  const rows = [
    { label: '売上 FY5', key: 'revenue', idx: 4 },
    { label: '営業利益 FY5', key: 'operating_profit', idx: 4 },
    { label: '累積FCF FY5', key: 'cumulative_fcf', idx: 4 },
  ]

  return (
    <div className="bg-white rounded-3xl shadow-warm overflow-hidden">
      <div className="px-5 py-3 border-b border-cream-200 flex items-center justify-between">
        <h3 className="font-medium text-dark-900">シナリオ比較</h3>
        {isLoading && (
          <span className="text-xs text-gold-500 animate-pulse">計算中...</span>
        )}
      </div>
      {scenarioError && (
        <div className="px-4 py-2 bg-red-50/50 border-b border-red-100 text-xs text-red-600">
          シナリオ計算エラー: {(scenarioError as Error).message}
        </div>
      )}
      <table className="w-full text-sm">
        <thead className="bg-cream-100">
          <tr>
            <th className="text-left px-4 py-2 text-sand-500 font-medium">KPI</th>
            <th className="text-right px-4 py-2 text-dark-900 font-medium">Base</th>
            <th className="text-right px-4 py-2 text-green-600 font-medium">Best</th>
            <th className="text-right px-4 py-2 text-red-600 font-medium">Worst</th>
            <th className="text-right px-4 py-2 text-sand-500 font-medium">Delta (B-W)</th>
          </tr>
        </thead>
        <tbody className={isLoading ? 'opacity-50 transition-opacity' : 'transition-opacity'}>
          {/* Completion status row */}
          <tr className="border-t border-cream-200 bg-cream-100">
            <td className="px-4 py-2 text-sand-600 font-medium">設定状況</td>
            <td className="px-4 py-2 text-right">
              <CompletionBadge complete={baseComplete} loading={baseFetching} />
            </td>
            <td className="px-4 py-2 text-right">
              <CompletionBadge complete={bestComplete} loading={bestFetching} />
            </td>
            <td className="px-4 py-2 text-right">
              <CompletionBadge complete={worstComplete} loading={worstFetching} />
            </td>
            <td className="px-4 py-2 text-right">
              {baseComplete && bestComplete && worstComplete ? (
                <span className="text-[11px] text-green-600 font-medium">全シナリオ完了</span>
              ) : (
                <span className="text-[11px] text-sand-400">
                  {[baseComplete, bestComplete, worstComplete].filter(Boolean).length}/3 完了
                </span>
              )}
            </td>
          </tr>
          {rows.map((row) => {
            const baseVal = baseData?.pl_summary?.[row.key]?.[row.idx]
            const bestVal = bestData?.pl_summary?.[row.key]?.[row.idx]
            const worstVal = worstData?.pl_summary?.[row.key]?.[row.idx]
            const delta = bestVal != null && worstVal != null ? bestVal - worstVal : undefined

            return (
              <tr key={row.key} className="border-t border-cream-200">
                <td className="px-4 py-2 text-dark-900">{row.label}</td>
                <td className="px-4 py-2 text-right font-mono">{formatYen(baseVal)}</td>
                <td className="px-4 py-2 text-right font-mono text-green-700">{formatYen(bestVal)}</td>
                <td className="px-4 py-2 text-right font-mono text-red-700">{formatYen(worstVal)}</td>
                <td className="px-4 py-2 text-right font-mono text-sand-500">
                  {delta != null ? `+${formatYen(delta)}` : '-'}
                </td>
              </tr>
            )
          })}
          {/* KPI rows */}
          <tr className="border-t border-cream-200 bg-cream-100">
            <td className="px-4 py-2 text-dark-900">黒字化年度</td>
            <td className="px-4 py-2 text-right font-mono">{baseData?.kpis?.break_even_year || '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-green-700">{bestData?.kpis?.break_even_year || '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-red-700">{worstData?.kpis?.break_even_year || '-'}</td>
            <td className="px-4 py-2 text-right text-sand-400">-</td>
          </tr>
          <tr className="border-t border-cream-200 bg-cream-100">
            <td className="px-4 py-2 text-dark-900">売上 CAGR</td>
            <td className="px-4 py-2 text-right font-mono">{baseData?.kpis?.revenue_cagr != null ? `${(baseData.kpis.revenue_cagr * 100).toFixed(0)}%` : '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-green-700">{bestData?.kpis?.revenue_cagr != null ? `${(bestData.kpis.revenue_cagr * 100).toFixed(0)}%` : '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-red-700">{worstData?.kpis?.revenue_cagr != null ? `${(worstData.kpis.revenue_cagr * 100).toFixed(0)}%` : '-'}</td>
            <td className="px-4 py-2 text-right text-sand-400">-</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
