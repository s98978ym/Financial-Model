'use client'

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

interface PLChartProps {
  data?: {
    revenue: number[]
    cogs: number[]
    gross_profit: number[]
    opex: number[]
    operating_profit: number[]
    fcf: number[]
    cumulative_fcf: number[]
  }
  kpis?: {
    break_even_year?: string | null
    revenue_cagr?: number
    fy5_op_margin?: number
  }
}

const YEARS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

const formatYen = (value: number) => {
  if (Math.abs(value) >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}億`
  if (Math.abs(value) >= 10_000) return `${(value / 10_000).toFixed(0)}万`
  return value.toLocaleString()
}

export function PLChart({ data, kpis }: PLChartProps) {
  if (!data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 flex items-center justify-center h-80">
        <p className="text-gray-400">パラメータを調整するとグラフが表示されます</p>
      </div>
    )
  }

  const chartData = YEARS.map((year, i) => ({
    name: year,
    revenue: data.revenue[i] || 0,
    opex: -(data.opex[i] || 0),
    cogs: -(data.cogs[i] || 0),
    operating_profit: data.operating_profit[i] || 0,
    cumulative_fcf: data.cumulative_fcf[i] || 0,
  }))

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
          {kpis.fy5_op_margin != null && (
            <div>
              <span className="text-gray-500">FY5営業利益率: </span>
              <span className="font-bold">{(kpis.fy5_op_margin * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      )}

      {/* Bar Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} stackOffset="sign">
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="name" />
          <YAxis tickFormatter={formatYen} width={70} />
          <Tooltip
            formatter={(value: number, name: string) => [
              formatYen(Math.abs(value)),
              name === 'revenue' ? '売上' :
              name === 'cogs' ? '原価' :
              name === 'opex' ? 'OPEX' :
              name === 'operating_profit' ? '営業利益' :
              name === 'cumulative_fcf' ? '累積FCF' : name,
            ]}
          />
          <Legend
            formatter={(value) =>
              value === 'revenue' ? '売上' :
              value === 'cogs' ? '原価' :
              value === 'opex' ? 'OPEX' :
              value === 'operating_profit' ? '営業利益' :
              value === 'cumulative_fcf' ? '累積FCF' : value
            }
          />
          <ReferenceLine y={0} stroke="#000" />
          <Bar dataKey="revenue" fill="#3b82f6" name="revenue" />
          <Bar dataKey="cogs" fill="#f87171" name="cogs" stackId="costs" />
          <Bar dataKey="opex" fill="#fb923c" name="opex" stackId="costs" />
          <Bar dataKey="operating_profit" fill="#22c55e" name="operating_profit" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
