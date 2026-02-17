'use client'

/**
 * Unit Economics archetype configuration panel.
 *
 * Screenshot reference: SKU定義テーブル + UNIT ECONOMICS計算テーブル
 * - SKU: 単価, 商品数/取引, 取引回数/人, 年間購入回数, 一人あたり売上
 * - Unit Economics: CAC, LTV, LTV/CAC, 回収期間, 月次解約率
 */

import { useState } from 'react'
import type { UnitEconomicsConfig, UnitEconSKU } from './types'
import {
  computeUnitEconRevPerPerson,
  computeUnitEconLTV,
  computeUnitEconLTVCACRatio,
  computeUnitEconPaybackMonths,
} from './types'

interface Props {
  config: UnitEconomicsConfig
  onChange: (config: UnitEconomicsConfig) => void
}

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function UnitEconomicsPanel({ config, onChange }: Props) {
  var [addOpen, setAddOpen] = useState(false)

  function updateSKU(id: string, patch: Partial<UnitEconSKU>) {
    onChange({
      ...config,
      skus: config.skus.map(function(s) { return s.id === id ? { ...s, ...patch } : s }),
    })
  }

  function addSKU() {
    var newSKU: UnitEconSKU = {
      id: 'sku_' + Date.now().toString(36),
      name: 'プラン' + String.fromCharCode(65 + config.skus.length),
      price: 30000,
      items_per_txn: 1,
      txns_per_person: 1,
      annual_purchases: 12,
    }
    onChange({ ...config, skus: [...config.skus, newSKU] })
    setAddOpen(false)
  }

  function removeSKU(id: string) {
    onChange({ ...config, skus: config.skus.filter(function(s) { return s.id !== id }) })
  }

  // Computed
  var ltv = computeUnitEconLTV(config)
  var ltvCac = computeUnitEconLTVCACRatio(config)
  var payback = computeUnitEconPaybackMonths(config)
  var avgLifeMonths = config.monthly_churn > 0 ? 1 / config.monthly_churn : config.avg_contract_months

  return (
    <div className="space-y-5">
      {/* ═══ SKU DEFINITION TABLE ═══ */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">SKU定義</h4>
          <button onClick={addSKU} className="text-[10px] text-gold-600 hover:text-gold-500">+ SKU追加</button>
        </div>
        <div className="bg-cream-50 rounded-2xl border border-cream-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cream-200">
                <th className="text-left px-3 py-2 text-sand-500 font-medium">SKU名</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">単価(税抜)</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium whitespace-nowrap">商品数/取引</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium whitespace-nowrap">取引回数/人</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium whitespace-nowrap">年間購入回数</th>
                <th className="text-right px-3 py-2 text-gold-600 font-semibold whitespace-nowrap">一人あたり売上</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.skus.map(function(sku) {
                var revPerPerson = computeUnitEconRevPerPerson(sku)
                return (
                  <tr key={sku.id} className="border-b border-cream-200 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={sku.name}
                        onChange={function(e) { updateSKU(sku.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-dark-900 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <NumInput value={sku.price} onChange={function(v) { updateSKU(sku.id, { price: v }) }}
                        suffix="円" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <NumInput value={sku.items_per_txn} onChange={function(v) { updateSKU(sku.id, { items_per_txn: v }) }}
                        step={0.1} min={0.1} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <NumInput value={sku.txns_per_person} onChange={function(v) { updateSKU(sku.id, { txns_per_person: v }) }}
                        step={0.1} min={0.1} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <NumInput value={sku.annual_purchases} onChange={function(v) { updateSKU(sku.id, { annual_purchases: v }) }}
                        step={1} min={1} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="font-mono font-semibold text-gold-600">{formatYen(revPerPerson)}円</span>
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

      {/* ═══ UNIT ECONOMICS TABLE ═══ */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">UNIT ECONOMICS</h4>
        <div className="bg-cream-100 rounded-2xl border border-cream-200 overflow-hidden">
          <div className="grid grid-cols-5 divide-x divide-cream-200">
            {/* CAC */}
            <div className="px-3 py-3 text-center">
              <div className="text-[9px] text-sand-500 mb-1">CAC</div>
              <div className="mb-1">
                <NumInput value={config.cac}
                  onChange={function(v) { onChange({ ...config, cac: v }) }}
                  className="text-center font-semibold text-dark-900" suffix="円" />
              </div>
              <div className="text-[9px] text-sand-400">顧客獲得コスト</div>
            </div>

            {/* LTV */}
            <div className="px-3 py-3 text-center">
              <div className="text-[9px] text-sand-500 mb-1">LTV</div>
              <div className="text-sm font-mono font-bold text-gold-600 mb-1">{formatYen(ltv)}円</div>
              <div className="text-[9px] text-sand-400">生涯顧客価値</div>
            </div>

            {/* LTV/CAC */}
            <div className="px-3 py-3 text-center">
              <div className="text-[9px] text-sand-500 mb-1">LTV/CAC</div>
              <div className={'text-sm font-mono font-bold mb-1 '
                + (ltvCac >= 3 ? 'text-green-600' : ltvCac >= 1 ? 'text-amber-600' : 'text-red-600')}>
                {ltvCac.toFixed(1)}x
              </div>
              <div className={'text-[9px] ' + (ltvCac >= 3 ? 'text-green-500' : ltvCac >= 1 ? 'text-amber-500' : 'text-red-500')}>
                {ltvCac >= 3 ? '健全' : ltvCac >= 1 ? '要注意' : '危険'}
              </div>
            </div>

            {/* Payback */}
            <div className="px-3 py-3 text-center">
              <div className="text-[9px] text-sand-500 mb-1">回収期間</div>
              <div className={'text-sm font-mono font-bold mb-1 '
                + (payback <= 12 ? 'text-green-600' : payback <= 24 ? 'text-amber-600' : 'text-red-600')}>
                {payback.toFixed(0)}ヶ月
              </div>
              <div className="text-[9px] text-sand-400">CAC回収</div>
            </div>

            {/* Monthly Churn */}
            <div className="px-3 py-3 text-center">
              <div className="text-[9px] text-sand-500 mb-1">月次解約率</div>
              <div className="mb-1">
                <NumInput value={config.monthly_churn * 100}
                  onChange={function(v) { onChange({ ...config, monthly_churn: v / 100 }) }}
                  className={'text-center font-semibold ' + (config.monthly_churn <= 0.03 ? 'text-green-600' : config.monthly_churn <= 0.05 ? 'text-amber-600' : 'text-red-600')}
                  suffix="%" step={0.1} min={0} max={100} />
              </div>
              <div className="text-[9px] text-sand-400">平均{avgLifeMonths.toFixed(0)}ヶ月</div>
            </div>
          </div>
        </div>

        {/* Reference bars */}
        <div className="mt-2 flex gap-2 text-[9px] text-sand-400">
          <span>基準: LTV/CAC</span>
          <span className="text-green-500">3x以上=健全</span>
          <span className="text-amber-500">1-3x=要注意</span>
          <span className="text-red-500">1x未満=危険</span>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Inline numeric input
// ---------------------------------------------------------------------------
function NumInput({ value, onChange, suffix, step, min, max, className }: {
  value: number; onChange: (v: number) => void
  suffix?: string; step?: number; min?: number; max?: number; className?: string
}) {
  var [editing, setEditing] = useState(false)
  var [draft, setDraft] = useState('')

  function startEdit() {
    setDraft(String(value))
    setEditing(true)
  }

  function commit() {
    var n = parseFloat(draft.replace(/[,\s円%万億]/g, ''))
    if (!isNaN(n)) {
      if (min != null && n < min) n = min
      if (max != null && n > max) n = max
      onChange(n)
    }
    setEditing(false)
  }

  if (editing) {
    return (
      <input type="text" value={draft}
        onChange={function(e) { setDraft(e.target.value) }}
        onBlur={commit}
        onKeyDown={function(e) { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') setEditing(false) }}
        autoFocus
        className="w-20 text-right bg-white border border-gold-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-gold-400"
      />
    )
  }

  return (
    <button onClick={startEdit}
      className={'font-mono text-[11px] px-1 py-0.5 rounded border border-transparent hover:border-gold-300 hover:bg-cream-100 cursor-pointer transition-colors ' + (className || 'text-dark-900')}>
      {value.toLocaleString()}{suffix || ''}
    </button>
  )
}
