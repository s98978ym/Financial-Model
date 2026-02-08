'use client'

import { useCallback } from 'react'

interface DriverSlidersProps {
  parameters: Record<string, number>
  onChange: (key: string, value: number) => void
}

const DRIVERS = [
  {
    key: 'revenue_fy1',
    label: '初年度売上',
    unit: '円',
    min: 10_000_000,
    max: 1_000_000_000,
    step: 10_000_000,
    format: (v: number) => `${(v / 100_000_000).toFixed(1)}億円`,
  },
  {
    key: 'growth_rate',
    label: '売上成長率',
    unit: '%',
    min: 0,
    max: 1.0,
    step: 0.05,
    format: (v: number) => `${(v * 100).toFixed(0)}%`,
  },
  {
    key: 'cogs_rate',
    label: '売上原価率',
    unit: '%',
    min: 0,
    max: 0.8,
    step: 0.05,
    format: (v: number) => `${(v * 100).toFixed(0)}%`,
  },
  {
    key: 'opex_base',
    label: '初年度 OPEX',
    unit: '円',
    min: 10_000_000,
    max: 500_000_000,
    step: 5_000_000,
    format: (v: number) => `${(v / 100_000_000).toFixed(1)}億円`,
  },
  {
    key: 'opex_growth',
    label: 'OPEX 増加率',
    unit: '%',
    min: 0,
    max: 0.5,
    step: 0.05,
    format: (v: number) => `${(v * 100).toFixed(0)}%`,
  },
]

export function DriverSliders({ parameters, onChange }: DriverSlidersProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-5">
      <h3 className="font-medium text-gray-900">ドライバー調整</h3>
      <p className="text-xs text-gray-500">
        スライダーを動かすとPLがリアルタイムで変化します
      </p>

      {DRIVERS.map((driver) => {
        const value = parameters[driver.key] ?? driver.min
        return (
          <div key={driver.key}>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm text-gray-700">{driver.label}</label>
              <span className="text-sm font-mono font-medium text-gray-900">
                {driver.format(value)}
              </span>
            </div>
            <input
              type="range"
              min={driver.min}
              max={driver.max}
              step={driver.step}
              value={value}
              onChange={(e) => onChange(driver.key, parseFloat(e.target.value))}
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
