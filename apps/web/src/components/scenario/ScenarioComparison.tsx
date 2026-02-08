'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface ScenarioComparisonProps {
  projectId: string
  parameters: Record<string, number>
}

export function ScenarioComparison({ projectId, parameters }: ScenarioComparisonProps) {
  // Fetch all three scenarios in parallel
  const { data: baseData } = useQuery({
    queryKey: ['recalc', projectId, 'base', parameters],
    queryFn: () => api.recalc({ project_id: projectId, parameters, scenario: 'base' }),
    staleTime: 5000,
  })

  const { data: bestData } = useQuery({
    queryKey: ['recalc', projectId, 'best', parameters],
    queryFn: () => api.recalc({ project_id: projectId, parameters, scenario: 'best' }),
    staleTime: 5000,
  })

  const { data: worstData } = useQuery({
    queryKey: ['recalc', projectId, 'worst', parameters],
    queryFn: () => api.recalc({ project_id: projectId, parameters, scenario: 'worst' }),
    staleTime: 5000,
  })

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
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="font-medium text-gray-900">シナリオ比較</h3>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-4 py-2 text-gray-500 font-medium">KPI</th>
            <th className="text-right px-4 py-2 text-blue-600 font-medium">Base</th>
            <th className="text-right px-4 py-2 text-green-600 font-medium">Best</th>
            <th className="text-right px-4 py-2 text-red-600 font-medium">Worst</th>
            <th className="text-right px-4 py-2 text-gray-500 font-medium">Delta (B-W)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const baseVal = baseData?.pl_summary?.[row.key]?.[row.idx]
            const bestVal = bestData?.pl_summary?.[row.key]?.[row.idx]
            const worstVal = worstData?.pl_summary?.[row.key]?.[row.idx]
            const delta = bestVal != null && worstVal != null ? bestVal - worstVal : undefined

            return (
              <tr key={row.key} className="border-t border-gray-100">
                <td className="px-4 py-2 text-gray-700">{row.label}</td>
                <td className="px-4 py-2 text-right font-mono">{formatYen(baseVal)}</td>
                <td className="px-4 py-2 text-right font-mono text-green-700">{formatYen(bestVal)}</td>
                <td className="px-4 py-2 text-right font-mono text-red-700">{formatYen(worstVal)}</td>
                <td className="px-4 py-2 text-right font-mono text-gray-500">
                  {delta != null ? `+${formatYen(delta)}` : '-'}
                </td>
              </tr>
            )
          })}
          {/* KPI rows */}
          <tr className="border-t border-gray-200 bg-gray-50">
            <td className="px-4 py-2 text-gray-700">黒字化年度</td>
            <td className="px-4 py-2 text-right font-mono">{baseData?.kpis?.break_even_year || '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-green-700">{bestData?.kpis?.break_even_year || '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-red-700">{worstData?.kpis?.break_even_year || '-'}</td>
            <td className="px-4 py-2 text-right text-gray-400">-</td>
          </tr>
          <tr className="border-t border-gray-100 bg-gray-50">
            <td className="px-4 py-2 text-gray-700">売上 CAGR</td>
            <td className="px-4 py-2 text-right font-mono">{baseData?.kpis?.revenue_cagr != null ? `${(baseData.kpis.revenue_cagr * 100).toFixed(0)}%` : '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-green-700">{bestData?.kpis?.revenue_cagr != null ? `${(bestData.kpis.revenue_cagr * 100).toFixed(0)}%` : '-'}</td>
            <td className="px-4 py-2 text-right font-mono text-red-700">{worstData?.kpis?.revenue_cagr != null ? `${(worstData.kpis.revenue_cagr * 100).toFixed(0)}%` : '-'}</td>
            <td className="px-4 py-2 text-right text-gray-400">-</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
