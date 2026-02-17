'use client'

/**
 * Academy archetype configuration panel.
 *
 * Screenshot reference: ティア構成 + レート + 受講者フロー
 * - Tiers: Level(C/B/A/S), コース名, 受講料, 概要
 * - Rates: 修了率, 認定率, 進級率 per tier
 * - Flow: FY1-FY5 受講者数 per tier (with advancement arrows)
 */

import { useState } from 'react'
import type { AcademyConfig, AcademyTier } from './types'

interface Props {
  config: AcademyConfig
  onChange: (config: AcademyConfig) => void
}

var FY_LABELS = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']
var LEVEL_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  C: { bg: 'bg-cream-100', text: 'text-sand-600', border: 'border-cream-300' },
  B: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  A: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' },
  S: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300' },
}

function formatYen(v: number): string {
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '億'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toLocaleString()
}

export function AcademyPanel({ config, onChange }: Props) {
  var [showFlow, setShowFlow] = useState(true)

  function updateTier(id: string, patch: Partial<AcademyTier>) {
    onChange({
      ...config,
      tiers: config.tiers.map(function(t) { return t.id === id ? { ...t, ...patch } : t }),
    })
  }

  function updateStudents(id: string, fyIdx: number, val: number) {
    onChange({
      ...config,
      tiers: config.tiers.map(function(t) {
        if (t.id !== id) return t
        var newS = t.students.slice()
        newS[fyIdx] = val
        return { ...t, students: newS }
      }),
    })
  }

  function addTier() {
    var levels = ['C', 'B', 'A', 'S', 'SS', 'SSS']
    var nextLevel = levels[config.tiers.length] || 'X'
    var newTier: AcademyTier = {
      id: 'tier_' + Date.now().toString(36),
      level: nextLevel,
      name: nextLevel + 'コース',
      price: 100000 * (config.tiers.length + 1),
      description: '',
      completion_rate: 0.80,
      certification_rate: 0.65,
      advancement_rate: 0.40,
      students: [50, 80, 120, 170, 230],
    }
    onChange({ ...config, tiers: [...config.tiers, newTier] })
  }

  function removeTier(id: string) {
    onChange({ ...config, tiers: config.tiers.filter(function(t) { return t.id !== id }) })
  }

  // Revenue per FY
  var fyRevenue = FY_LABELS.map(function(_, fi) {
    return config.tiers.reduce(function(sum, tier) {
      return sum + (tier.students[fi] || 0) * tier.price
    }, 0)
  })

  return (
    <div className="space-y-5">
      {/* ═══ TIER DEFINITION ═══ */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">コース/ティア構成</h4>
          <button onClick={addTier} className="text-[10px] text-gold-600 hover:text-gold-500">+ ティア追加</button>
        </div>
        <div className="bg-cream-50 rounded-2xl border border-cream-200 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-cream-200">
                <th className="text-center px-2 py-2 text-sand-500 font-medium w-10">Lv</th>
                <th className="text-left px-3 py-2 text-sand-500 font-medium">コース名</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">受講料</th>
                <th className="text-left px-3 py-2 text-sand-500 font-medium">概要</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {config.tiers.map(function(tier) {
                var lc = LEVEL_COLORS[tier.level] || LEVEL_COLORS.C
                return (
                  <tr key={tier.id} className="border-b border-cream-200 last:border-0 hover:bg-white">
                    <td className="px-2 py-2 text-center">
                      <span className={'inline-flex items-center justify-center w-6 h-6 rounded font-bold text-[10px] ' + lc.bg + ' ' + lc.text}>
                        {tier.level}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <input type="text" value={tier.name}
                        onChange={function(e) { updateTier(tier.id, { name: e.target.value }) }}
                        className="w-full bg-transparent font-medium text-dark-900 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <CellInput value={tier.price} onChange={function(v) { updateTier(tier.id, { price: v }) }} />
                      <span className="text-sand-400 text-[10px]">円</span>
                    </td>
                    <td className="px-3 py-2">
                      <input type="text" value={tier.description}
                        onChange={function(e) { updateTier(tier.id, { description: e.target.value }) }}
                        placeholder="コースの概要"
                        className="w-full bg-transparent text-sand-600 outline-none focus:bg-cream-100 focus:rounded px-1 -mx-1 text-[10px]" />
                    </td>
                    <td className="px-1 py-2">
                      {config.tiers.length > 1 && (
                        <button onClick={function() { removeTier(tier.id) }}
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

      {/* ═══ RATES TABLE ═══ */}
      <div>
        <h4 className="text-xs font-semibold text-sand-600 mb-2">進級・修了レート</h4>
        <div className="bg-purple-50 rounded-2xl border border-purple-100 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-purple-200">
                <th className="text-center px-2 py-2 text-sand-500 font-medium w-10">Lv</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">修了率</th>
                <th className="text-right px-3 py-2 text-sand-500 font-medium">認定率</th>
                <th className="text-right px-3 py-2 text-purple-600 font-semibold">進級率</th>
                <th className="px-3 py-2 text-sand-500 font-medium text-center">フロー</th>
              </tr>
            </thead>
            <tbody>
              {config.tiers.map(function(tier, idx) {
                var lc = LEVEL_COLORS[tier.level] || LEVEL_COLORS.C
                var isLast = idx === config.tiers.length - 1
                var fy1Students = tier.students[0] || 0
                var completers = Math.round(fy1Students * tier.completion_rate)
                var certified = Math.round(completers * tier.certification_rate)
                var advancing = isLast ? 0 : Math.round(certified * tier.advancement_rate)

                return (
                  <tr key={tier.id} className="border-b border-purple-100 last:border-0 hover:bg-white/50">
                    <td className="px-2 py-2 text-center">
                      <span className={'inline-flex items-center justify-center w-6 h-6 rounded font-bold text-[10px] ' + lc.bg + ' ' + lc.text}>
                        {tier.level}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <PctInput value={tier.completion_rate} onChange={function(v) { updateTier(tier.id, { completion_rate: v }) }} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <PctInput value={tier.certification_rate} onChange={function(v) { updateTier(tier.id, { certification_rate: v }) }} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isLast ? (
                        <span className="text-sand-400">—</span>
                      ) : (
                        <PctInput value={tier.advancement_rate} onChange={function(v) { updateTier(tier.id, { advancement_rate: v }) }} />
                      )}
                    </td>
                    <td className="px-3 py-2 text-center text-[9px] text-sand-400">
                      {fy1Students}人 → {completers}修了 → {certified}認定
                      {!isLast && <span className="text-purple-500"> → {advancing}進級</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ═══ STUDENT FLOW (FY1-FY5) ═══ */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-sand-600">受講者数推移</h4>
          <button onClick={function() { setShowFlow(!showFlow) }}
            className="text-[10px] text-sand-400 hover:text-sand-600">
            {showFlow ? '閉じる' : '開く'}
          </button>
        </div>
        {showFlow && (
          <div className="bg-purple-50 rounded-2xl border border-purple-100 overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-purple-200">
                  <th className="text-left px-3 py-2 text-sand-500 font-medium">ティア</th>
                  {FY_LABELS.map(function(fy) {
                    return <th key={fy} className="text-right px-3 py-2 text-purple-600 font-medium">{fy}</th>
                  })}
                </tr>
              </thead>
              <tbody>
                {config.tiers.map(function(tier) {
                  var lc = LEVEL_COLORS[tier.level] || LEVEL_COLORS.C
                  return (
                    <tr key={tier.id} className="border-b border-purple-100 last:border-0 hover:bg-white/50">
                      <td className="px-3 py-2">
                        <span className={'inline-flex items-center gap-1'}>
                          <span className={'w-4 h-4 rounded text-[8px] font-bold flex items-center justify-center ' + lc.bg + ' ' + lc.text}>{tier.level}</span>
                          <span className="text-sand-600 font-medium">{tier.name}</span>
                        </span>
                      </td>
                      {FY_LABELS.map(function(_, fi) {
                        return (
                          <td key={fi} className="px-3 py-2 text-right">
                            <CellInput
                              value={tier.students[fi] || 0}
                              onChange={function(v) { updateStudents(tier.id, fi, v) }}
                              integer
                            />
                            <span className="text-sand-400 text-[10px]">人</span>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
                {/* Revenue row */}
                <tr className="border-t-2 border-purple-200 bg-purple-100/50">
                  <td className="px-3 py-2 font-semibold text-sand-600">売上合計</td>
                  {fyRevenue.map(function(rev, fi) {
                    return (
                      <td key={fi} className="px-3 py-2 text-right font-mono font-bold text-purple-700">
                        {formatYen(rev)}円
                      </td>
                    )
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* Visual flow diagram */}
        {showFlow && config.tiers.length > 1 && (
          <div className="mt-3 flex items-center justify-center gap-2">
            {config.tiers.map(function(tier, idx) {
              var lc = LEVEL_COLORS[tier.level] || LEVEL_COLORS.C
              var isLast = idx === config.tiers.length - 1
              return (
                <div key={tier.id} className="flex items-center gap-2">
                  <div className={'rounded-2xl px-3 py-2 border text-center ' + lc.bg + ' ' + lc.border}>
                    <div className={'text-xs font-bold ' + lc.text}>{tier.level}</div>
                    <div className="text-[9px] text-sand-500">{tier.students[0] || 0}人</div>
                    <div className="text-[9px] text-sand-400">{formatYen(tier.price)}円</div>
                  </div>
                  {!isLast && (
                    <div className="flex flex-col items-center">
                      <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      <span className="text-[8px] text-purple-400">{(tier.advancement_rate * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
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

  function startEdit() { setDraft(String(value)); setEditing(true) }
  function commit() {
    var n = integer ? parseInt(draft.replace(/[,\s]/g, '')) : parseFloat(draft.replace(/[,\s]/g, ''))
    if (!isNaN(n) && n >= 0) onChange(n)
    setEditing(false)
  }

  if (editing) return (
    <input type="text" value={draft}
      onChange={function(e) { setDraft(e.target.value) }}
      onBlur={commit}
      onKeyDown={function(e) { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') setEditing(false) }}
      autoFocus
      className="w-14 text-right bg-white border border-gold-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-gold-400" />
  )
  return (
    <button onClick={startEdit}
      className="font-mono text-[11px] text-dark-900 px-1 py-0.5 rounded border border-transparent hover:border-gold-300 hover:bg-cream-100 cursor-pointer transition-colors">
      {value.toLocaleString()}
    </button>
  )
}

function PctInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  var [editing, setEditing] = useState(false)
  var [draft, setDraft] = useState('')

  function startEdit() { setDraft(String(Math.round(value * 100))); setEditing(true) }
  function commit() {
    var n = parseFloat(draft.replace(/[%％\s]/g, ''))
    if (!isNaN(n) && n >= 0 && n <= 100) onChange(n / 100)
    setEditing(false)
  }

  if (editing) return (
    <input type="text" value={draft}
      onChange={function(e) { setDraft(e.target.value) }}
      onBlur={commit}
      onKeyDown={function(e) { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') setEditing(false) }}
      autoFocus
      className="w-12 text-right bg-white border border-gold-300 rounded px-1 py-0.5 text-[11px] font-mono outline-none focus:ring-1 focus:ring-gold-400" />
  )
  return (
    <button onClick={startEdit}
      className="font-mono text-[11px] text-purple-700 px-1 py-0.5 rounded border border-transparent hover:border-purple-300 hover:bg-purple-50 cursor-pointer transition-colors">
      {(value * 100).toFixed(0)}%
    </button>
  )
}
