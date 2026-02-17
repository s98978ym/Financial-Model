'use client'

/**
 * Franchise (フランチャイズ) archetype configuration panel.
 *
 * Initial fee, royalty rate, store count, avg store revenue, support cost.
 */

import { useState } from 'react'
import type { FranchiseConfig } from './types'

interface Props {
  config: FranchiseConfig
  onChange: (config: FranchiseConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function FranchisePanel({ config, onChange }: Props) {
  function updateStores(fi: number, val: number) {
    var newS = config.stores.slice(); newS[fi] = val
    onChange({ ...config, stores: newS })
  }

  // Revenue breakdown per FY
  var fyNewStores = FY_LABELS.map(function(_, fi) {
    return fi === 0 ? config.stores[0] : Math.max(0, (config.stores[fi] || 0) - (config.stores[fi - 1] || 0))
  })

  var fyInitialFeeRev = fyNewStores.map(function(n) { return n * config.initial_fee })

  var fyRoyaltyRev = FY_LABELS.map(function(_, fi) {
    return (config.stores[fi] || 0) * config.avg_store_monthly_revenue * config.royalty_rate * 12
  })

  var fySupportCost = FY_LABELS.map(function(_, fi) {
    return (config.stores[fi] || 0) * config.support_cost_per_store * 12
  })

  var fyTotalRev = FY_LABELS.map(function(_, fi) {
    return fyInitialFeeRev[fi] + fyRoyaltyRev[fi]
  })

  var fyGrossProfit = FY_LABELS.map(function(_, fi) {
    return fyTotalRev[fi] - fySupportCost[fi]
  })

  return (
    <div className="space-y-5">
      {/* FC parameters */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">フランチャイズ条件</h4>
        <div className="bg-lime-50 rounded-lg border border-lime-200 p-3 space-y-2 text-[11px]">
          <div className="flex items-center justify-between">
            <span className="text-sand-500">加盟金</span>
            <span>
              <CellInput value={config.initial_fee} onChange={function(v) { onChange({ ...config, initial_fee: v }) }} integer />
              <span className="text-[10px] text-sand-400">円</span>
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sand-500">ロイヤリティ率</span>
            <span>
              <CellInput value={config.royalty_rate * 100} onChange={function(v) { onChange({ ...config, royalty_rate: v / 100 }) }} />
              <span className="text-[10px] text-sand-400">%</span>
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sand-500">平均店舗月商</span>
            <span>
              <CellInput value={config.avg_store_monthly_revenue} onChange={function(v) { onChange({ ...config, avg_store_monthly_revenue: v }) }} integer />
              <span className="text-[10px] text-sand-400">円</span>
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sand-500">店舗サポートコスト/月</span>
            <span>
              <CellInput value={config.support_cost_per_store} onChange={function(v) { onChange({ ...config, support_cost_per_store: v }) }} integer />
              <span className="text-[10px] text-sand-400">円</span>
            </span>
          </div>
        </div>
      </div>

      {/* Store count + revenue projections */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">店舗展開計画</h4>
        <div className="bg-lime-50 rounded-lg border border-lime-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-lime-300">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">指標</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-lime-700 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-lime-100 hover:bg-white/50">
                <td className="px-3 py-2 font-medium text-sand-600">累計店舗数</td>
                {FY_LABELS.map(function(_, fi) {
                  return (
                    <td key={fi} className="px-3 py-2 text-right">
                      <CellInput value={config.stores[fi] || 0} onChange={function(v) { updateStores(fi, v) }} integer />
                    </td>
                  )
                })}
              </tr>
              <tr className="border-b border-lime-100 hover:bg-white/50">
                <td className="px-3 py-2 text-sand-500">新規出店数</td>
                {fyNewStores.map(function(n, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-sand-600">{n}</td>
                })}
              </tr>
              <tr className="border-b border-lime-100 bg-lime-100/30">
                <td className="px-3 py-2 text-sand-500">加盟金収入</td>
                {fyInitialFeeRev.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-sand-600">{formatYen(rev)}円</td>
                })}
              </tr>
              <tr className="border-b border-lime-100 bg-lime-100/30">
                <td className="px-3 py-2 text-sand-500">ロイヤリティ収入</td>
                {fyRoyaltyRev.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-sand-600">{formatYen(rev)}円</td>
                })}
              </tr>
              <tr className="border-b border-lime-200 bg-lime-100/30">
                <td className="px-3 py-2 text-sand-500">サポートコスト</td>
                {fySupportCost.map(function(cost, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-red-500">-{formatYen(cost)}円</td>
                })}
              </tr>
              <tr className="border-t-2 border-lime-300 bg-lime-100/50">
                <td className="px-3 py-2 font-semibold text-sand-600">粗利</td>
                {fyGrossProfit.map(function(gp, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-lime-700">{formatYen(gp)}円</td>
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
      autoFocus className="w-16 text-right bg-white border border-lime-400 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-lime-500" />
  )
  return (
    <button onClick={startEdit} className="font-mono text-[11px] text-dark-900 px-1 py-0.5 rounded border border-transparent hover:border-lime-400 hover:bg-lime-50 cursor-pointer transition-colors">
      {(integer ? Math.round(value) : value).toLocaleString()}
    </button>
  )
}
