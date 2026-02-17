'use client'

/**
 * Advertising (広告) archetype configuration panel.
 *
 * MAU, pageviews, ad formats with CPM/CPC/CPA pricing.
 */

import { useState } from 'react'
import type { AdvertisingConfig, AdFormat } from './types'

interface Props {
  config: AdvertisingConfig
  onChange: (config: AdvertisingConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']
var PRICING_LABELS: Record<string, string> = { cpm: 'CPM', cpc: 'CPC', cpa: 'CPA' }

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

function formatNum(v: number): string {
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(0) + 'K'
  return v.toLocaleString()
}

export function AdvertisingPanel({ config, onChange }: Props) {
  function updateMAU(fi: number, val: number) {
    var newMAU = config.monthly_active_users.slice(); newMAU[fi] = val
    onChange({ ...config, monthly_active_users: newMAU })
  }

  function updateFormat(id: string, patch: Partial<AdFormat>) {
    onChange({ ...config, formats: config.formats.map(function(f) { return f.id === id ? { ...f, ...patch } : f }) })
  }

  function addFormat() {
    var f: AdFormat = {
      id: 'ad_' + Date.now().toString(36),
      name: '広告枠' + String.fromCharCode(65 + config.formats.length),
      pricing_model: 'cpm',
      rate: 500,
      fill_rate: 0.50,
    }
    onChange({ ...config, formats: [...config.formats, f] })
  }

  function removeFormat(id: string) {
    onChange({ ...config, formats: config.formats.filter(function(f) { return f.id !== id }) })
  }

  // Monthly impressions per FY = MAU × avg_pageviews
  var fyImpressions = FY_LABELS.map(function(_, fi) {
    return (config.monthly_active_users[fi] || 0) * config.avg_pageviews_per_user
  })

  // Revenue per format per FY
  function formatRevenue(format: AdFormat, fi: number): number {
    var totalImps = fyImpressions[fi] * format.fill_rate
    if (format.pricing_model === 'cpm') return totalImps * format.rate / 1000
    if (format.pricing_model === 'cpc') return totalImps * 0.02 * format.rate // 2% CTR assumed
    if (format.pricing_model === 'cpa') return totalImps * 0.005 * format.rate // 0.5% CVR assumed
    return 0
  }

  // Total annual revenue per FY
  var fyRevenue = FY_LABELS.map(function(_, fi) {
    return config.formats.reduce(function(sum, f) {
      return sum + formatRevenue(f, fi) * 12
    }, 0)
  })

  return (
    <div className="space-y-5">
      {/* MAU + pageviews */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">トラフィック</h4>
        <div className="bg-rose-50 rounded-2xl border border-rose-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-rose-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">指標</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-rose-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-rose-100 hover:bg-white/50">
                <td className="px-3 py-2 font-medium text-sand-600">MAU</td>
                {FY_LABELS.map(function(_, fi) {
                  return (
                    <td key={fi} className="px-3 py-2 text-right">
                      <CellInput value={config.monthly_active_users[fi] || 0} onChange={function(v) { updateMAU(fi, v) }} integer />
                    </td>
                  )
                })}
              </tr>
              <tr className="border-b border-rose-100 hover:bg-white/50">
                <td className="px-3 py-2 text-sand-500">月間PV</td>
                {fyImpressions.map(function(imp, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono text-sand-600">{formatNum(imp)}</td>
                })}
              </tr>
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-3 text-[11px] px-1 mt-2">
          <span className="text-sand-500">平均PV/ユーザー:</span>
          <CellInput value={config.avg_pageviews_per_user}
            onChange={function(v) { onChange({ ...config, avg_pageviews_per_user: v }) }} />
        </div>
      </div>

      {/* Ad format definitions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">広告フォーマット</h4>
          <button onClick={addFormat} className="text-[10px] text-rose-600 hover:text-rose-800">+ フォーマット追加</button>
        </div>
        <div className="bg-cream-50 rounded-2xl border border-cream-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cream-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">フォーマット</th>
                <th className="text-left px-3 py-2 text-sand-500 font-medium">課金方式</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">単価</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">充填率</th>
                <th className="text-right px-3 py-2 text-rose-600 font-semibold">月次売上(FY5)</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.formats.map(function(f) {
                return (
                  <tr key={f.id} className="border-b border-cream-200 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={f.name}
                        onChange={function(e) { updateFormat(f.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-dark-900 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2">
                      <select value={f.pricing_model}
                        onChange={function(e) { updateFormat(f.id, { pricing_model: e.target.value as any }) }}
                        className="bg-transparent text-sand-600 outline-none text-[11px]">
                        <option value="cpm">CPM</option>
                        <option value="cpc">CPC</option>
                        <option value="cpa">CPA</option>
                      </select>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={f.rate} onChange={function(v) { updateFormat(f.id, { rate: v }) }} />
                      <span className="text-[10px] text-sand-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={f.fill_rate * 100} onChange={function(v) { updateFormat(f.id, { fill_rate: v / 100 }) }} />
                      <span className="text-[10px] text-sand-400">%</span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-rose-700">
                      {formatYen(formatRevenue(f, 4))}円
                    </td>
                    <td className="px-1 py-2">
                      {config.formats.length > 1 && (
                        <button onClick={function() { removeFormat(f.id) }} className="text-sand-300 hover:text-red-500 transition-colors">
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

      {/* Annual revenue summary */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">年間広告売上</h4>
        <div className="bg-rose-50 rounded-2xl border border-rose-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-rose-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">フォーマット</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-rose-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.formats.map(function(f) {
                return (
                  <tr key={f.id} className="border-b border-rose-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-sand-600">{f.name} ({PRICING_LABELS[f.pricing_model]})</td>
                    {FY_LABELS.map(function(_, fi) {
                      return <td key={fi} className="px-3 py-2 text-right font-mono text-sand-600">{formatYen(formatRevenue(f, fi) * 12)}円</td>
                    })}
                  </tr>
                )
              })}
              <tr className="border-t-2 border-rose-200 bg-rose-100/50">
                <td className="px-3 py-2 font-semibold text-sand-600">合計</td>
                {fyRevenue.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-rose-700">{formatYen(rev)}円</td>
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
