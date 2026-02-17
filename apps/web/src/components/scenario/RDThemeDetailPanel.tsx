'use client'

import { useState } from 'react'

export interface RDThemeItem {
  name: string
  items: string[]
  amounts?: number[]
}

export var DEFAULT_RD_THEMES: RDThemeItem[] = [
  { name: 'コアプロダクト開発', items: ['バックエンド開発', 'フロントエンド開発', 'UI/UXデザイン', 'QA・テスト'] },
  { name: '新規事業・機能開発', items: ['新機能企画・開発', 'PoC・プロトタイプ', '外注開発費'] },
  { name: 'インフラ・技術基盤', items: ['クラウドインフラ（AWS/GCP等）', 'DevOps・CI/CD', 'セキュリティ対応'] },
  { name: '保守・運用', items: ['バグ修正・障害対応', 'モニタリング・監視', 'その他保守'] },
]

// Category icon & accent color presets
var CAT_STYLES = [
  { accent: 'border-l-blue-500', bg: 'bg-blue-50', badge: 'bg-blue-100 text-blue-700', icon: 'code' },
  { accent: 'border-l-violet-500', bg: 'bg-violet-50', badge: 'bg-violet-100 text-violet-700', icon: 'rocket' },
  { accent: 'border-l-teal-500', bg: 'bg-teal-50', badge: 'bg-teal-100 text-teal-700', icon: 'server' },
  { accent: 'border-l-amber-500', bg: 'bg-amber-50', badge: 'bg-amber-100 text-amber-700', icon: 'wrench' },
  { accent: 'border-l-rose-500', bg: 'bg-rose-50', badge: 'bg-rose-100 text-rose-700', icon: 'sparkles' },
  { accent: 'border-l-emerald-500', bg: 'bg-emerald-50', badge: 'bg-emerald-100 text-emerald-700', icon: 'leaf' },
]

function getCatStyle(idx: number) {
  return CAT_STYLES[idx % CAT_STYLES.length]
}

// Inline SVG icons
function IconCode({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
    </svg>
  )
}

function IconRocket({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.841m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
    </svg>
  )
}

function IconServer({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
    </svg>
  )
}

function IconWrench({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
    </svg>
  )
}

function IconSparkles({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
    </svg>
  )
}

function IconLeaf({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
    </svg>
  )
}

