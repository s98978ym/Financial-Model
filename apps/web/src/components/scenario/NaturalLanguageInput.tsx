'use client'

import { useState, useRef, useEffect } from 'react'

interface NaturalLanguageInputProps {
  parameters: Record<string, number>
  onParameterChange: (key: string, value: number) => void
  onBatchChange: (changes: Record<string, number>) => void
  onPropose?: (changes: Record<string, number>, sourceDetail: string) => void
}

interface ChatMessage {
  role: 'user' | 'system'
  text: string
}

/**
 * Parse natural language input to parameter changes.
 * Handles Japanese financial expressions.
 */
function parseNaturalLanguage(
  input: string,
  currentParams: Record<string, number>
): Record<string, number> | null {
  var changes: Record<string, number> = {}
  var text = input.toLowerCase().trim()

  // Revenue patterns
  var revenuePatterns = [
    /売上[をは]?\s*([0-9,.]+)\s*(億|万)?\s*(円)?/,
    /初年度売上[をは]?\s*([0-9,.]+)\s*(億|万)?\s*(円)?/,
    /revenue[をは]?\s*([0-9,.]+)\s*(億|万)?\s*(円)?/,
  ]
  for (var i = 0; i < revenuePatterns.length; i++) {
    var match = text.match(revenuePatterns[i])
    if (match) {
      var val = parseFloat(match[1].replace(/,/g, ''))
      if (match[2] === '億') val *= 100_000_000
      else if (match[2] === '万') val *= 10_000
      else if (val < 1000) val *= 100_000_000 // assume 億 if small number
      changes.revenue_fy1 = val
    }
  }

  // Growth rate patterns
  var growthPatterns = [
    /成長率[をは]?\s*([0-9,.]+)\s*(%|％|パーセント)?/,
    /growth[をは]?\s*([0-9,.]+)\s*(%|％)?/,
    /売上成長[をは]?\s*([0-9,.]+)\s*(%|％)?/,
  ]
  for (var i2 = 0; i2 < growthPatterns.length; i2++) {
    var gMatch = text.match(growthPatterns[i2])
    if (gMatch) {
      var gVal = parseFloat(gMatch[1].replace(/,/g, ''))
      changes.growth_rate = gVal > 1 ? gVal / 100 : gVal
    }
  }

  // COGS rate patterns
  var cogsPatterns = [
    /原価率[をは]?\s*([0-9,.]+)\s*(%|％)?/,
    /cogs[をは]?\s*([0-9,.]+)\s*(%|％)?/,
    /売上原価[をは]?\s*([0-9,.]+)\s*(%|％)?/,
  ]
  for (var i3 = 0; i3 < cogsPatterns.length; i3++) {
    var cMatch = text.match(cogsPatterns[i3])
    if (cMatch) {
      var cVal = parseFloat(cMatch[1].replace(/,/g, ''))
      changes.cogs_rate = cVal > 1 ? cVal / 100 : cVal
    }
  }

  // OPEX patterns
  var opexPatterns = [
    /(?:opex|販管費|経費)[をは]?\s*([0-9,.]+)\s*(億|万)?\s*(円)?/,
    /固定費[をは]?\s*([0-9,.]+)\s*(億|万)?\s*(円)?/,
  ]
  for (var i4 = 0; i4 < opexPatterns.length; i4++) {
    var oMatch = text.match(opexPatterns[i4])
    if (oMatch) {
      var oVal = parseFloat(oMatch[1].replace(/,/g, ''))
      if (oMatch[2] === '億') oVal *= 100_000_000
      else if (oMatch[2] === '万') oVal *= 10_000
      else if (oVal < 1000) oVal *= 100_000_000
      changes.opex_base = oVal
    }
  }

  // OPEX growth patterns
  var opexGrowthPatterns = [
    /opex増加率[をは]?\s*([0-9,.]+)\s*(%|％)?/,
    /経費増加[をは]?\s*([0-9,.]+)\s*(%|％)?/,
    /販管費増加[をは]?\s*([0-9,.]+)\s*(%|％)?/,
  ]
  for (var i5 = 0; i5 < opexGrowthPatterns.length; i5++) {
    var ogMatch = text.match(opexGrowthPatterns[i5])
    if (ogMatch) {
      var ogVal = parseFloat(ogMatch[1].replace(/,/g, ''))
      changes.opex_growth = ogVal > 1 ? ogVal / 100 : ogVal
    }
  }

  // Relative changes: "売上を2倍にして" / "原価率を10%下げて"
  var doubleMatch = text.match(/売上[をは]?\s*([0-9,.]+)\s*倍/)
  if (doubleMatch) {
    var multiplier = parseFloat(doubleMatch[1])
    changes.revenue_fy1 = (currentParams.revenue_fy1 || 100_000_000) * multiplier
  }

  var increaseMatch = text.match(/(売上|成長率|原価率|opex|販管費)[をは]?\s*([0-9,.]+)\s*(%|％)?\s*(上げ|あげ|増やし|アップ)/)
  if (increaseMatch) {
    var targetKey = ''
    if (increaseMatch[1].indexOf('売上') !== -1) targetKey = 'revenue_fy1'
    else if (increaseMatch[1].indexOf('成長') !== -1) targetKey = 'growth_rate'
    else if (increaseMatch[1].indexOf('原価') !== -1) targetKey = 'cogs_rate'
    else targetKey = 'opex_base'

    var incVal = parseFloat(increaseMatch[2])
    if (targetKey === 'revenue_fy1' || targetKey === 'opex_base') {
      // Percentage increase of absolute value
      var currentVal = currentParams[targetKey] || 100_000_000
      changes[targetKey] = currentVal * (1 + incVal / 100)
    } else {
      // Add percentage points
      var currentRate = currentParams[targetKey] || 0.3
      changes[targetKey] = currentRate + incVal / 100
    }
  }

  var decreaseMatch = text.match(/(売上|成長率|原価率|opex|販管費)[をは]?\s*([0-9,.]+)\s*(%|％)?\s*(下げ|さげ|減らし|ダウン|カット)/)
  if (decreaseMatch) {
    var targetKey2 = ''
    if (decreaseMatch[1].indexOf('売上') !== -1) targetKey2 = 'revenue_fy1'
    else if (decreaseMatch[1].indexOf('成長') !== -1) targetKey2 = 'growth_rate'
    else if (decreaseMatch[1].indexOf('原価') !== -1) targetKey2 = 'cogs_rate'
    else targetKey2 = 'opex_base'

    var decVal = parseFloat(decreaseMatch[2])
    if (targetKey2 === 'revenue_fy1' || targetKey2 === 'opex_base') {
      var currentVal2 = currentParams[targetKey2] || 100_000_000
      changes[targetKey2] = currentVal2 * (1 - decVal / 100)
    } else {
      var currentRate2 = currentParams[targetKey2] || 0.3
      changes[targetKey2] = currentRate2 - decVal / 100
    }
  }

  if (Object.keys(changes).length === 0) return null
  return changes
}

