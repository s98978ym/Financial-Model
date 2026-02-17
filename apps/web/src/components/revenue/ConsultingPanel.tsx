'use client'

/**
 * Consulting archetype configuration panel.
 *
 * Screenshot reference: SKU定義 + 数量(件数)テーブル
 * - SKU: 項目名, 単価, 原価(時給×標準時間), 粗利率, CAC
 * - 数量: FY1-FY5 件数 per service
 */

import { useState } from 'react'
import type { ConsultingConfig, ConsultingSKU } from './types'
import { computeConsultingDeliveryCost, computeConsultingGrossMargin } from './types'

interface Props {
  config: ConsultingConfig
  onChange: (config: ConsultingConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function ConsultingPanel({ config, onChange }: Props) {

  function updateSKU(id: string, patch: Partial<ConsultingSKU>) {
    onChange({
      ...config,
      skus: config.skus.map(function(s) { return s.id === id ? { ...s, ...patch } : s }),
    })
  }

  function addSKU() {
    var newSKU: ConsultingSKU = {
      id: 'sku_' + Date.now().toString(36),
      name: 'サービス' + String.fromCharCode(65 + config.skus.length),
      unit_price: 3000000,
      hourly_rate: 12000,
      standard_hours: 160,
      cac: 150000,
      quantities: [5, 8, 12, 18, 25],
    }
    onChange({ ...config, skus: [...config.skus, newSKU] })
  }

  function removeSKU(id: string) {
    onChange({ ...config, skus: config.skus.filter(function(s) { return s.id !== id }) })
  }

  function updateQuantity(id: string, fyIdx: number, val: number) {
    onChange({
      ...config,
      skus: config.skus.map(function(s) {
        if (s.id !== id) return s
        var newQ = s.quantities.slice()
        newQ[fyIdx] = val
        return { ...s, quantities: newQ }
      }),
    })
  }

  // Compute totals per FY
  var fyTotals = FY_LABELS.map(function(_, fi) {
    return config.skus.reduce(function(sum, sku) {
      return sum + (sku.quantities[fi] || 0) * sku.unit_price
    }, 0)
  })

  return (
    <div className="space-y-5">
      {/* ═══ SKU DEFINITION ═══ */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">SKU定義</h4>
          <button onClick={addSKU} className="text-[10px] text-gold-600 hover:text-gold-500">+ サービス追加</button>
        </div>
        <div className="bg-cream-50 rounded-2xl border border-cream-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cream-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">項目名</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">単価</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium whitespace-nowrap">原価(時給x時間)</th>
                <th className="text-right px-3 py-2 text-emerald-600 font-semibold">粗利率</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">CAC</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.skus.map(function(sku) {
                var cost = computeConsultingDeliveryCost(sku)
                var margin = computeConsultingGrossMargin(sku)
                return (
                  <tr key={sku.id} className="border-b border-cream-200 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={sku.name}
                        onChange={function(e) { updateSKU(sku.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-dark-900 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={sku.unit_price} onChange={function(v) { updateSKU(sku.id, { unit_price: v }) }} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-sand-400 text-[10px]">
                        <CellInput value={sku.hourly_rate} onChange={function(v) { updateSKU(sku.id, { hourly_rate: v }) }} />
                        <span className="mx-0.5">x</span>
                        <CellInput value={sku.standard_hours} onChange={function(v) { updateSKU(sku.id, { standard_hours: v }) }} />
                        <span className="ml-1 text-sand-500">= {formatYen(cost)}円</span>
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className={'font-mono font-semibold '
                        + (margin >= 0.5 ? 'text-green-600' : margin >= 0.3 ? 'text-amber-600' : 'text-red-600')}>
                        {(margin * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={sku.cac} onChange={function(v) { updateSKU(sku.id, { cac: v }) }} />
                    </td>
                    <td className="px-1 py-2">
                      {config.skus.length > 1 && (
                        <button onClick={function() { removeSKU(sku.id) }}
                          className="text-sand-300 hover:text-red-500 transition-colors">
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

      {/* ═══ QUANTITY (件数) TABLE ═══ */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">数量 (件数)</h4>
        <div className="bg-emerald-50 rounded-2xl border border-emerald-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-emerald-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">サービス</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-emerald-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.skus.map(function(sku) {
                return (
                  <tr key={sku.id} className="border-b border-emerald-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-sand-600">{sku.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput
                            value={sku.quantities[fi] || 0}
                            onChange={function(v) { updateQuantity(sku.id, fi, v) }}
                            integer
                          />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              {/* Total row */}
              <tr className="border-t-2 border-emerald-200 bg-emerald-100/50">
                <td className="px-3 py-2 font-semibold text-sand-600">売上合計</td>
                {fyTotals.map(function(total, fi) {
                  return (
                    <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-emerald-700">
                      {formatYen(total)}円
                    </td>
                  )
                })}
              </tr>
            </tbody>
          </table>
        </div>

        {/* Mini bar chart */}
        <div className="mt-2 flex items-end gap-1 h-8">
          {fyTotals.map(function(total, fi) {
            var maxT = Math.max(...fyTotals) || 1
            var h = Math.max((total / maxT) * 100, 5)
            return (
              <div key={fi} className="flex-1 flex flex-col items-center gap-0.5">
                <div className="w-full bg-emerald-400 rounded-t" style={{ height: h + '%' }} />
                <span className="text-[8px] text-sand-400">{FY_LABELS[fi]}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Inline cell input
// ---------------------------------------------------------------------------
function CellInput({ value, onChange, integer }: {
  value: number; onChange: (v: number) => void; integer?: boolean
}) {
  var [editing, setEditing] = useState(false)
  var [draft, setDraft] = useState('')

  function startEdit() {
    setDraft(String(value))
    setEditing(true)
  }

  function commit() {
    var n = integer ? parseInt(draft.replace(/[,\s]/g, '')) : parseFloat(draft.replace(/[,\s]/g, ''))
    if (!isNaN(n) && n >= 0) onChange(n)
    setEditing(false)
  }

  if (editing) {
    return (
      <input type="text" value={draft}
        onChange={function(e) { setDraft(e.target.value) }}
        onBlur={commit}
        onKeyDown={function(e) { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') setEditing(false) }}
        autoFocus
        className="w-16 text-right bg-white border border-gold-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-gold-400"
      />
    )
  }

  return (
    <button onClick={startEdit}
      className="font-mono text-[11px] text-dark-900 px-1 py-0.5 rounded border border-transparent hover:border-gold-300 hover:bg-cream-100 cursor-pointer transition-colors">
      {value.toLocaleString()}
    </button>
  )
}
