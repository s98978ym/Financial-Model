'use client'

import { useState } from 'react'
import type { IndustryKey, PerspectiveKey, TrendItem } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS, INDUSTRY_KEYS, PERSPECTIVE_META, PERSPECTIVE_KEYS } from '@/data/industryBenchmarks'

interface IndustryBenchmarkCardsProps {
  industry: IndustryKey
  onIndustryChange: (industry: IndustryKey) => void
}

var TAB_ITEMS = [
  { key: 'kpi', label: 'KPI指標' },
  { key: 'competition', label: '競争環境' },
  { key: 'competitors', label: '競合企業' },
]

// Color class maps for perspective chips and badges
var PERSPECTIVE_BG: Record<string, string> = {
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  purple: 'bg-purple-50 border-purple-200 text-purple-700',
  rose: 'bg-rose-50 border-rose-200 text-rose-700',
  green: 'bg-green-50 border-green-200 text-green-700',
  orange: 'bg-orange-50 border-orange-200 text-orange-700',
  red: 'bg-red-50 border-red-200 text-red-700',
}

var PERSPECTIVE_BG_ACTIVE: Record<string, string> = {
  blue: 'bg-blue-600 border-blue-600 text-white',
  purple: 'bg-purple-600 border-purple-600 text-white',
  rose: 'bg-rose-600 border-rose-600 text-white',
  green: 'bg-green-600 border-green-600 text-white',
  orange: 'bg-orange-600 border-orange-600 text-white',
  red: 'bg-red-600 border-red-600 text-white',
}

var PERSPECTIVE_DOT: Record<string, string> = {
  blue: 'bg-blue-500',
  purple: 'bg-purple-500',
  rose: 'bg-rose-500',
  green: 'bg-green-500',
  orange: 'bg-orange-500',
  red: 'bg-red-500',
}

var DETAIL_CARDS = [
  { key: 'marketStructure', label: '市場構造', icon: 'chart', color: 'blue' },
  { key: 'entryBarriers', label: '参入障壁', icon: 'shield', color: 'orange' },
  { key: 'ksf', label: 'KSF（成功要因）', icon: 'star', color: 'emerald' },
  { key: 'risks', label: 'リスク', icon: 'alert', color: 'red' },
]

