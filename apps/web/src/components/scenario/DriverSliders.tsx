'use client'

import { useState } from 'react'
import type { IndustryKey, DriverBenchmark } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS } from '@/data/industryBenchmarks'

interface DriverSlidersProps {
  parameters: Record<string, number>
  onChange: (key: string, value: number) => void
  industry?: IndustryKey
}

const DRIVERS = [
  {
    key: 'revenue_fy1',
    label: '初年度売上',
    unit: '円',
    min: 10_000_000,
    max: 1_000_000_000,
    step: 10_000_000,
    format: function(v: number) { return (v / 100_000_000).toFixed(1) + '億円' },
  },
  {
    key: 'growth_rate',
    label: '売上成長率',
    unit: '%',
    min: 0,
    max: 1.0,
    step: 0.05,
    format: function(v: number) { return (v * 100).toFixed(0) + '%' },
  },
  {
    key: 'cogs_rate',
    label: '売上原価率',
    unit: '%',
    min: 0,
    max: 0.8,
    step: 0.05,
    format: function(v: number) { return (v * 100).toFixed(0) + '%' },
  },
  {
    key: 'opex_base',
    label: '初年度 OPEX',
    unit: '円',
    min: 10_000_000,
    max: 500_000_000,
    step: 5_000_000,
    format: function(v: number) { return (v / 100_000_000).toFixed(1) + '億円' },
  },
  {
    key: 'opex_growth',
    label: 'OPEX 増加率',
    unit: '%',
    min: 0,
    max: 0.5,
    step: 0.05,
    format: function(v: number) { return (v * 100).toFixed(0) + '%' },
  },
]

function BenchmarkTooltip({ benchmark, driverKey }: { benchmark: DriverBenchmark; driverKey: string }) {
  var isRate = driverKey.includes('rate') || driverKey.includes('growth')
  var formatVal = function(v: number) {
    if (isRate) return (v * 100).toFixed(0) + '%'
    if (v >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
    return (v / 10_000).toFixed(0) + '万円'
  }

  return (
    <div className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg pointer-events-none">
      <div className="font-medium mb-1.5 text-blue-300">業界水準</div>
      <div className="space-y-1">
        <div className="flex justify-between">
          <span className="text-gray-400">低位:</span>
          <span>{formatVal(benchmark.low)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">中央:</span>
          <span className="text-blue-300 font-medium">{formatVal(benchmark.mid)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">高位:</span>
          <span>{formatVal(benchmark.high)}</span>
        </div>
      </div>
      <div className="mt-2 pt-1.5 border-t border-gray-700 text-gray-400 leading-tight">
        {benchmark.label}
      </div>
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
    </div>
  )
}

function BenchmarkBar({ benchmark, driver, value }: { benchmark: DriverBenchmark; driver: typeof DRIVERS[0]; value: number }) {
  var range = driver.max - driver.min
  if (range <= 0) return null

  var lowPct = ((benchmark.low - driver.min) / range) * 100
  var highPct = ((benchmark.high - driver.min) / range) * 100
  var midPct = ((benchmark.mid - driver.min) / range) * 100

  // Clamp
  lowPct = Math.max(0, Math.min(100, lowPct))
  highPct = Math.max(0, Math.min(100, highPct))
  midPct = Math.max(0, Math.min(100, midPct))

  return (
    <div className="relative h-1.5 mt-0.5 mb-1">
      {/* Benchmark range bar */}
      <div
        className="absolute h-full bg-blue-200 rounded-full opacity-60"
        style={{ left: lowPct + '%', width: (highPct - lowPct) + '%' }}
      />
      {/* Mid marker */}
      <div
        className="absolute w-1.5 h-1.5 bg-blue-500 rounded-full -translate-x-1/2"
        style={{ left: midPct + '%' }}
      />
    </div>
  )
}

export function DriverSliders({ parameters, onChange, industry }: DriverSlidersProps) {
  var [hoveredDriver, setHoveredDriver] = useState<string | null>(null)
  var benchmarks = industry ? INDUSTRY_BENCHMARKS[industry]?.drivers : null

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-5">
      <h3 className="font-medium text-gray-900">ドライバー調整</h3>
      <p className="text-xs text-gray-500">
        スライダーを動かすとPLがリアルタイムで変化します
        {benchmarks && <span className="text-blue-500 ml-1">(青帯=業界水準)</span>}
      </p>

      {DRIVERS.map(function(driver) {
        var value = parameters[driver.key] != null ? parameters[driver.key] : driver.min
        var benchmark = benchmarks ? benchmarks[driver.key as keyof typeof benchmarks] : null
        var isHovered = hoveredDriver === driver.key

        return (
          <div
            key={driver.key}
            className="relative"
            onMouseEnter={function() { setHoveredDriver(driver.key) }}
            onMouseLeave={function() { setHoveredDriver(null) }}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <label className="text-sm text-gray-700">{driver.label}</label>
                {benchmark && (
                  <span className="relative">
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] cursor-help">
                      i
                    </span>
                    {isHovered && <BenchmarkTooltip benchmark={benchmark} driverKey={driver.key} />}
                  </span>
                )}
              </div>
              <span className="text-sm font-mono font-medium text-gray-900">
                {driver.format(value)}
              </span>
            </div>
            {benchmark && (
              <BenchmarkBar benchmark={benchmark} driver={driver} value={value} />
            )}
            <input
              type="range"
              min={driver.min}
              max={driver.max}
              step={driver.step}
              value={value}
              onChange={function(e) { onChange(driver.key, parseFloat(e.target.value)) }}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>{driver.format(driver.min)}</span>
              <span>{driver.format(driver.max)}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
