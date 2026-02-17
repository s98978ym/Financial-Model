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

function formatYen(v: number): string {
  if (Math.abs(v) >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(v) >= 10_000) return (v / 10_000).toFixed(0) + '万円'
  return v.toLocaleString() + '円'
}

function parseManInput(text: string): number {
  var s = text.trim().replace(/,/g, '').replace(/万円?/g, '').replace(/円/g, '')
  var n = parseFloat(s)
  if (isNaN(n)) return 0
  // If the original text had 万 or the number is small, treat as 万円
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

  // Compute grand total from all item amounts
  var grandTotal = 0
  themes.forEach(function(theme) {
    if (theme.amounts) {
      theme.amounts.forEach(function(a) { grandTotal += (a || 0) })
    }
  })

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
    updateTheme(catIdx, {
      name: t.name,
      items: t.items.filter(function(_, i) { return i !== itemIdx }),
      amounts: (t.amounts || []).filter(function(_, i) { return i !== itemIdx }),
    })
  }

  // Recompute grand total from themesWithAmounts
  var computedTotal = 0
  themesWithAmounts.forEach(function(t) {
    if (t.amounts) t.amounts.forEach(function(a) { computedTotal += (a || 0) })
  })

  return (
    <div className="mt-2 bg-cyan-50 rounded-lg p-3 border border-cyan-100">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] text-cyan-700 font-medium">
          開発費内訳（R&D）
          <span className="text-[10px] text-cyan-500 ml-1">合計: {formatYen(computedTotal)}</span>
        </div>
        {computedTotal !== systemTotal && systemTotal > 0 && (
          <span className="text-[9px] text-amber-600">
            sga_system: {formatYen(systemTotal)}
          </span>
        )}
      </div>

      <div className="space-y-3">
        {themesWithAmounts.map(function(theme, catIdx) {
          var catTotal = 0
          if (theme.amounts) theme.amounts.forEach(function(a) { catTotal += (a || 0) })

          return (
            <div key={catIdx} className="bg-white rounded-lg p-2.5 border border-cyan-100">
              {/* Category header */}
              <div className="flex items-center justify-between mb-1.5">
                {editingName && editingName.catIdx === catIdx && editingName.itemIdx == null ? (
                  <input
                    type="text"
                    value={editText}
                    onChange={function(e) { setEditText(e.target.value) }}
                    onBlur={commitName}
                    onKeyDown={function(e) {
                      if (e.key === 'Enter') commitName()
                      if (e.key === 'Escape') setEditingName(null)
                    }}
                    className="text-xs font-medium text-cyan-800 bg-cyan-50 border border-cyan-300 rounded px-1.5 py-0.5 flex-1 mr-2 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                    autoFocus
                  />
                ) : (
                  <button
                    onClick={function() { startEditCatName(catIdx) }}
                    className="text-xs font-medium text-cyan-800 hover:text-cyan-600 transition-colors text-left"
                    title="クリックして編集"
                  >
                    {theme.name}
                  </button>
                )}
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono text-cyan-600">{formatYen(catTotal)}</span>
                  <button
                    onClick={function() { removeCategory(catIdx) }}
                    className="text-[10px] text-gray-400 hover:text-red-500 transition-colors"
                    title="カテゴリ削除"
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* Items */}
              <div className="space-y-1.5">
                {theme.items.map(function(item, itemIdx) {
                  var amount = (theme.amounts || [])[itemIdx] || 0
                  var isEditingThisName = editingName && editingName.catIdx === catIdx && editingName.itemIdx === itemIdx
                  var isEditingThisAmount = editingAmount && editingAmount.catIdx === catIdx && editingAmount.itemIdx === itemIdx

                  return (
                    <div key={itemIdx} className="group">
                      <div className="flex items-center gap-2 mb-0.5">
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
                              className="text-[11px] text-gray-700 bg-cyan-50 border border-cyan-300 rounded px-1.5 py-0.5 w-full focus:outline-none focus:ring-1 focus:ring-cyan-400"
                              autoFocus
                            />
                          ) : (
                            <button
                              onClick={function() { startEditItemName(catIdx, itemIdx) }}
                              className="text-[11px] text-gray-700 hover:text-cyan-600 transition-colors text-left truncate w-full"
                              title="クリックして編集"
                            >
                              {item}
                            </button>
                          )}
                        </div>

                        {/* Amount display / edit */}
                        {isEditingThisAmount ? (
                          <div className="flex items-center gap-0.5">
                            <input
                              type="text"
                              value={amountText}
                              onChange={function(e) { setAmountText(e.target.value) }}
                              onBlur={commitAmount}
                              onKeyDown={function(e) {
                                if (e.key === 'Enter') commitAmount()
                                if (e.key === 'Escape') setEditingAmount(null)
                              }}
                              className="w-16 text-[11px] font-mono text-right bg-cyan-50 border border-cyan-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                              autoFocus
                            />
                            <span className="text-[9px] text-gray-400">万円</span>
                          </div>
                        ) : (
                          <button
                            onClick={function() { startEditAmount(catIdx, itemIdx) }}
                            className="text-[11px] font-mono text-gray-600 hover:text-cyan-600 transition-colors whitespace-nowrap"
                            title="クリックして金額を編集"
                          >
                            {amount > 0 ? formatYen(amount) : (
                              <span className="text-gray-300 italic">未設定</span>
                            )}
                          </button>
                        )}

                        {/* Remove item */}
                        <button
                          onClick={function() { removeItem(catIdx, itemIdx) }}
                          className="text-[10px] text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                          title="項目削除"
                        >
                          ×
                        </button>
                      </div>

                      {/* Amount slider */}
                      <input
                        type="range"
                        min={0}
                        max={30_000_000}
                        step={500_000}
                        value={amount}
                        onChange={function(e) { handleSliderChange(catIdx, itemIdx, parseFloat(e.target.value)) }}
                        className="w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                      />
                    </div>
                  )
                })}
              </div>

              {/* Add item button */}
              <button
                onClick={function() { addItem(catIdx) }}
                className="mt-1.5 text-[10px] text-cyan-500 hover:text-cyan-700 transition-colors flex items-center gap-0.5"
              >
                <span>+</span> 項目追加
              </button>
            </div>
          )
        })}
      </div>

      {/* Add category + Grand total */}
      <div className="mt-2 flex items-center justify-between">
        <button
          onClick={addCategory}
          className="text-[10px] text-cyan-600 hover:text-cyan-800 transition-colors font-medium flex items-center gap-0.5"
        >
          <span>+</span> カテゴリ追加
        </button>
        <div className="text-[11px] font-medium text-cyan-800">
          開発費合計: <span className="font-mono">{formatYen(computedTotal)}</span>
        </div>
      </div>
    </div>
  )
}
