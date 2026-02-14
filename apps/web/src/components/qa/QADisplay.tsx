'use client'

import { useState, useMemo } from 'react'
import type { QAItem, QACategory } from '@/data/qaTemplates'
import { CATEGORY_INFO } from '@/data/qaTemplates'

interface QADisplayProps {
  items: QAItem[]
}

export function QADisplay({ items }: QADisplayProps) {
  var [activeCategory, setActiveCategory] = useState<QACategory | 'all'>('all')
  var [expandedId, setExpandedId] = useState<string | null>(null)

  // Group items by category
  var categories = useMemo(function() {
    var cats: Record<string, number> = {}
    items.forEach(function(item) {
      cats[item.category] = (cats[item.category] || 0) + 1
    })
    return cats
  }, [items])

  var filteredItems = activeCategory === 'all'
    ? items
    : items.filter(function(item) { return item.category === activeCategory })

  var categoryKeys = Object.keys(categories) as QACategory[]

  function handleCopyAll() {
    var text = items.map(function(item, i) {
      return 'Q' + (i + 1) + ': ' + item.question + '\nA: ' + item.answer
    }).join('\n\n')
    navigator.clipboard.writeText(text)
  }

  function handleCopyItem(item: QAItem) {
    navigator.clipboard.writeText('Q: ' + item.question + '\nA: ' + item.answer)
  }

  if (items.length === 0) return null

  return (
    <div className="space-y-4">
      {/* Header with Category Filters */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">生成されたQ&A</h3>
            <p className="text-xs text-gray-500 mt-0.5">{items.length}問のQ&Aが{categoryKeys.length}カテゴリに分類されています</p>
          </div>
          <button
            onClick={handleCopyAll}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800 transition-colors"
          >
            全てコピー
          </button>
        </div>

        {/* Category Filter Tabs */}
        <div className="px-4 py-3 border-b border-gray-100 flex gap-2 overflow-x-auto">
          <button
            onClick={function() { setActiveCategory('all') }}
            className={'px-3 py-1.5 rounded-lg text-xs font-medium transition-all ' + (
              activeCategory === 'all'
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            全て ({items.length})
          </button>
          {categoryKeys.map(function(cat) {
            var info = CATEGORY_INFO[cat]
            return (
              <button
                key={cat}
                onClick={function() { setActiveCategory(cat) }}
                className={'px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ' + (
                  activeCategory === cat
                    ? info.bgColor + ' ' + info.color + ' border ' + info.borderColor
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}
              >
                <span>{info.icon}</span>
                {info.label} ({categories[cat]})
              </button>
            )
          })}
        </div>
      </div>

      {/* Q&A Cards by Category */}
      {activeCategory === 'all' ? (
        // Show grouped by category
        categoryKeys.map(function(cat) {
          var info = CATEGORY_INFO[cat]
          var catItems = items.filter(function(item) { return item.category === cat })
          return (
            <div key={cat} className="space-y-2">
              <div className="flex items-center gap-2 px-1">
                <span>{info.icon}</span>
                <h4 className={'text-sm font-semibold ' + info.color}>{info.label}</h4>
                <span className="text-xs text-gray-400">{catItems.length}問</span>
              </div>
              {catItems.map(function(item) {
                return (
                  <QACard
                    key={item.id}
                    item={item}
                    isExpanded={expandedId === item.id}
                    onToggle={function() { setExpandedId(expandedId === item.id ? null : item.id) }}
                    onCopy={function() { handleCopyItem(item) }}
                  />
                )
              })}
            </div>
          )
        })
      ) : (
        // Show flat list for selected category
        filteredItems.map(function(item) {
          return (
            <QACard
              key={item.id}
              item={item}
              isExpanded={expandedId === item.id}
              onToggle={function() { setExpandedId(expandedId === item.id ? null : item.id) }}
              onCopy={function() { handleCopyItem(item) }}
            />
          )
        })
      )}
    </div>
  )
}

function QACard({
  item,
  isExpanded,
  onToggle,
  onCopy,
}: {
  item: QAItem
  isExpanded: boolean
  onToggle: () => void
  onCopy: () => void
}) {
  var info = CATEGORY_INFO[item.category]
  var [copied, setCopied] = useState(false)

  function handleCopy(e: React.MouseEvent) {
    e.stopPropagation()
    onCopy()
    setCopied(true)
    setTimeout(function() { setCopied(false) }, 1500)
  }

  return (
    <div className={'rounded-xl border overflow-hidden transition-all ' + (
      isExpanded ? 'shadow-md ' + info.borderColor : 'border-gray-200 hover:border-gray-300'
    )}>
      {/* Question Header */}
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-3.5 flex items-start gap-3 hover:bg-gray-50 transition-colors"
      >
        <span className={'flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center text-xs mt-0.5 ' + info.bgColor}>
          {info.icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 leading-snug">{item.question}</div>
          {!isExpanded && (
            <div className="text-xs text-gray-400 mt-1 truncate">{item.answer}</div>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {item.tags.slice(0, 2).map(function(tag) {
            return (
              <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                {tag}
              </span>
            )
          })}
          <span className={'inline-block transition-transform text-gray-400 text-xs ' + (isExpanded ? 'rotate-180' : '')}>
            ▼
          </span>
        </div>
      </button>

      {/* Answer Body */}
      {isExpanded && (
        <div className={'px-5 pb-4 pt-0 border-t ' + info.borderColor}>
          <div className={'px-4 py-3 rounded-lg mt-3 ' + info.bgColor}>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{item.answer}</p>
          </div>
          <div className="flex justify-end mt-2">
            <button
              onClick={handleCopy}
              className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
            >
              {copied ? 'コピーしました' : 'コピー'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