var PARAM_LABELS: Record<string, string> = {
  revenue_fy1: '初年度売上',
  growth_rate: '売上成長率',
  cogs_rate: '売上原価率',
  opex_base: '初年度OPEX',
  opex_growth: 'OPEX増加率',
}

function formatChangeValue(key: string, value: number): string {
  if (key.includes('rate') || key.includes('growth')) {
    return (value * 100).toFixed(0) + '%'
  }
  if (value >= 100_000_000) return (value / 100_000_000).toFixed(1) + '億円'
  if (value >= 10_000) return (value / 10_000).toFixed(0) + '万円'
  return value.toLocaleString() + '円'
}

var EXAMPLES = [
  '売上を2億円にして',
  '原価率を20%に下げて',
  '成長率50%、OPEX 1億円',
  '売上を2倍にして',
]

export function NaturalLanguageInput({ parameters, onParameterChange, onBatchChange, onPropose }: NaturalLanguageInputProps) {
  var [input, setInput] = useState('')
  var [messages, setMessages] = useState<ChatMessage[]>([])
  var messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(function() {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim()) return

    var userMessage = input.trim()
    setInput('')

    var newMessages: ChatMessage[] = messages.concat([{ role: 'user', text: userMessage }])

    var changes = parseNaturalLanguage(userMessage, parameters)

    if (changes) {
      var descriptions: string[] = []
      var keys = Object.keys(changes)
      for (var i = 0; i < keys.length; i++) {
        var key = keys[i]
        descriptions.push((PARAM_LABELS[key] || key) + ' → ' + formatChangeValue(key, changes[key]))
      }

      // Route through proposal confirmation when onPropose is available
      if (onPropose) {
        onPropose(changes, userMessage)
        newMessages = newMessages.concat([{
          role: 'system',
          text: '変更を提案しました（確認待ち）:\n' + descriptions.join('\n'),
        }])
      } else {
        newMessages = newMessages.concat([{
          role: 'system',
          text: '変更を適用しました:\n' + descriptions.join('\n'),
        }])
        // Direct apply fallback
        if (keys.length === 1) {
          onParameterChange(keys[0], changes[keys[0]])
        } else {
          onBatchChange(changes)
        }
      }
    } else {
      newMessages = newMessages.concat([{
        role: 'system',
        text: 'パラメータの変更を認識できませんでした。\n例: 「売上を2億円にして」「原価率を20%に」「成長率50%」',
      }])
    }

    setMessages(newMessages)
  }

  function handleExample(example: string) {
    setInput(example)
  }

  return (
    <div className="bg-white rounded-3xl shadow-warm overflow-hidden">
      <div className="px-5 py-3 border-b border-cream-200">
        <h3 className="font-medium text-dark-900 text-sm">自然言語で調整</h3>
        <p className="text-xs text-sand-500 mt-0.5">変更したい内容を日本語で入力してください</p>
      </div>

      {/* Messages */}
      {messages.length > 0 && (
        <div className="px-4 py-3 max-h-40 overflow-y-auto space-y-2 bg-cream-100 border-b border-cream-200">
          {messages.map(function(msg, i) {
            return (
              <div
                key={i}
                className={'text-xs rounded-lg px-3 py-2 max-w-[85%] whitespace-pre-line ' + (
                  msg.role === 'user'
                    ? 'ml-auto bg-dark-900 text-white'
                    : 'bg-white border border-cream-200 text-sand-600'
                )}
              >
                {msg.text}
              </div>
            )
          })}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={function(e) { setInput(e.target.value) }}
            placeholder="例: 売上を2億円にして"
            className="flex-1 text-sm border border-cream-200 rounded-2xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="bg-dark-900 text-white px-4 py-2 rounded-2xl text-sm hover:bg-dark-800 disabled:bg-cream-300 disabled:cursor-not-allowed transition-colors"
          >
            適用
          </button>
        </div>

        {/* Example chips */}
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {EXAMPLES.map(function(example) {
              return (
                <button
                  key={example}
                  type="button"
                  onClick={function() { handleExample(example) }}
                  className="text-xs px-2.5 py-1 rounded-full bg-cream-200 text-sand-600 hover:bg-cream-300 hover:text-gold-600 transition-colors"
                >
                  {example}
                </button>
              )
            })}
          </div>
        )}
      </form>
    </div>
  )
}
