'use client'

/**
 * Usage (従量課金) archetype configuration panel.
 *
 * Tier-based pricing with unit price, free tier, usage per user.
 */

import { useState } from 'react'
import type { UsageConfig, UsageTier } from './types'

interface Props {
  config: UsageConfig
  onChange: (config: UsageConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function UsagePanel({ config, onChange }: Props) {
  function updateTier(id: string, patch: Partial<UsageTier>) {
    onChange({ ...config, tiers: config.tiers.map(function(t) { return t.id === id ? { ...t, ...patch } : t }) })
  }

  function updateUsers(id: string, fi: number, val: number) {
    onChange({
      ...config,
      tiers: config.tiers.map(function(t) {
        if (t.id !== id) return t
        var newU = t.users.slice(); newU[fi] = val
        return { ...t, users: newU }
      }),
    })
  }

  function addTier() {
    var t: UsageTier = {
      id: 'tier_' + Date.now().toString(36),
      name: 'ティア' + String.fromCharCode(65 + config.tiers.length),
      unit_price: 1,
      unit_label: 'リクエスト',
      included_units: 5000,
      users: [100, 250, 500, 900, 1500],
      avg_usage_per_user: 20000,
    }
    onChange({ ...config, tiers: [...config.tiers, t] })
  }

  function removeTier(id: string) {
    onChange({ ...config, tiers: config.tiers.filter(function(t) { return t.id !== id }) })
  }

  // Revenue per FY: sum across tiers of (users × max(0, avg_usage - included) × unit_price × 12)
  var fyRevenue = FY_LABELS.map(function(_, fi) {
    return config.tiers.reduce(function(sum, t) {
      var users = t.users[fi] || 0
      var billable = Math.max(0, t.avg_usage_per_user - t.included_units)
      return sum + users * billable * t.unit_price * 12
    }, 0)
  })

  return (
    <div className="space-y-5">
      {/* Tier definitions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">料金ティア定義</h4>
          <button onClick={addTier} className="text-[10px] text-teal-600 hover:text-teal-800">+ ティア追加</button>
        </div>
        <div className="bg-cream-50 rounded-2xl border border-cream-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cream-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">ティア名</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">単価</th>
                <th className="text-left px-3 py-2 text-sand-500 font-medium">利用単位</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">無料枠</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">平均利用量/月</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.tiers.map(function(tier) {
                return (
                  <tr key={tier.id} className="border-b border-cream-200 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={tier.name}
                        onChange={function(e) { updateTier(tier.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-dark-900 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={tier.unit_price} onChange={function(v) { updateTier(tier.id, { unit_price: v }) }} />
                      <span className="text-[10px] text-sand-400">円</span>
                    </td>
                    <td className="px-3 py-2">
                      <input type="text" value={tier.unit_label}
                        onChange={function(e) { updateTier(tier.id, { unit_label: e.target.value }) }}
                        className="w-20 bg-transparent text-sand-600 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={tier.included_units} onChange={function(v) { updateTier(tier.id, { included_units: v }) }} integer />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={tier.avg_usage_per_user} onChange={function(v) { updateTier(tier.id, { avg_usage_per_user: v }) }} integer />
                    </td>
                    <td className="px-1 py-2">
                      {config.tiers.length > 1 && (
                        <button onClick={function() { removeTier(tier.id) }} className="text-sand-300 hover:text-red-500 transition-colors">
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

      {/* User count projections per tier */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">ユーザー数推移</h4>
        <div className="bg-teal-50 rounded-lg border border-teal-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-teal-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">ティア</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-teal-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.tiers.map(function(tier) {
                return (
                  <tr key={tier.id} className="border-b border-teal-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-sand-600">{tier.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput value={tier.users[fi] || 0} onChange={function(v) { updateUsers(tier.id, fi, v) }} integer />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              <tr className="border-t-2 border-teal-200 bg-teal-100/50">
                <td className="px-3 py-2 font-semibold text-sand-600">年間売上</td>
                {fyRevenue.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-teal-700">{formatYen(rev)}円</td>
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
