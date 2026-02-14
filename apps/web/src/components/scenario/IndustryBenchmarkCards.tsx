'use client'

import { useState } from 'react'
import type { IndustryKey } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS, INDUSTRY_KEYS } from '@/data/industryBenchmarks'

interface IndustryBenchmarkCardsProps {
  industry: IndustryKey
  onIndustryChange: (industry: IndustryKey) => void
}

export function IndustryBenchmarkCards({ industry, onIndustryChange }: IndustryBenchmarkCardsProps) {
  var [isExpanded, setIsExpanded] = useState(false)
  var info = INDUSTRY_BENCHMARKS[industry]
  if (!info) return null

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header with industry selector */}
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-gray-900 text-sm">業界参考情報</h3>
          <span className="text-xs text-gray-400">|</span>
          <select
            value={industry}
            onChange={function(e) { onIndustryChange(e.target.value as IndustryKey) }}
            className="text-sm text-blue-600 font-medium bg-transparent border-none cursor-pointer focus:outline-none focus:ring-0 pr-6 -mr-2"
          >
            {INDUSTRY_KEYS.map(function(key) {
              return (
                <option key={key} value={key}>{INDUSTRY_BENCHMARKS[key].label}</option>
              )
            })}
          </select>
        </div>
        <button
          onClick={function() { setIsExpanded(!isExpanded) }}
          className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          {isExpanded ? '閉じる' : 'KPI詳細'}
          <span className={'inline-block transition-transform ' + (isExpanded ? 'rotate-180' : '')} style={{ fontSize: '10px' }}>
            ▼
          </span>
        </button>
      </div>

      {/* Industry description */}
      <div className="px-5 py-2 bg-blue-50 border-b border-blue-100">
        <p className="text-xs text-blue-700">{info.description}</p>
        <p className="text-xs text-blue-500 mt-0.5">ビジネスモデル: {info.businessModel}</p>
      </div>

      {/* KPI Cards Grid */}
      <div className="p-4">
        <div className="grid grid-cols-2 gap-3">
          {info.kpis.slice(0, isExpanded ? info.kpis.length : 4).map(function(kpi) {
            return (
              <div
                key={kpi.key}
                className="bg-gray-50 rounded-lg p-3 border border-gray-100 hover:border-blue-200 transition-colors group"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-600">{kpi.label}</span>
                </div>
                <div className="text-base font-bold text-gray-900 mb-1">{kpi.value}</div>
                <p className="text-xs text-gray-500 leading-relaxed opacity-80 group-hover:opacity-100">
                  {kpi.description}
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
