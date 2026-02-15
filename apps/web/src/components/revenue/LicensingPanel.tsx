'use client'

/**
 * Licensing (ライセンス) archetype configuration panel.
 *
 * License fee, maintenance rate, cumulative license count, renewal rate.
 */

import { useState } from 'react'
import type { LicensingConfig, LicenseProduct } from './types'

interface Props {
  config: LicensingConfig
  onChange: (config: LicensingConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function LicensingPanel({ config, onChange }: Props) {
  function updateProduct(id: string, patch: Partial<LicenseProduct>) {
    onChange({ ...config, products: config.products.map(function(p) { return p.id === id ? { ...p, ...patch } : p }) })
  }

  function updateLicenses(id: string, fi: number, val: number) {
    onChange({
      ...config,
      products: config.products.map(function(p) {
        if (p.id !== id) return p
        var newL = p.licenses.slice(); newL[fi] = val
        return { ...p, licenses: newL }
      }),
    })
  }

  function addProduct() {
    var p: LicenseProduct = {
      id: 'lic_' + Date.now().toString(36),
      name: '製品' + String.fromCharCode(65 + config.products.length),
      license_fee: 1000000,
      maintenance_rate: 0.18,
      licenses: [10, 25, 50, 80, 120],
    }
    onChange({ ...config, products: [...config.products, p] })
  }

  function removeProduct(id: string) {
    onChange({ ...config, products: config.products.filter(function(p) { return p.id !== id }) })
  }

  // Revenue per FY: new licenses × fee + existing licenses × fee × maintenance_rate
  var fyRevenue = FY_LABELS.map(function(_, fi) {
    return config.products.reduce(function(sum, p) {
      var cumLicenses = p.licenses[fi] || 0
      var prevLicenses = fi > 0 ? (p.licenses[fi - 1] || 0) : 0
      var newLicenses = Math.max(0, cumLicenses - prevLicenses)
      var renewedLicenses = prevLicenses * config.renewal_rate
      var newLicenseRev = newLicenses * p.license_fee
      var maintenanceRev = renewedLicenses * p.license_fee * p.maintenance_rate
      return sum + newLicenseRev + maintenanceRev
    }, 0)
  })

  return (
    <div className="space-y-5">
      {/* Product definitions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-700">ライセンス製品定義</h4>
          <button onClick={addProduct} className="text-[10px] text-indigo-600 hover:text-indigo-800">+ 製品追加</button>
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">製品名</th>
                <th className="text-right px-3 py-2 text-gray-500 font-medium">ライセンス料</th>
                <th className="text-right px-3 py-2 text-gray-500 font-medium">保守料率</th>
                <th className="text-right px-3 py-2 text-indigo-600 font-semibold">年間保守料</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.products.map(function(prod) {
                return (
                  <tr key={prod.id} className="border-b border-gray-100 last:border-0 hover:bg-white">
                    <td className="px-3 py-2">
                      <input type="text" value={prod.name}
                        onChange={function(e) { updateProduct(prod.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-gray-900 outline-none focus:bg-indigo-50 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={prod.license_fee} onChange={function(v) { updateProduct(prod.id, { license_fee: v }) }} integer />
                      <span className="text-[10px] text-gray-400">円</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={prod.maintenance_rate * 100} onChange={function(v) { updateProduct(prod.id, { maintenance_rate: v / 100 }) }} />
                      <span className="text-[10px] text-gray-400">%</span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-indigo-700">
                      {formatYen(prod.license_fee * prod.maintenance_rate)}円/年
                    </td>
                    <td className="px-1 py-2">
                      {config.products.length > 1 && (
                        <button onClick={function() { removeProduct(prod.id) }} className="text-gray-300 hover:text-red-500 transition-colors">
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

      {/* Renewal rate */}
      <div className="flex items-center gap-3 text-[11px] px-1">
        <span className="text-gray-500 font-medium">ライセンス更新率:</span>
        <CellInput value={config.renewal_rate * 100}
          onChange={function(v) { onChange({ ...config, renewal_rate: v / 100 }) }} />
        <span className="text-gray-400">%</span>
      </div>

      {/* License count projections */}
      <div>
        <h4 className="text-xs font-semibold text-gray-700 mb-2">累計ライセンス数推移</h4>
        <div className="bg-indigo-50 rounded-lg border border-indigo-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-indigo-200">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">製品</th>
                {FY_LABELS.map(function(fy) {
                  return <th key={fy} className="text-right px-3 py-2 text-indigo-600 font-medium">{fy}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {config.products.map(function(prod) {
                return (
                  <tr key={prod.id} className="border-b border-indigo-100 last:border-0 hover:bg-white/50">
                    <td className="px-3 py-2 font-medium text-gray-700">{prod.name}</td>
                    {FY_LABELS.map(function(_, fi) {
                      return (
                        <td key={fi} className="px-3 py-2 text-right">
                          <CellInput value={prod.licenses[fi] || 0} onChange={function(v) { updateLicenses(prod.id, fi, v) }} integer />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              <tr className="border-t-2 border-indigo-200 bg-indigo-100/50">
                <td className="px-3 py-2 font-semibold text-gray-700">売上</td>
                {fyRevenue.map(function(rev, fi) {
                  return <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-indigo-700">{formatYen(rev)}円</td>
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
      autoFocus className="w-16 text-right bg-white border border-indigo-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-indigo-400" />
  )
  return (
    <button onClick={startEdit} className="font-mono text-[11px] text-gray-900 px-1 py-0.5 rounded border border-transparent hover:border-indigo-300 hover:bg-indigo-50 cursor-pointer transition-colors">
      {(integer ? Math.round(value) : value).toLocaleString()}
    </button>
  )
}