function IconPlus({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-3.5 h-3.5'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  )
}

function IconTrash({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-3.5 h-3.5'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>
  )
}

function IconPencil({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-3 h-3'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
    </svg>
  )
}

function IconYen({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-3.5 h-3.5'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 7.5l3 4.5m0 0l3-4.5M12 12v5.25M15 12H9m6 3H9" />
    </svg>
  )
}

var ICON_COMPONENTS: Record<string, (props: { className?: string }) => JSX.Element> = {
  code: IconCode,
  rocket: IconRocket,
  server: IconServer,
  wrench: IconWrench,
  sparkles: IconSparkles,
  leaf: IconLeaf,
}

function formatYen(v: number): string {
  if (Math.abs(v) >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(v) >= 10_000) return (v / 10_000).toFixed(0) + '万円'
  return v.toLocaleString() + '円'
}

function parseManInput(text: string): number {
  var s = text.trim().replace(/,/g, '').replace(/万円?/g, '').replace(/円/g, '')
  var n = parseFloat(s)
  if (isNaN(n)) return 0
  if (/万/.test(text) || (n > 0 && n < 100_000)) return Math.round(n * 10_000)
  return Math.round(n)
}

interface RDThemeDetailPanelProps {
  themes: RDThemeItem[]
  onThemesChange: (themes: RDThemeItem[]) => void
  systemTotal: number
}

export function RDThemeDetailPanel({ themes, onThemesChange, systemTotal }: RDThemeDetailPanelProps) {
  var [editingName, setEditingName] = useState<{ catIdx: number; itemIdx?: number } | null>(null)
  var [editText, setEditText] = useState('')
  var [editingAmount, setEditingAmount] = useState<{ catIdx: number; itemIdx: number } | null>(null)
  var [amountText, setAmountText] = useState('')

  // Initialize amounts if missing — distribute systemTotal equally
  function ensureAmounts(themeList: RDThemeItem[]): RDThemeItem[] {
    var totalItems = 0
    themeList.forEach(function(t) { totalItems += t.items.length })
    var share = totalItems > 0 ? Math.round(systemTotal / totalItems) : 0
    return themeList.map(function(t) {
      if (t.amounts && t.amounts.length === t.items.length) return t
      return {
        name: t.name,
        items: t.items,
        amounts: t.items.map(function() { return share }),
      }
    })
  }

  var themesWithAmounts = ensureAmounts(themes)

  // Compute grand total
  var computedTotal = 0
  themesWithAmounts.forEach(function(t) {
    if (t.amounts) t.amounts.forEach(function(a) { computedTotal += (a || 0) })
  })

  function updateTheme(catIdx: number, updated: RDThemeItem) {
    var next = themesWithAmounts.map(function(t, i) { return i === catIdx ? updated : t })
    onThemesChange(next)
  }

  // --- Name editing ---
  function startEditCatName(catIdx: number) {
    setEditingName({ catIdx: catIdx })
    setEditText(themesWithAmounts[catIdx].name)
  }

  function startEditItemName(catIdx: number, itemIdx: number) {
    setEditingName({ catIdx: catIdx, itemIdx: itemIdx })
    setEditText(themesWithAmounts[catIdx].items[itemIdx])
  }

  function commitName() {
    if (!editingName || !editText.trim()) {
      setEditingName(null)
      return
    }
    var t = themesWithAmounts[editingName.catIdx]
    if (editingName.itemIdx != null) {
      var newItems = t.items.slice()
      newItems[editingName.itemIdx] = editText.trim()
      updateTheme(editingName.catIdx, { name: t.name, items: newItems, amounts: t.amounts })
    } else {
      updateTheme(editingName.catIdx, { name: editText.trim(), items: t.items, amounts: t.amounts })
    }
    setEditingName(null)
  }

  // --- Amount editing ---
  function startEditAmount(catIdx: number, itemIdx: number) {
    var amt = (themesWithAmounts[catIdx].amounts || [])[itemIdx] || 0
    setEditingAmount({ catIdx: catIdx, itemIdx: itemIdx })
    setAmountText((amt / 10_000).toFixed(0))
  }

  function commitAmount() {
    if (!editingAmount) return
    var val = parseManInput(amountText)
    var t = themesWithAmounts[editingAmount.catIdx]
    var newAmounts = (t.amounts || []).slice()
    newAmounts[editingAmount.itemIdx] = val
    updateTheme(editingAmount.catIdx, { name: t.name, items: t.items, amounts: newAmounts })
    setEditingAmount(null)
  }

  function handleSliderChange(catIdx: number, itemIdx: number, val: number) {
    var t = themesWithAmounts[catIdx]
    var newAmounts = (t.amounts || []).slice()
    newAmounts[itemIdx] = val
    updateTheme(catIdx, { name: t.name, items: t.items, amounts: newAmounts })
  }

  // --- Add / Remove ---
  function addCategory() {
    var next = themesWithAmounts.concat([{ name: '新規カテゴリ', items: ['新規項目'], amounts: [0] }])
    onThemesChange(next)
  }

  function removeCategory(catIdx: number) {
    if (themesWithAmounts.length <= 1) return
    var next = themesWithAmounts.filter(function(_, i) { return i !== catIdx })
    onThemesChange(next)
  }

  function addItem(catIdx: number) {
    var t = themesWithAmounts[catIdx]
    updateTheme(catIdx, {
      name: t.name,
      items: t.items.concat(['新規項目']),
      amounts: (t.amounts || []).concat([0]),
    })
  }

  function removeItem(catIdx: number, itemIdx: number) {
    var t = themesWithAmounts[catIdx]
    if (t.items.length <= 1) return
    updateTheme(catIdx, {
      name: t.name,
      items: t.items.filter(function(_, i) { return i !== itemIdx }),
      amounts: (t.amounts || []).filter(function(_, i) { return i !== itemIdx }),
    })
  }

  // Composition bar data
  var catTotals = themesWithAmounts.map(function(t) {
    var s = 0
    if (t.amounts) t.amounts.forEach(function(a) { s += (a || 0) })
    return s
  })

  return (
    <div className="mt-3 rounded-3xl shadow-warm bg-white overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cream-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-dark-900 flex items-center justify-center shadow-warm">
              <IconCode className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold text-dark-900">開発費内訳</div>
              <div className="text-[10px] text-sand-400">R&D Cost Breakdown</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-bold text-dark-900 font-mono">{formatYen(computedTotal)}</div>
            {computedTotal !== systemTotal && systemTotal > 0 && (
              <div className="text-[10px] text-amber-500">目標: {formatYen(systemTotal)}</div>
            )}
          </div>
        </div>

        {/* Composition bar */}
        {computedTotal > 0 && (
          <div className="mt-2.5">
            <div className="h-2 rounded-full overflow-hidden flex bg-cream-200">
              {catTotals.map(function(ct, idx) {
                var pct = computedTotal > 0 ? (ct / computedTotal) * 100 : 0
                var colors = [
                  'bg-blue-500', 'bg-violet-500', 'bg-teal-500',
                  'bg-amber-500', 'bg-rose-500', 'bg-emerald-500',
                ]
                return (
                  <div
                    key={idx}
                    className={colors[idx % colors.length] + ' transition-all duration-300'}
                    style={{ width: Math.max(pct, 1) + '%' }}
                    title={themesWithAmounts[idx].name + ': ' + formatYen(ct) + ' (' + pct.toFixed(0) + '%)'}
                  />
                )
              })}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
              {catTotals.map(function(ct, idx) {
                var pct = computedTotal > 0 ? (ct / computedTotal) * 100 : 0
                var style = getCatStyle(idx)
                return (
                  <div key={idx} className="flex items-center gap-1">
                    <div className={'w-2 h-2 rounded-full ' + style.badge.split(' ')[0].replace('bg-', 'bg-').replace('100', '500')} style={{ backgroundColor: ['#3b82f6', '#8b5cf6', '#14b8a6', '#f59e0b', '#f43f5e', '#10b981'][idx % 6] }} />
                    <span className="text-[9px] text-sand-500">{themesWithAmounts[idx].name} {pct.toFixed(0)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Category Cards */}
      <div className="p-3 space-y-3">
        {themesWithAmounts.map(function(theme, catIdx) {
          var catTotal = catTotals[catIdx]
          var style = getCatStyle(catIdx)
          var IconCmp = ICON_COMPONENTS[style.icon] || IconCode
          var isEditingCatName = editingName && editingName.catIdx === catIdx && editingName.itemIdx == null

          return (
            <div key={catIdx} className={'rounded-2xl border border-cream-200 bg-white overflow-hidden border-l-[3px] ' + style.accent + ' shadow-warm hover:shadow-warm-md transition-shadow'}>
              {/* Category Header */}
              <div className="px-3 py-2.5 flex items-center gap-2.5">
                <div className={'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ' + style.bg}>
                  <IconCmp className={'w-4 h-4 ' + style.badge.split(' ')[1]} />
                </div>

                <div className="flex-1 min-w-0">
                  {isEditingCatName ? (
                    <input
                      type="text"
                      value={editText}
                      onChange={function(e) { setEditText(e.target.value) }}
                      onBlur={commitName}
                      onKeyDown={function(e) {
                        if (e.key === 'Enter') commitName()
                        if (e.key === 'Escape') setEditingName(null)
                      }}
                      className="text-sm font-semibold text-dark-900 bg-cream-100 border border-gold-300 rounded-md px-2 py-0.5 w-full focus:outline-none focus:ring-2 focus:ring-gold-400"
                      autoFocus
                    />
                  ) : (
                    <div className="flex items-center gap-1.5 group/catname">
                      <span className="text-sm font-semibold text-dark-900 truncate">{theme.name}</span>
                      <button
                        onClick={function() { startEditCatName(catIdx) }}
                        className="opacity-0 group-hover/catname:opacity-100 transition-opacity p-0.5 rounded hover:bg-cream-100"
                        title="名前を編集"
                      >
                        <IconPencil className="w-3 h-3 text-sand-400" />
                      </button>
                    </div>
                  )}
                  <div className="text-[10px] text-sand-400">{theme.items.length} 項目</div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={'text-xs font-mono font-semibold px-2 py-0.5 rounded-full ' + style.badge}>
                    {formatYen(catTotal)}
                  </span>
                  {themesWithAmounts.length > 1 && (
                    <button
                      onClick={function() { removeCategory(catIdx) }}
                      className="p-1 rounded-md text-sand-300 hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="カテゴリを削除"
                    >
                      <IconTrash className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Items */}
              <div className="px-3 pb-2.5">
                <div className="space-y-1">
                  {theme.items.map(function(item, itemIdx) {
                    var amount = (theme.amounts || [])[itemIdx] || 0
                    var isEditingThisName = editingName && editingName.catIdx === catIdx && editingName.itemIdx === itemIdx
                    var isEditingThisAmount = editingAmount && editingAmount.catIdx === catIdx && editingAmount.itemIdx === itemIdx

                    return (
                      <div key={itemIdx} className="group/item rounded-lg hover:bg-cream-50 transition-colors px-2 py-1.5">
                        <div className="flex items-center gap-2">
                          {/* Dot indicator */}
                          <div className={'w-1.5 h-1.5 rounded-full flex-shrink-0 ' + (amount > 0 ? 'bg-emerald-400' : 'bg-cream-200')} />

                          {/* Item name */}
                          <div className="flex-1 min-w-0">
                            {isEditingThisName ? (
                              <input
                                type="text"
                                value={editText}
                                onChange={function(e) { setEditText(e.target.value) }}
                                onBlur={commitName}
                                onKeyDown={function(e) {
                                  if (e.key === 'Enter') commitName()
                                  if (e.key === 'Escape') setEditingName(null)
                                }}
                                className="text-xs text-sand-600 bg-cream-100 border border-gold-300 rounded-md px-2 py-0.5 w-full focus:outline-none focus:ring-2 focus:ring-gold-400"
                                autoFocus
                              />
                            ) : (
                              <div className="flex items-center gap-1 group/name">
                                <span className="text-xs text-sand-600 truncate cursor-pointer hover:text-gold-600 transition-colors" onClick={function() { startEditItemName(catIdx, itemIdx) }}>
                                  {item}
                                </span>
                                <button
                                  onClick={function() { startEditItemName(catIdx, itemIdx) }}
                                  className="opacity-0 group-hover/name:opacity-100 transition-opacity p-0.5"
                                  title="項目名を編集"
                                >
                                  <IconPencil className="w-2.5 h-2.5 text-sand-300" />
                                </button>
                              </div>
                            )}
                          </div>

                          {/* Amount display / edit */}
                          {isEditingThisAmount ? (
                            <div className="flex items-center gap-1 flex-shrink-0">
                              <div className="relative">
                                <IconYen className="w-3 h-3 text-sand-400 absolute left-1.5 top-1/2 -translate-y-1/2" />
                                <input
                                  type="text"
                                  value={amountText}
                                  onChange={function(e) { setAmountText(e.target.value) }}
                                  onBlur={commitAmount}
                                  onKeyDown={function(e) {
                                    if (e.key === 'Enter') commitAmount()
                                    if (e.key === 'Escape') setEditingAmount(null)
                                  }}
                                  className="w-20 text-xs font-mono text-right bg-white border border-gold-300 rounded-md pl-5 pr-2 py-1 focus:outline-none focus:ring-2 focus:ring-gold-400 shadow-warm"
                                  autoFocus
                                  placeholder="0"
                                />
                              </div>
                              <span className="text-[10px] text-sand-400">万円</span>
                            </div>
                          ) : (
                            <button
                              onClick={function() { startEditAmount(catIdx, itemIdx) }}
                              className={'flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono transition-all flex-shrink-0 ' + (
                                amount > 0
                                  ? 'text-sand-600 hover:bg-cream-100 hover:text-gold-600 bg-cream-50'
                                  : 'text-sand-300 hover:bg-amber-50 hover:text-amber-600 border border-dashed border-cream-200 hover:border-amber-300'
                              )}
                              title="金額を編集"
                            >
                              <IconYen className={'w-3 h-3 ' + (amount > 0 ? 'text-sand-400' : 'text-cream-300')} />
                              {amount > 0 ? formatYen(amount) : '未設定'}
                            </button>
                          )}

                          {/* Remove item */}
                          {theme.items.length > 1 && (
                            <button
                              onClick={function() { removeItem(catIdx, itemIdx) }}
                              className="p-0.5 rounded text-cream-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover/item:opacity-100 transition-all flex-shrink-0"
                              title="項目を削除"
                            >
                              <IconTrash className="w-3 h-3" />
                            </button>
                          )}
                        </div>

                        {/* Amount slider */}
                        <div className="mt-1 pl-3.5">
                          <input
                            type="range"
                            min={0}
                            max={30_000_000}
                            step={500_000}
                            value={amount}
                            onChange={function(e) { handleSliderChange(catIdx, itemIdx, parseFloat(e.target.value)) }}
                            className="w-full h-1 bg-cream-200 rounded-lg appearance-none cursor-pointer accent-gold-500"
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Add item button */}
                <button
                  onClick={function() { addItem(catIdx) }}
                  className="mt-2 ml-2 flex items-center gap-1 text-[11px] text-sand-400 hover:text-gold-600 transition-colors px-2 py-1 rounded-md hover:bg-cream-100"
                >
                  <IconPlus className="w-3 h-3" />
                  <span>項目を追加</span>
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer: Add category + summary */}
      <div className="px-4 py-3 border-t border-cream-200 flex items-center justify-between">
        <button
          onClick={addCategory}
          className="flex items-center gap-1.5 text-xs text-sand-500 hover:text-gold-600 transition-colors px-3 py-1.5 rounded-lg border border-dashed border-cream-300 hover:border-gold-400 hover:bg-cream-100"
        >
          <IconPlus className="w-3.5 h-3.5" />
          <span>カテゴリ追加</span>
        </button>

        <div className="flex items-center gap-3">
          <div className="text-[10px] text-sand-400">
            {themesWithAmounts.length} カテゴリ / {themesWithAmounts.reduce(function(s, t) { return s + t.items.length }, 0)} 項目
          </div>
          <div className="flex items-center gap-1.5 bg-cream-100 px-3 py-1.5 rounded-2xl border border-cream-200">
            <span className="text-xs text-sand-600">合計</span>
            <span className="text-sm font-bold text-dark-900 font-mono">{formatYen(computedTotal)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
