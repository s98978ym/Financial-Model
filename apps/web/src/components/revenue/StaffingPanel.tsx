'use client'

/**
 * Staffing / SES (人材派遣) archetype configuration panel.
 *
 * Staff categories with monthly billing rate, cost rate, headcount per FY, utilization.
 */

import { useState } from 'react'
import type { StaffingConfig, StaffCategory } from './types'

interface Props {
  config: StaffingConfig
  onChange: (config: StaffingConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function StaffingPanel({ config, onChange }: Props) {
  function updateCategory(id: string, patch: Partial<StaffCategory>) {
    onChange({ ...config, categories: config.categories.map(function(c) { return c.id === id ? { ...c, ...patch } : c }) })
  }

  function updateHeadcount(id: string, fi: number, val: number) {
    onChange({
      ...config,
      categories: config.categories.map(function(c) {
        if (c.id !== id) return c
        var newH = c.headcount.slice(); newH[fi] = val
        return { ...c, headcount: newH }
      }),
    })
  }

  function addCategory() {
    var c: StaffCategory = {
      id: 'staff_' + Date.now().toString(36),
      name: '職種' + String.fromCharCode(65 + config.categories.length),
      monthly_rate: 600000,
      cost_rate: 420000,
      headcount: [5, 12, 25, 40, 60],
    }
    onChange({ ...config, categories: [...config.categories, c] })
  }

  function removeCategory(id: string) {
    onChange({ ...config, categories: config.categories.filter(function(c) { return c.id !== id }) })
  }

  // Revenue per FY: sum of (headcount × monthly_rate × utilization × 12)
  var fyRevenue = FY_LABELS.map(function(_, fi) {
    return config.categories.reduce(function(sum, c) {
      return sum + (c.headcount[fi] || 0) * c.monthly_rate * config.utilization_rate * 12
    }, 0)
  })

  // Cost per FY
  var fyCost = FY_LABELS.map(function(_, fi) {
    return config.categories.reduce(function(sum, c) {
      return sum + (c.headcount[fi] || 0) * c.cost_rate * 12
    }, 0)
  })

  // Gross margin per FY
  var fyMargin = fyRevenue.map(function(rev, fi) {
    return rev > 0 ? (rev - fyCost[fi]) / rev : 0
  })

  return (
    <div className="space-y-5">
      {/* Category definitions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-700">職種カテゴリ定義</h4>
          <button onClick={addCategory} className="text-[10px] text-amber-600 hover:text-amber-800">+ カテゴリ追加</button>
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">職種名</th>
                <th className="text-right px-3 py-2 text-gray-500 font-medium">月額単価(請求)</th>
                <th className="text-right px-3 py-2 text-gray-500 font-medium">月額原価</th>
                <th className="text-right px-3 py-2 text-amber-600 font-semibold">粗利率</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.categories.map(function(cat) {
                var margin = cat.monthly_rate > 0 ? (cat.monthly_rate - cat.cost_rate) / cat.monthly_rate : 0
                return (
                  <tr key={cat.id} className="border-b border-gray-100 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={cat.name}
                        onChange={function(e) { updateCategory(cat.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-gray-900 outline-none focus:bg-amber-50 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={cat.monthly_rate} onChange={function(v) { updateCategory(cat.id, { monthly_rate: v }) }} integer />
                      <span className="text-[10px] text-gray-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={cat.cost_rate} onChange={function(v) { updateCategory(cat.id, { cost_rate: v }) }} integer />
                      <span className="text-[10px] text-gray-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-semibold text-amber-700">
                      {(margin * 100).toFixed(1)}%
                    </td>
                    <td className="px-1 py-2">
                      {config.categories.length > 1 && (
                        <button onClick={function() { removeCategory(cat.id) }} className="text-gray-300 hover:text-red-500 transition-colors">
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Utilization rate */}
      <div className="flex items-center gap-3 text-[11px] px-1">
        <span className="text-gray-500 font-medium">稼働率:</span>
        <CellInput value={config.utilization_rate * 100}
          onChange={function(v) { onChange({ ...config, utilization_rate: v / 100 }) }} />
        <span className="text-gray-400">%</span>
      </div>

      {/* Headcount projections */}
      <div>
        <h4 className="text-xs font-semibold text-gray-700 mb-2">稼働人数推移</h4>
        <div className="bg-amber-50 rounded-lg border border-amber-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-amber-200">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">職種</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-amber-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.categories.map(function(cat) {
                return (
                  <tr key={cat.id} className="border-b border-amber-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-gray-700">{cat.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput value={cat.headcount[fi] || 0} onChange={function(v) { updateHeadcount(cat.id, fi, v) }} integer />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              <tr className="border-t border-amber-200 bg-amber-100/30">
                <td className="px-3 py-2 text-gray-500">売上</td>
                {fyRevenue.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-gray-600">{formatYen(rev)}円</td>
                })}
              </tr>
              <tr className="border-t border-amber-200 bg-amber-100/30">
                <td className="px-3 py-2 text-gray-500">原価</td>
                {fyCost.map(function(cost, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-gray-500">{formatYen(cost)}円</td>
                })}
              </tr>
              <tr className="border-t-2 border-amber-200 bg-amber-100/50">
                <td className="px-3 py-2 font-semibold text-gray-700">粗利</td>
                {fyRevenue.map(function(rev, fi) {
                  return (
                    <td key={fi} className="px-3 py-2 text-right">
                      <span className="font-mono font-bold text-amber-700">{formatYen(rev - fyCost[fi])}円</span>
                      <span className="text-[10px] text-gray-400 ml-1">({(fyMargin[fi] * 100).toFixed(0)}%)</span>
                    </td>
                  )
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function CellInput({ value, onChange, integer }: { value: number; onChange: (v: number) => void; integer?: boolean }) {
  var [editing, setEditing] = useState(false)
  var [draft, setDraft] = useState('')
  function startEdit() { setDraft(String(integer ? Math.round(value) : value)); setEditing(true) }
  function commit() {
    var n = integer ? parseInt(draft.replace(/[,\s]/g, '')) : parseFloat(draft.replace(/[,\s]/g, ''))
    if (!isNaN(n) && n >= 0) onChange(n)
    setEditing(false)
  }
  if (editing) return (
    <input type="text" value={draft} onChange={function(e) { setDraft(e.target.value) }}
      onBlur={commit} onKeyDown={function(e) { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') setEditing(false) }}
      autoFocus className="w-16 text-right bg-white border border-amber-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-amber-400" />
  )
  return (
    <button onClick={startEdit} className="font-mono text-[11px] text-gray-900 px-1 py-0.5 rounded border border-transparent hover:border-amber-300 hover:bg-amber-50 cursor-pointer transition-colors">
      {(integer ? Math.round(value) : value).toLocaleString()}
    </button>
  )
}
