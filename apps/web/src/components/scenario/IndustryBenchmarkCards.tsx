'use client'

import { useState } from 'react'
import type { IndustryKey } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS, INDUSTRY_KEYS } from '@/data/industryBenchmarks'

interface IndustryBenchmarkCardsProps {
  industry: IndustryKey
  onIndustryChange: (industry: IndustryKey) => void
}

var TAB_ITEMS = [
  { key: 'kpi', label: 'KPI指標' },
  { key: 'competition', label: '競争環境' },
  { key: 'competitors', label: '競合企業' },
]

export function IndustryBenchmarkCards({ industry, onIndustryChange }: IndustryBenchmarkCardsProps) {
  var [activeTab, setActiveTab] = useState('kpi')
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
      </div>

      {/* Industry description */}
      <div className="px-5 py-2 bg-blue-50 border-b border-blue-100">
        <p className="text-xs text-blue-700">{info.description}</p>
        <p className="text-xs text-blue-500 mt-0.5">ビジネスモデル: {info.businessModel}</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200">
        {TAB_ITEMS.map(function(tab) {
          var isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={function() { setActiveTab(tab.key) }}
              className={'flex-1 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ' + (
                isActive
                  ? 'text-blue-600 border-blue-600 bg-blue-50/50'
                  : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
              )}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {/* KPI Tab */}
        {activeTab === 'kpi' && (
          <div className="grid grid-cols-2 gap-3">
            {info.kpis.map(function(kpi) {
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
        )}

        {/* Competition Environment Tab */}
        {activeTab === 'competition' && (
          <div className="space-y-4">
            {/* Competitive Landscape */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 rounded bg-orange-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-3 h-3 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h4 className="text-xs font-semibold text-gray-800">競争環境</h4>
              </div>
              <div className="bg-orange-50 border border-orange-100 rounded-lg p-3">
                <p className="text-xs text-gray-700 leading-relaxed">{info.competitiveEnvironment}</p>
              </div>
            </div>

            {/* Trends */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 rounded bg-emerald-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-3 h-3 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h4 className="text-xs font-semibold text-gray-800">業界トレンド</h4>
              </div>
              <div className="space-y-2">
                {info.trends.map(function(trend, idx) {
                  var parts = trend.split(' — ')
                  var title = parts[0] || trend
                  var desc = parts[1] || ''
                  return (
                    <div key={idx} className="flex items-start gap-2.5 bg-emerald-50 border border-emerald-100 rounded-lg p-2.5">
                      <span className="text-xs font-bold text-emerald-600 bg-emerald-100 rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <div className="min-w-0">
                        <span className="text-xs font-medium text-gray-800">{title}</span>
                        {desc && (
                          <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* Competitors Tab */}
        {activeTab === 'competitors' && (
          <div className="space-y-3">
            <p className="text-xs text-gray-400 mb-1">主要競合企業の概要（参考情報）</p>
            {info.competitors.map(function(comp, idx) {
              return (
                <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden hover:border-blue-200 transition-colors">
                  {/* Company Header */}
                  <div className="bg-gray-50 px-3 py-2 border-b border-gray-100 flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-sm font-semibold text-gray-900">{comp.name}</span>
                  </div>
                  {/* Company Details */}
                  <div className="p-3 space-y-1.5">
                    <div className="flex gap-2">
                      <span className="text-[10px] font-medium text-gray-400 w-10 flex-shrink-0 pt-0.5">特徴</span>
                      <span className="text-xs text-gray-700">{comp.features}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-[10px] font-medium text-gray-400 w-10 flex-shrink-0 pt-0.5">強み</span>
                      <span className="text-xs text-gray-700">{comp.strengths}</span>
                    </div>
                    <div className="flex gap-4 mt-2 pt-2 border-t border-gray-100">
                      <div className="flex-1">
                        <span className="text-[10px] text-gray-400 block">売上</span>
                        <span className="text-xs font-semibold text-gray-900">{comp.revenue}</span>
                      </div>
                      <div className="flex-1">
                        <span className="text-[10px] text-gray-400 block">営業利益</span>
                        <span className="text-xs font-semibold text-gray-900">{comp.operatingProfit}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
