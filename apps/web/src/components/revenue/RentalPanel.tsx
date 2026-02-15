'use client'

/**
 * Rental / Lease (レンタル/リース) archetype configuration panel.
 *
 * Asset categories with monthly fee, acquisition cost, units per FY, utilization.
 */

import { useState } from 'react'
import type { RentalConfig, RentalAsset } from './types'

interface Props {
  config: RentalConfig
  onChange: (config: RentalConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function RentalPanel({ config, onChange }: Props) {
  function updateAsset(id: string, patch: Partial<RentalAsset>) {
    onChange({ ...config, assets: config.assets.map(function(a) { return a.id === id ? { ...a, ...patch } : a }) })
  }

  function updateUnits(id: string, fi: number, val: number) {
    onChange({
      ...config,
      assets: config.assets.map(function(a) {
        if (a.id !== id) return a
        var newU = a.units.slice(); newU[fi] = val
        return { ...a, units: newU }
      }),
    })
  }

  function addAsset() {
    var a: RentalAsset = {
      id: 'asset_' + Date.now().toString(36),
      name: '資産' + String.fromCharCode(65 + config.assets.length),
      monthly_fee: 40000,
      acquisition_cost: 500000,
      units: [10, 25, 50, 90, 150],
    }
    onChange({ ...config, assets: [...config.assets, a] })
  }

  function removeAsset(id: string) {
    onChange({ ...config, assets: config.assets.filter(function(a) { return a.id !== id }) })
  }

  // Revenue per FY: sum of (units × monthly_fee × utilization × 12)
  var fyRevenue = FY_LABELS.map(function(_, fi) {
    return config.assets.reduce(function(sum, a) {
      return sum + (a.units[fi] || 0) * a.monthly_fee * config.utilization_rate * 12
    }, 0)
  })

  // Payback months per asset
  function paybackMonths(asset: RentalAsset): number {
    var monthlyNet = asset.monthly_fee * config.utilization_rate
    return monthlyNet > 0 ? asset.acquisition_cost / monthlyNet : 0
  }

  return (
    <div className="space-y-5">
      {/* Asset definitions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-700">資産カテゴリ定義</h4>
          <button onClick={addAsset} className="text-[10px] text-stone-600 hover:text-stone-800">+ 資産追加</button>
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">資産名</th>
                <th className="text-right px-3 py-2 text-gray-500 font-medium">月額料金</th>
                <th className="text-right px-3 py-2 text-gray-500 font-medium">取得原価</th>
                <th className="text-right px-3 py-2 text-stone-600 font-semibold">回収期間</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.assets.map(function(asset) {
                var pb = paybackMonths(asset)
                return (
                  <tr key={asset.id} className="border-b border-gray-100 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={asset.name}
                        onChange={function(e) { updateAsset(asset.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-gray-900 outline-none focus:bg-stone-50 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={asset.monthly_fee} onChange={function(v) { updateAsset(asset.id, { monthly_fee: v }) }} integer />
                      <span className="text-[10px] text-gray-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={asset.acquisition_cost} onChange={function(v) { updateAsset(asset.id, { acquisition_cost: v }) }} integer />
                      <span className="text-[10px] text-gray-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-stone-700">
                      {pb > 0 ? pb.toFixed(1) + 'ヶ月' : '—'}
                    </td>
                    <td className="px-1 py-2">
                      {config.assets.length > 1 && (
                        <button onClick={function() { removeAsset(asset.id) }} className="text-gray-300 hover:text-red-500 transition-colors">
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

      {/* Utilization + contract months */}
      <div className="flex items-center gap-6 text-[11px] px-1">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 font-medium">稼働率:</span>
          <CellInput value={config.utilization_rate * 100}
            onChange={function(v) { onChange({ ...config, utilization_rate: v / 100 }) }} />
          <span className="text-gray-400">%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-500 font-medium">平均契約期間:</span>
          <CellInput value={config.avg_contract_months}
            onChange={function(v) { onChange({ ...config, avg_contract_months: v }) }} integer />
          <span className="text-gray-400">ヶ月</span>
        </div>
      </div>

      {/* Unit count projections */}
      <div>
        <h4 className="text-xs font-semibold text-gray-700 mb-2">保有台数推移</h4>
        <div className="bg-stone-50 rounded-lg border border-stone-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-stone-300">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">資産</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-stone-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.assets.map(function(asset) {
                return (
                  <tr key={asset.id} className="border-b border-stone-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-gray-700">{asset.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput value={asset.units[fi] || 0} onChange={function(v) { updateUnits(asset.id, fi, v) }} integer />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              <tr className="border-t-2 border-stone-300 bg-stone-100/50">
                <td className="px-3 py-2 font-semibold text-gray-700">年間売上</td>
                {fyRevenue.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-stone-700">{formatYen(rev)}円</td>
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
      autoFocus className="w-16 text-right bg-white border border-stone-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-stone-400" />
  )
  return (
    <button onClick={startEdit} className="font-mono text-[11px] text-gray-900 px-1 py-0.5 rounded border border-transparent hover:border-stone-300 hover:bg-stone-50 cursor-pointer transition-colors">
      {(integer ? Math.round(value) : value).toLocaleString()}
    </button>
  )
}