export function IndustryBenchmarkCards({ industry, onIndustryChange }: IndustryBenchmarkCardsProps) {
  var [activeTab, setActiveTab] = useState('kpi')
  var [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({})
  var [activePerspective, setActivePerspective] = useState<PerspectiveKey | 'all'>('all')
  var [expandedTrend, setExpandedTrend] = useState<number | null>(null)
  var info = INDUSTRY_BENCHMARKS[industry]
  if (!info) return null

  function toggleDetail(key: string) {
    setExpandedDetails(function(prev) {
      var next: Record<string, boolean> = {}
      for (var k in prev) { next[k] = prev[k] }
      next[key] = !prev[key]
      return next
    })
  }

  function togglePerspective(p: PerspectiveKey) {
    if (activePerspective === p) {
      setActivePerspective('all')
    } else {
      setActivePerspective(p)
    }
  }

  // Filter trends by selected perspective
  var filteredTrends: TrendItem[] = []
  for (var i = 0; i < info.trends.length; i++) {
    if (activePerspective === 'all' || info.trends[i].perspective === activePerspective) {
      filteredTrends.push(info.trends[i])
    }
  }

  // Count trends per perspective for badge
  var perspectiveCounts: Record<string, number> = {}
  for (var j = 0; j < info.trends.length; j++) {
    var p = info.trends[j].perspective
    perspectiveCounts[p] = (perspectiveCounts[p] || 0) + 1
  }

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

        {/* Competition Environment Tab — Enhanced */}
        {activeTab === 'competition' && (
          <div className="space-y-5">
            {/* Overview */}
            <div className="bg-gradient-to-r from-slate-50 to-gray-50 rounded-lg p-3 border border-gray-100">
              <p className="text-xs text-gray-700 leading-relaxed">{info.competitiveEnvironment}</p>
            </div>

            {/* Structured Competition Detail Cards */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <h4 className="text-xs font-semibold text-gray-800">競争環境の深堀り</h4>
                <span className="text-[10px] text-gray-400">（クリックで展開）</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {DETAIL_CARDS.map(function(card) {
                  var isOpen = !!expandedDetails[card.key]
                  var content = (info.competitionDetail as any)[card.key] as string
                  var colorMap: Record<string, { bg: string; border: string; icon: string; text: string; hoverBorder: string }> = {
                    blue:    { bg: 'bg-blue-50',    border: 'border-blue-200', icon: 'text-blue-600',    text: 'text-blue-800',    hoverBorder: 'hover:border-blue-300' },
                    orange:  { bg: 'bg-orange-50',  border: 'border-orange-200', icon: 'text-orange-600',  text: 'text-orange-800',  hoverBorder: 'hover:border-orange-300' },
                    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: 'text-emerald-600', text: 'text-emerald-800', hoverBorder: 'hover:border-emerald-300' },
                    red:     { bg: 'bg-red-50',     border: 'border-red-200', icon: 'text-red-600',     text: 'text-red-800',     hoverBorder: 'hover:border-red-300' },
                  }
                  var c = colorMap[card.color] || colorMap.blue
                  return (
                    <button
                      key={card.key}
                      onClick={function() { toggleDetail(card.key) }}
                      className={'text-left rounded-lg border transition-all ' + c.border + ' ' + c.hoverBorder + ' ' + (
                        isOpen ? c.bg + ' shadow-sm' : 'bg-white'
                      )}
                    >
                      <div className="flex items-center gap-2 px-3 py-2">
                        <div className={'w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ' + (isOpen ? c.bg : 'bg-gray-100')}>
                          {card.icon === 'chart' && (
                            <svg className={'w-3 h-3 ' + (isOpen ? c.icon : 'text-gray-500')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          )}
                          {card.icon === 'shield' && (
                            <svg className={'w-3 h-3 ' + (isOpen ? c.icon : 'text-gray-500')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                          )}
                          {card.icon === 'star' && (
                            <svg className={'w-3 h-3 ' + (isOpen ? c.icon : 'text-gray-500')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                            </svg>
                          )}
                          {card.icon === 'alert' && (
                            <svg className={'w-3 h-3 ' + (isOpen ? c.icon : 'text-gray-500')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                          )}
                        </div>
                        <span className={'text-xs font-semibold flex-1 ' + (isOpen ? c.text : 'text-gray-700')}>{card.label}</span>
                        <svg
                          className={'w-3.5 h-3.5 transition-transform ' + (isOpen ? 'rotate-180 ' + c.icon : 'text-gray-400')}
                          fill="none" viewBox="0 0 24 24" stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                      {isOpen && (
                        <div className={'px-3 pb-3 pt-0'}>
                          <p className="text-xs text-gray-700 leading-relaxed">{content}</p>
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Trends with Perspective Filter */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-gray-800">業界トレンド</h4>
                <span className="text-[10px] text-gray-400">{filteredTrends.length}/{info.trends.length} 件</span>
              </div>

              {/* Perspective chip filters */}
              <div className="flex flex-wrap gap-1.5 mb-3">
                <button
                  onClick={function() { setActivePerspective('all') }}
                  className={'text-[10px] font-medium px-2.5 py-1 rounded-full border transition-colors ' + (
                    activePerspective === 'all'
                      ? 'bg-gray-800 border-gray-800 text-white'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  )}
                >
                  すべて
                </button>
                {PERSPECTIVE_KEYS.map(function(pk) {
                  var meta = PERSPECTIVE_META[pk]
                  var count = perspectiveCounts[pk] || 0
                  if (count === 0) return null
                  var isActive = activePerspective === pk
                  return (
                    <button
                      key={pk}
                      onClick={function() { togglePerspective(pk) }}
                      className={'text-[10px] font-medium px-2.5 py-1 rounded-full border transition-colors ' + (
                        isActive
                          ? PERSPECTIVE_BG_ACTIVE[meta.color]
                          : PERSPECTIVE_BG[meta.color]
                      )}
                    >
                      {meta.label}
                      <span className="ml-1 opacity-70">{count}</span>
                    </button>
                  )
                })}
              </div>

              {/* Trend Cards */}
              <div className="space-y-2">
                {filteredTrends.map(function(trend, idx) {
                  var meta = PERSPECTIVE_META[trend.perspective]
                  var isExpanded = expandedTrend === idx
                  var dotColor = PERSPECTIVE_DOT[meta.color] || 'bg-gray-500'
                  return (
                    <div
                      key={trend.title}
                      className={'rounded-lg border transition-all ' + (
                        isExpanded
                          ? 'border-gray-300 shadow-sm bg-white'
                          : 'border-gray-100 bg-gray-50 hover:border-gray-200'
                      )}
                    >
                      {/* Trend Header — clickable */}
                      <button
                        onClick={function() { setExpandedTrend(isExpanded ? null : idx) }}
                        className="w-full text-left px-3 py-2.5 flex items-start gap-2.5"
                      >
                        <div className={'w-2 h-2 rounded-full flex-shrink-0 mt-1 ' + dotColor} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-gray-800">{trend.title}</span>
                            <span className={'text-[9px] px-1.5 py-0.5 rounded-full border font-medium ' + PERSPECTIVE_BG[meta.color]}>
                              {meta.label}
                            </span>
                          </div>
                          <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">{trend.summary}</p>
                        </div>
                        <svg
                          className={'w-3.5 h-3.5 flex-shrink-0 mt-0.5 transition-transform text-gray-400 ' + (isExpanded ? 'rotate-180' : '')}
                          fill="none" viewBox="0 0 24 24" stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>

                      {/* P&L Impact — expanded */}
                      {isExpanded && (
                        <div className="px-3 pb-3 pt-0 ml-[18px]">
                          <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5">
                            <div className="flex items-center gap-1.5 mb-1">
                              <svg className="w-3 h-3 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <span className="text-[10px] font-semibold text-amber-700">P&L影響</span>
                            </div>
                            <p className="text-[11px] text-amber-900 leading-relaxed">{trend.plImpact}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}

                {filteredTrends.length === 0 && (
                  <div className="text-center py-4">
                    <p className="text-xs text-gray-400">この視点のトレンドはありません</p>
                  </div>
                )}
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
