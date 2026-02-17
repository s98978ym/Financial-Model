'use client'

import { useState, useMemo, useCallback } from 'react'
import type { QAItem, QACategory } from '@/data/qaTemplates'
import { CATEGORY_INFO } from '@/data/qaTemplates'

interface QADisplayProps {
  items: QAItem[]
  onItemsChange?: (items: QAItem[]) => void
}

/** Simple markdown-like renderer for structured answers */
function RichAnswer({ text }: { text: string }) {
  var blocks = text.split('\n\n')
  return (
    <div className="space-y-3">
      {blocks.map(function(block, bi) {
        // Check if block is a list
        var lines = block.split('\n')
        var isList = lines.every(function(l) { return l.trim().startsWith('- ') || l.trim() === '' })

        if (isList) {
          return (
            <ul key={bi} className="space-y-1.5">
              {lines.filter(function(l) { return l.trim() }).map(function(line, li) {
                var content = line.replace(/^\s*- /, '')
                return (
                  <li key={li} className="flex gap-2 text-sm text-gray-700 leading-relaxed">
                    <span className="text-gray-300 mt-1 flex-shrink-0">•</span>
                    <span><InlineMarkdown text={content} /></span>
                  </li>
                )
              })}
            </ul>
          )
        }

        // Regular paragraph
        return (
          <p key={bi} className="text-sm text-gray-700 leading-relaxed">
            <InlineMarkdown text={block.replace(/\n/g, ' ')} />
          </p>
        )
      })}
    </div>
  )
}

