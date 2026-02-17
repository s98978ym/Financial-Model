'use client'

/**
 * Subscription archetype configuration panel.
 *
 * Plans with monthly price, subscriber counts (FY1-FY5), churn rate.
 * Computed: MRR, ARR per plan per FY.
 */

import { useState } from 'react'
import type { SubscriptionConfig, SubscriptionPlan } from './types'

interface Props {
  config: SubscriptionConfig
  onChange: (config: SubscriptionConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function SubscriptionPanel({ config, onChange }: Props) {
  function updatePlan(id: string, patch: Partial<SubscriptionPlan>) {
    onChange({ ...config, plans: config.plans.map(function(p) { return p.id === id ? { ...p, ...patch } : p }) })
  }

  function updateSubscribers(id: string, fi: number, val: number) {
    onChange({
      ...config,
      plans: config.plans.map(function(p) {
        if (p.id !== id) return p
        var newS = p.subscribers.slice(); newS[fi] = val
        return { ...p, subscribers: newS }
      }),
    })
  }

  function addPlan() {
    var p: SubscriptionPlan = {
      id: 'plan_' + Date.now().toString(36),
      name: 'プラン' + String.fromCharCode(65 + config.plans.length),
      monthly_price: 1980,
      subscribers: [100, 250, 500, 900, 1500],
      churn_rate: 0.04,
    }
    onChange({ ...config, plans: [...config.plans, p] })
  }

  function removePlan(id: string) {
    onChange({ ...config, plans: config.plans.filter(function(p) { return p.id !== id }) })
  }

  // ARR per FY
  var fyARR = FY_LABELS.map(function(_, fi) {
    return config.plans.reduce(function(sum, p) { return sum + (p.subscribers[fi] || 0) * p.monthly_price * 12 }, 0)
  })

  return (
    <div className="space-y-5">
      {/* Plan definitions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">プラン定義</h4>
          <button onClick={addPlan} className="text-[10px] text-gold-600 hover:text-gold-500">+ プラン追加</button>
        </div>
        <div className="bg-cream-50 rounded-2xl border border-cream-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cream-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">プラン名</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">月額</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">月次解約率</th>
                <th className="text-right px-3 py-2 text-orange-600 font-semibold">年間ARPU</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.plans.map(function(plan) {
                return (
                  <tr key={plan.id} className="border-b border-cream-200 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={plan.name}
                        onChange={function(e) { updatePlan(plan.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-dark-900 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={plan.monthly_price} onChange={function(v) { updatePlan(plan.id, { monthly_price: v }) }} />
                      <span className="text-[10px] text-sand-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={plan.churn_rate * 100} onChange={function(v) { updatePlan(plan.id, { churn_rate: v / 100 }) }} />
                      <span className="text-[10px] text-sand-400">%</span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-semibold text-orange-700">
                      {formatYen(plan.monthly_price * 12)}円
                    </td>
                    <td className="px-1 py-2">
                      {config.plans.length > 1 && (
                        <button onClick={function() { removePlan(plan.id) }} className="text-sand-300 hover:text-red-500 transition-colors">
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

      {/* Subscriber count per FY */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">契約者数推移</h4>
        <div className="bg-orange-50 rounded-2xl border border-orange-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-orange-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">プラン</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-orange-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.plans.map(function(plan) {
                return (
                  <tr key={plan.id} className="border-b border-orange-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-sand-600">{plan.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput value={plan.subscribers[fi] || 0} onChange={function(v) { updateSubscribers(plan.id, fi, v) }} integer />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              <tr className="border-t-2 border-orange-200 bg-orange-100/50">
                <td className="px-3 py-2 font-semibold text-sand-600">ARR</td>
                {fyARR.map(function(arr, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-orange-700">{formatYen(arr)}円</td>
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Trial conversion */}
      <div className="flex items-center gap-3 text-[11px]">
        <span className="text-sand-500">トライアル→有料転換率:</span>
        <CellInput value={config.trial_conversion_rate * 100}
          onChange={function(v) { onChange({ ...config, trial_conversion_rate: v / 100 }) }} />
        <span className="text-sand-400">%</span>
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
