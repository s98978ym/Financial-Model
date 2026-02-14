'use client'

import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

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

interface PLChartProps {
  data?: {
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
  }
  kpis?: {
    break_even_year?: string | null
    revenue_cagr?: number
    fy5_op_margin?: number
    gp_margin?: number
  }
}

const YEARS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

const SEGMENT_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ef4444', '#22c55e']

const SGA_COLORS = {
  payroll: '#f97316',
  marketing: '#a855f7',
  office: '#6b7280',
  system: '#0ea5e9',
  other: '#d1d5db',
}

const SGA_LABELS: Record<string, string> = {
  payroll: '人件費',
  marketing: 'マーケティング',
  office: 'オフィス・管理',
  system: 'システム・開発',
  other: 'その他',
}

const formatYen = (value: number) => {
  if (Math.abs(value) >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}億`
  if (Math.abs(value) >= 10_000) return `${(value / 10_000).toFixed(0)}万`
  return value.toLocaleString()
}

export function PLChart({ data, kpis }: PLChartProps) {
  var [view, setView] = useState<'pl' | 'segments' | 'sga'>('pl')

  if (!data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 flex items-center justify-center h-80">
        <p className="text-gray-400">パラメータを調整するとグラフが表示されます</p>
      </div>
    )
  }

  var hasSegments = data.segments && data.segments.length > 1
  var hasSGA = data.sga_breakdown && Object.values(data.sga_breakdown).some(function(arr) {
    return arr.some(function(v) { return v > 0 })
  })

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      {/* KPI Summary */}
      {kpis && (
        <div className="flex gap-6 mb-4 text-sm">
          {kpis.break_even_year && (
            <div>
              <span className="text-gray-500">黒字化: </span>
              <span className="font-bold text-green-700">{kpis.break_even_year}</span>
            </div>
          )}
          {kpis.revenue_cagr != null && (
            <div>
              <span className="text-gray-500">売上CAGR: </span>
              <span className="font-bold">{(kpis.revenue_cagr * 100).toFixed(0)}%</span>
            </div>
          )}
          {kpis.gp_margin != null && (
            <div>
              <span className="text-gray-500">粗利率: </span>
              <span className="font-bold">{(kpis.gp_margin * 100).toFixed(0)}%</span>
            </div>
          )}
          {kpis.fy5_op_margin != null && (
            <div>
              <span className="text-gray-500">FY5営業利益率: </span>
              <span className="font-bold">{(kpis.fy5_op_margin * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      )}

      {/* View Toggle */}
      <div className="flex bg-gray-100 rounded-lg p-0.5 mb-4">
        <button
          onClick={function() { setView('pl') }}
          className={'px-3 py-1.5 text-xs rounded-md transition-colors ' + (
            view === 'pl'
              ? 'bg-white text-gray-800 shadow-sm font-medium'
              : 'text-gray-500 hover:text-gray-700'
          )}
        >
          PL全体
        </button>
        {hasSegments && (
          <button
            onClick={function() { setView('segments') }}
            className={'px-3 py-1.5 text-xs rounded-md transition-colors ' + (
              view === 'segments'
                ? 'bg-white text-gray-800 shadow-sm font-medium'
                : 'text-gray-500 hover:text-gray-700'
            )}
          >
            セグメント別売上
          </button>
        )}
        {hasSGA && (
          <button
            onClick={function() { setView('sga') }}
            className={'px-3 py-1.5 text-xs rounded-md transition-colors ' + (
              view === 'sga'
                ? 'bg-white text-gray-800 shadow-sm font-medium'
                : 'text-gray-500 hover:text-gray-700'
            )}
          >
            販管費内訳
          </button>
        )}
      </div>

      {/* PL Chart */}
      {view === 'pl' && <PLBarChart data={data} />}

      {/* Segment Revenue Chart */}
      {view === 'segments' && data.segments && (
        <SegmentChart segments={data.segments} />
      )}

      {/* SGA Breakdown Chart */}
      {view === 'sga' && data.sga_breakdown && (
        <SGAChart breakdown={data.sga_breakdown} />
      )}

      {/* Segment Summary Table */}
      {hasSegments && view === 'pl' && (
        <SegmentSummaryTable segments={data.segments!} totalRevenue={data.revenue} totalGP={data.gross_profit} />
      )}
    </div>
  )
}

function PLBarChart({ data }: { data: PLChartProps['data'] }) {
  if (!data) return null

  var chartData = YEARS.map(function(year, i) {
    return {
      name: year,
      revenue: data.revenue[i] || 0,
      opex: -(data.opex[i] || 0),
      cogs: -(data.cogs[i] || 0),
      operating_profit: data.operating_profit[i] || 0,
      cumulative_fcf: data.cumulative_fcf[i] || 0,
    }
  })

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} stackOffset="sign">
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" />
        <YAxis tickFormatter={formatYen} width={70} />
        <Tooltip
          formatter={function(value: number, name: string) {
            return [
              formatYen(Math.abs(value)),
              name === 'revenue' ? '売上' :
              name === 'cogs' ? '原価' :
              name === 'opex' ? 'OPEX' :
              name === 'operating_profit' ? '営業利益' :
              name === 'cumulative_fcf' ? '累積FCF' : name,
            ]
          }}
        />
        <Legend
          formatter={function(value) {
            return value === 'revenue' ? '売上' :
              value === 'cogs' ? '原価' :
              value === 'opex' ? 'OPEX' :
              value === 'operating_profit' ? '営業利益' :
              value === 'cumulative_fcf' ? '累積FCF' : value
          }}
        />
        <ReferenceLine y={0} stroke="#000" />
        <Bar dataKey="revenue" fill="#3b82f6" name="revenue" />
        <Bar dataKey="cogs" fill="#f87171" name="cogs" stackId="costs" />
        <Bar dataKey="opex" fill="#fb923c" name="opex" stackId="costs" />
        <Bar dataKey="operating_profit" fill="#22c55e" name="operating_profit" />
      </BarChart>
    </ResponsiveContainer>
  )
}

function SegmentChart({ segments }: { segments: SegmentData[] }) {
  var chartData = YEARS.map(function(year, i) {
    var point: Record<string, any> = { name: year }
    segments.forEach(function(seg, si) {
      point['rev_' + si] = seg.revenue[i] || 0
      point['gp_' + si] = seg.gross_profit[i] || 0
    })
    return point
  })

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="name" />
          <YAxis tickFormatter={formatYen} width={70} />
          <Tooltip
            formatter={function(value: number, name: string) {
              var idx = parseInt(name.split('_')[1])
              var seg = segments[idx]
              var prefix = name.startsWith('rev_') ? '売上' : '粗利'
              return [formatYen(value), seg ? seg.name + ' ' + prefix : name]
            }}
          />
          <Legend
            formatter={function(value) {
              var idx = parseInt(value.split('_')[1])
              var seg = segments[idx]
              var prefix = value.startsWith('rev_') ? '売上' : '粗利'
              return seg ? seg.name + ' ' + prefix : value
            }}
          />
          <ReferenceLine y={0} stroke="#000" />
          {segments.map(function(seg, si) {
            return (
              <Bar
                key={'rev_' + si}
                dataKey={'rev_' + si}
                fill={SEGMENT_COLORS[si % SEGMENT_COLORS.length]}
                name={'rev_' + si}
                stackId="revenue"
              />
            )
          })}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function SGAChart({ breakdown }: { breakdown: SGABreakdown }) {
  var categories = ['payroll', 'marketing', 'office', 'system', 'other'] as const

  var chartData = YEARS.map(function(year, i) {
    var point: Record<string, any> = { name: year }
    categories.forEach(function(cat) {
      point[cat] = breakdown[cat][i] || 0
    })
    return point
  })

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" />
        <YAxis tickFormatter={formatYen} width={70} />
        <Tooltip
          formatter={function(value: number, name: string) {
            return [formatYen(value), SGA_LABELS[name] || name]
          }}
        />
        <Legend
          formatter={function(value) { return SGA_LABELS[value] || value }}
        />
        {categories.map(function(cat) {
          return (
            <Bar
              key={cat}
              dataKey={cat}
              fill={SGA_COLORS[cat]}
              name={cat}
              stackId="sga"
            />
          )
        })}
      </BarChart>
    </ResponsiveContainer>
  )
}

function SegmentSummaryTable({ segments, totalRevenue, totalGP }: {
  segments: SegmentData[]
  totalRevenue: number[]
  totalGP: number[]
}) {
  return (
    <div className="mt-4 pt-3 border-t border-gray-100">
      <div className="text-xs font-medium text-gray-500 mb-2">セグメント別 売上・粗利</div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-1.5 px-2 text-gray-500 font-medium">セグメント</th>
              {YEARS.map(function(fy) {
                return <th key={fy} className="text-right py-1.5 px-2 text-gray-500 font-medium">{fy}</th>
              })}
              <th className="text-right py-1.5 px-2 text-gray-500 font-medium">成長率</th>
              <th className="text-right py-1.5 px-2 text-gray-500 font-medium">粗利率</th>
            </tr>
          </thead>
          <tbody>
            {segments.map(function(seg, si) {
              return (
                <tr key={si} className="border-b border-gray-50">
                  <td className="py-1.5 px-2">
                    <div className="flex items-center gap-1.5">
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: SEGMENT_COLORS[si % SEGMENT_COLORS.length] }}
                      />
                      <span className="font-medium text-gray-700">{seg.name}</span>
                    </div>
                  </td>
                  {seg.revenue.map(function(rev, yi) {
                    return (
                      <td key={yi} className="text-right py-1.5 px-2 font-mono text-gray-700">
                        <div>{formatYen(rev)}</div>
                        <div className="text-[10px] text-green-600">{formatYen(seg.gross_profit[yi])}</div>
                      </td>
                    )
                  })}
                  <td className="text-right py-1.5 px-2 font-mono text-blue-600">
                    {(seg.growth_rate * 100).toFixed(0)}%
                  </td>
                  <td className="text-right py-1.5 px-2 font-mono text-green-600">
                    {((1 - seg.cogs_rate) * 100).toFixed(0)}%
                  </td>
                </tr>
              )
            })}
            {/* Total row */}
            <tr className="border-t-2 border-gray-300 font-bold">
              <td className="py-1.5 px-2 text-gray-900">合計</td>
              {totalRevenue.map(function(rev, yi) {
                return (
                  <td key={yi} className="text-right py-1.5 px-2 font-mono text-gray-900">
                    <div>{formatYen(rev)}</div>
                    <div className="text-[10px] text-green-700">{formatYen(totalGP[yi])}</div>
                  </td>
                )
              })}
              <td className="text-right py-1.5 px-2 font-mono text-blue-700">
                {totalRevenue[0] > 0
                  ? ((Math.pow(totalRevenue[4] / totalRevenue[0], 0.25) - 1) * 100).toFixed(0) + '%'
                  : '-'
                }
              </td>
              <td className="text-right py-1.5 px-2 font-mono text-green-700">
                {totalRevenue[4] > 0
                  ? ((totalGP[4] / totalRevenue[4]) * 100).toFixed(0) + '%'
                  : '-'
                }
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