/** Renders **bold** and regular text */
function InlineMarkdown({ text }: { text: string }) {
  var parts = text.split(/(\*\*[^*]+\*\*)/)
  return (
    <>
      {parts.map(function(part, i) {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

export function QADisplay({ items, onItemsChange }: QADisplayProps) {
  var [activeCategory, setActiveCategory] = useState<QACategory | 'all'>('all')
  var [expandedId, setExpandedId] = useState<string | null>(null)
  var [editingId, setEditingId] = useState<string | null>(null)
  var [editText, setEditText] = useState('')
  var [editQuestion, setEditQuestion] = useState('')
  var [customizeMode, setCustomizeMode] = useState(false)

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
      return 'Q' + (i + 1) + ': ' + item.question + '\nA: ' + item.answer.replace(/\*\*/g, '')
    }).join('\n\n')
    navigator.clipboard.writeText(text)
  }

  function handleCopyItem(item: QAItem) {
    navigator.clipboard.writeText('Q: ' + item.question + '\nA: ' + item.answer.replace(/\*\*/g, ''))
  }

  // Export as Markdown
  var handleExportMarkdown = useCallback(function() {
    var md = '# Q&A 想定問答集\n\n'
    var grouped: Record<string, QAItem[]> = {}
    items.forEach(function(item) {
      if (!grouped[item.category]) grouped[item.category] = []
      grouped[item.category].push(item)
    })
    Object.keys(grouped).forEach(function(cat) {
      var info = CATEGORY_INFO[cat as QACategory]
      md += '## ' + info.icon + ' ' + info.label + '\n\n'
      grouped[cat].forEach(function(item, i) {
        md += '### Q' + (i + 1) + ': ' + item.question + '\n\n'
        md += item.answer.replace(/\*\*/g, '**') + '\n\n'
      })
    })
    var blob = new Blob([md], { type: 'text/markdown' })
    var url = URL.createObjectURL(blob)
    var a = document.createElement('a')
    a.href = url
    a.download = 'qa-' + new Date().toISOString().slice(0, 10) + '.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [items])

  // Edit handlers
  function startEdit(item: QAItem) {
    setEditingId(item.id)
    setEditQuestion(item.question)
    setEditText(item.answer)
    setExpandedId(item.id)
  }

  function saveEdit() {
    if (!editingId || !onItemsChange) return
    var updated = items.map(function(item) {
      if (item.id === editingId) {
        return Object.assign({}, item, { question: editQuestion, answer: editText })
      }
      return item
    })
    onItemsChange(updated)
    setEditingId(null)
  }

  function cancelEdit() {
    setEditingId(null)
    setEditText('')
    setEditQuestion('')
  }

  // Customize handlers
  function handleDelete(id: string) {
    if (!onItemsChange) return
    onItemsChange(items.filter(function(item) { return item.id !== id }))
  }

  function handleMoveUp(id: string) {
    if (!onItemsChange) return
    var idx = items.findIndex(function(item) { return item.id === id })
    if (idx <= 0) return
    var newItems = items.slice()
    var temp = newItems[idx]
    newItems[idx] = newItems[idx - 1]
    newItems[idx - 1] = temp
    onItemsChange(newItems)
  }

  function handleMoveDown(id: string) {
    if (!onItemsChange) return
    var idx = items.findIndex(function(item) { return item.id === id })
    if (idx >= items.length - 1) return
    var newItems = items.slice()
    var temp = newItems[idx]
    newItems[idx] = newItems[idx + 1]
    newItems[idx + 1] = temp
    onItemsChange(newItems)
  }

  if (items.length === 0) return null

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 sm:px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-2">
          <div>
            <h3 className="font-semibold text-gray-900">生成されたQ&A</h3>
            <p className="text-xs text-gray-500 mt-0.5">{items.length}問・{categoryKeys.length}カテゴリ</p>
          </div>
          <div className="flex items-center gap-2">
            {onItemsChange && (
              <button
                onClick={function() { setCustomizeMode(!customizeMode) }}
                className={'text-xs px-3 py-1.5 rounded-lg border transition-colors ' + (
                  customizeMode
                    ? 'border-purple-300 bg-purple-50 text-purple-700'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                )}
              >
                {customizeMode ? '完了' : 'カスタマイズ'}
              </button>
            )}
            <button
              onClick={handleExportMarkdown}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            >
              MD出力
            </button>
            <button
              onClick={handleCopyAll}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            >
              全コピー
            </button>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="px-4 py-3 border-b border-gray-100 flex gap-2 overflow-x-auto">
          <button
            onClick={function() { setActiveCategory('all') }}
            className={'px-3 py-1.5 rounded-lg text-xs font-medium transition-all ' + (
              activeCategory === 'all' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
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
                    : 'bg-cream-200 text-sand-600 hover:bg-cream-300'
                )}
              >
                <span>{info.icon}</span>
                {info.label} ({categories[cat]})
              </button>
            )
          })}
        </div>
      </div>

      {/* Q&A Cards */}
      {activeCategory === 'all' ? (
        categoryKeys.map(function(cat) {
          var info = CATEGORY_INFO[cat]
          var catItems = items.filter(function(item) { return item.category === cat })
          return (
            <div key={cat} className="space-y-2">
              <div className="flex items-center gap-2 px-1">
                <span>{info.icon}</span>
                <h4 className={'text-sm font-semibold ' + info.color}>{info.label}</h4>
                <span className="text-xs text-sand-400">{catItems.length}問</span>
              </div>
              {catItems.map(function(item) {
                return renderCard(item)
              })}
            </div>
          )
        })
      ) : (
        filteredItems.map(function(item) { return renderCard(item) })
      )}
    </div>
  )

  function renderCard(item: QAItem) {
    var info = CATEGORY_INFO[item.category]
    var isExpanded = expandedId === item.id
    var isEditing = editingId === item.id

    return (
      <div key={item.id} className={'rounded-xl border overflow-hidden transition-all ' + (
        isExpanded ? 'shadow-md ' + info.borderColor : 'border-gray-200 hover:border-gray-300'
      )}>
        {/* Question Header */}
        <div className="flex items-start">
          {customizeMode && (
            <div className="flex flex-col gap-1 p-2 border-r border-gray-100">
              <button onClick={function() { handleMoveUp(item.id) }} className="text-xs text-gray-400 hover:text-gray-600 px-1">▲</button>
              <button onClick={function() { handleMoveDown(item.id) }} className="text-xs text-gray-400 hover:text-gray-600 px-1">▼</button>
              <button onClick={function() { handleDelete(item.id) }} className="text-xs text-red-400 hover:text-red-600 px-1">✕</button>
            </div>
          )}
          <button
            onClick={function() { setExpandedId(isExpanded ? null : item.id) }}
            className="flex-1 text-left px-4 sm:px-5 py-3.5 flex items-start gap-3 hover:bg-gray-50 transition-colors min-h-[44px]"
          >
            <span className={'flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center text-xs mt-0.5 ' + info.bgColor}>
              {info.icon}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 leading-snug">{item.question}</div>
              {!isExpanded && (
                <div className="text-xs text-gray-400 mt-1 truncate">{item.answer.replace(/\*\*/g, '').replace(/\n/g, ' ')}</div>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="hidden sm:flex gap-1">
                {item.tags.slice(0, 2).map(function(tag) {
                  return <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{tag}</span>
                })}
              </span>
              <span className={'inline-block transition-transform text-gray-400 text-xs ' + (isExpanded ? 'rotate-180' : '')}>▼</span>
            </div>
          </button>
        </div>

        {/* Answer Body */}
        {isExpanded && (
          <div className={'px-4 sm:px-5 pb-4 pt-0 border-t ' + info.borderColor}>
            {isEditing ? (
              <div className="mt-3 space-y-3">
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">質問</label>
                  <input
                    type="text"
                    value={editQuestion}
                    onChange={function(e) { setEditQuestion(e.target.value) }}
                    className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">回答（**太字** - リスト可）</label>
                  <textarea
                    value={editText}
                    onChange={function(e) { setEditText(e.target.value) }}
                    rows={8}
                    className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button onClick={cancelEdit} className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">キャンセル</button>
                  <button onClick={saveEdit} className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700">保存</button>
                </div>
              </div>
            ) : (
              <>
                <div className={'px-4 py-3 rounded-lg mt-3 ' + info.bgColor}>
                  <RichAnswer text={item.answer} />
                </div>
                <div className="flex justify-end gap-2 mt-2">
                  {onItemsChange && (
                    <button
                      onClick={function(e) { e.stopPropagation(); startEdit(item) }}
                      className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
                    >
                      編集
                    </button>
                  )}
                  <CopyButton item={item} onCopy={handleCopyItem} />
                </div>
              </>
            )}
          </div>
        )}
      </div>
    )
  }
}

function CopyButton({ item, onCopy }: { item: QAItem; onCopy: (item: QAItem) => void }) {
  var [copied, setCopied] = useState(false)
  function handleClick(e: React.MouseEvent) {
    e.stopPropagation()
    onCopy(item)
    setCopied(true)
    setTimeout(function() { setCopied(false) }, 1500)
  }
  return (
    <button onClick={handleClick} className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors">
      {copied ? 'コピー済' : 'コピー'}
    </button>
  )
}
