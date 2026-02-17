'use client'

/**
 * Marketplace archetype configuration panel.
 *
 * Supply/demand side users, transaction volumes, take rate.
 */

import { useState } from 'react'
import type { MarketplaceConfig, MarketplaceSide } from './types'

interface Props {
  config: MarketplaceConfig
  onChange: (config: MarketplaceConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function MarketplacePanel({ config, onChange }: Props) {
  function updateSide(side: 'supply' | 'demand', patch: Partial<MarketplaceSide>) {
    onChange({ ...config, [side]: { ...config[side], ...patch } })
  }

  function updateUsers(side: 'supply' | 'demand', fi: number, val: number) {
    var s = config[side]
    var newU = s.users.slice(); newU[fi] = val
    onChange({ ...config, [side]: { ...s, users: newU } })
  }

  // GMV and revenue per FY (use demand side transactions as the constraint)
  var fyGMV = FY_LABELS.map(function(_, fi) {
    var demandUsers = config.demand.users[fi] || 0
    return demandUsers * config.demand.txns_per_user * config.demand.avg_txn_value
  })
  var fyRevenue = fyGMV.map(function(gmv) { return gmv * config.take_rate })

  return (
    <div className="space-y-5">
      {/* Supply & Demand side config */}
      <div className="grid grid-cols-2 gap-4">
        {(['supply', 'demand'] as const).map(function(side) {
          var s = config[side]
          var label = side === 'supply' ? '供給側 (出品者)' : '需要側 (購入者)'
          var color = side === 'supply' ? 'cyan' : 'blue'
          return (
            <div key={side} className={'bg-' + color + '-50 rounded-lg border border-' + color + '-100 p-3'}>
              <h4 className={'text-xs font-semibold text-' + color + '-700 mb-3'}>{label}</h4>
              <div className="space-y-2 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-sand-500">名称</span>
                  <input type="text" value={s.name}
                    onChange={function(e) { updateSide(side, { name: e.target.value }) }}
                    className="w-24 text-right bg-transparent font-medium text-dark-900 outline-none focus:bg-white focus:rounded px-1" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sand-500">平均取引額</span>
                  <span>
                    <CellInput value={s.avg_txn_value} onChange={function(v) { updateSide(side, { avg_txn_value: v }) }} />
                    <span className="text-[10px] text-sand-400">円</span>
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sand-500">取引回数/人</span>
                  <CellInput value={s.txns_per_user} onChange={function(v) { updateSide(side, { txns_per_user: v }) }} />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Take rate */}
      <div className="flex items-center gap-3 text-[11px] px-1">
        <span className="text-sand-500 font-medium">手数料率 (テイクレート):</span>
        <CellInput value={config.take_rate * 100}
          onChange={function(v) { onChange({ ...config, take_rate: v / 100 }) }} />
        <span className="text-sand-400">%</span>
      </div>

      {/* User count projections */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">ユーザー数推移</h4>
        <div className="bg-cyan-50 rounded-lg border border-cyan-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cyan-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">サイド</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-cyan-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {(['supply', 'demand'] as const).map(function(side) {
                var s = config[side]
                return (
                  <tr key={side} className="border-b border-cyan-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-sand-600">{s.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput value={s.users[fi] || 0} onChange={function(v) { updateUsers(side, fi, v) }} integer />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              <tr className="border-t border-cyan-200 bg-cyan-100/30">
                <td className="px-3 py-2 text-sand-500">GMV</td>
                {fyGMV.map(function(gmv, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-sand-600">{formatYen(gmv)}円</td>
                })}
              </tr>
              <tr className="border-t-2 border-cyan-200 bg-cyan-100/50">
                <td className="px-3 py-2 font-semibold text-sand-600">売上 ({(config.take_rate * 100).toFixed(0)}%)</td>
                {fyRevenue.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-cyan-700">{formatYen(rev)}円</td>
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
      autoFocus className="w-16 text-right bg-white border border-gold-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-gold-400" />
  )
  return (
    <button onClick={startEdit} className="font-mono text-[11px] text-dark-900 px-1 py-0.5 rounded border border-transparent hover:border-gold-300 hover:bg-cream-100 cursor-pointer transition-colors">
      {(integer ? Math.round(value) : value).toLocaleString()}
    </button>
  )
}
