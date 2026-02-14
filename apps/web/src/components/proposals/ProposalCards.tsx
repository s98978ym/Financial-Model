'use client'

import { useState } from 'react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ParsedOption {
  id: string
  label: string
}

interface ParsedProposal {
  title: string
  description: string
  options: ParsedOption[]
}

interface ProposalDecision {
  proposalIndex: number
  selectedOption: string | null  // option id or 'custom'
  instruction: string
  status: 'pending' | 'decided' | 'skipped'
}

interface ProposalCardsProps {
  suggestions: string[]
  onDecisionsChange?: (decisions: ProposalDecision[]) => void
  onApplyAll?: (decisions: ProposalDecision[]) => void
}

// ---------------------------------------------------------------------------
// Parse suggestions into structured proposals
// ---------------------------------------------------------------------------

var CIRCLED_DIGITS: Record<string, number> = {
  '\u2460': 1, '\u2461': 2, '\u2462': 3, '\u2463': 4, '\u2464': 5,
  '\u2465': 6, '\u2466': 7, '\u2467': 8, '\u2468': 9,
}

function parseSuggestion(text: string): ParsedProposal {
  var options: ParsedOption[] = []
  var title = text
  var description = ''

  // Try to extract options from circled digits: ①option1 ②option2 ③option3
  var circledPattern = /[\u2460-\u2468][^\u2460-\u2468\n]*/g
  var circledMatches = text.match(circledPattern)

  if (circledMatches && circledMatches.length >= 2) {
    // Extract the part before the first circled digit as title
    var firstIdx = text.indexOf(circledMatches[0])
    title = text.substring(0, firstIdx).replace(/[（(：:、,\s]+$/, '').trim()
    description = ''

    circledMatches.forEach(function(match, idx) {
      var label = match.substring(1).replace(/[）)\s]+$/, '').trim()
      if (label) {
        options.push({ id: 'opt_' + (idx + 1), label: label })
      }
    })
  }

  // If no circled digits, try (1) (2) (3) patterns
  if (options.length === 0) {
    var parenPattern = /\((\d)\)\s*([^()\n]+)/g
    var parenMatch
    var parenOptions: ParsedOption[] = []
    while ((parenMatch = parenPattern.exec(text)) !== null) {
      parenOptions.push({ id: 'opt_' + parenMatch[1], label: parenMatch[2].trim() })
    }
    if (parenOptions.length >= 2) {
      var firstParenIdx = text.indexOf('(1)')
      if (firstParenIdx === -1) firstParenIdx = text.indexOf('(' + parenOptions[0].id.split('_')[1] + ')')
      if (firstParenIdx > 0) {
        title = text.substring(0, firstParenIdx).replace(/[：:、,\s]+$/, '').trim()
      }
      options = parenOptions
    }
  }

  // If still no embedded options, check for "・" bullets
  if (options.length === 0) {
    var bulletParts = text.split(/・/)
    if (bulletParts.length >= 3) {
      title = bulletParts[0].replace(/[：:、,\s]+$/, '').trim()
      bulletParts.slice(1).forEach(function(part, idx) {
        var label = part.trim()
        if (label) {
          options.push({ id: 'opt_' + (idx + 1), label: label })
        }
      })
    }
  }

  // If no embedded options found at all, split title/description on common delimiters
  if (options.length === 0) {
    var dashSplit = title.split(/[—–]/)
    if (dashSplit.length >= 2) {
      title = dashSplit[0].trim()
      description = dashSplit.slice(1).join('—').trim()
    } else {
      var periodSplit = title.split(/。/)
      if (periodSplit.length >= 2 && periodSplit[0].length < 60) {
        title = periodSplit[0].trim()
        description = periodSplit.slice(1).join('。').trim()
      }
    }
  }

  return { title: title, description: description, options: options }
}

// ---------------------------------------------------------------------------
// Default action options (when no embedded choices exist)
// ---------------------------------------------------------------------------

var DEFAULT_OPTIONS: ParsedOption[] = [
  { id: 'accept', label: 'このまま採用' },
  { id: 'custom', label: '指示を追加して採用' },
  { id: 'skip', label: 'スキップ' },
]

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ProposalCards(props: ProposalCardsProps) {
  var suggestions = props.suggestions
  var onDecisionsChange = props.onDecisionsChange
  var onApplyAll = props.onApplyAll

  var parsed = suggestions.map(function(s) { return parseSuggestion(s) })

  var initDecisions: ProposalDecision[] = suggestions.map(function(_, idx) {
    return {
      proposalIndex: idx,
      selectedOption: null,
      instruction: '',
      status: 'pending' as const,
    }
  })

  var [decisions, setDecisions] = useState<ProposalDecision[]>(initDecisions)
  var [expandedInstruction, setExpandedInstruction] = useState<number | null>(null)

  function updateDecision(idx: number, updates: Partial<ProposalDecision>) {
    setDecisions(function(prev) {
      var next = prev.map(function(d, i) {
        if (i !== idx) return d
        var merged = {
          proposalIndex: d.proposalIndex,
          selectedOption: updates.selectedOption !== undefined ? updates.selectedOption : d.selectedOption,
          instruction: updates.instruction !== undefined ? updates.instruction : d.instruction,
          status: updates.status !== undefined ? updates.status : d.status,
        }
        return merged
      })
      if (onDecisionsChange) onDecisionsChange(next)
      return next
    })
  }

  function handleSelectOption(proposalIdx: number, optionId: string) {
    var isCustom = optionId === 'custom'
    var isSkip = optionId === 'skip'
    updateDecision(proposalIdx, {
      selectedOption: optionId,
      status: isSkip ? 'skipped' : 'decided',
    })
    if (isCustom) {
      setExpandedInstruction(proposalIdx)
    }
  }

  function handleConfirmInstruction(proposalIdx: number) {
    updateDecision(proposalIdx, { status: 'decided' })
    setExpandedInstruction(null)
  }

  var decidedCount = decisions.filter(function(d) { return d.status !== 'pending' }).length
  var allDecided = decidedCount === decisions.length

  function handleApplyAll() {
    if (onApplyAll) onApplyAll(decisions)
  }

  if (!suggestions || suggestions.length === 0) return null

  return (
    <div className="space-y-4 mt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center">
            <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-gray-800">
            提案・改善ポイント
          </h3>
          <span className="text-xs text-gray-400">
            {decidedCount}/{suggestions.length} 決定済み
          </span>
        </div>
        {allDecided && onApplyAll && (
          <button
            onClick={handleApplyAll}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            すべて適用
          </button>
        )}
      </div>

      {/* Proposal Cards */}
      {parsed.map(function(proposal, idx) {
        var decision = decisions[idx]
        var hasEmbeddedOptions = proposal.options.length > 0
        var displayOptions = hasEmbeddedOptions ? proposal.options : DEFAULT_OPTIONS
        var isDecided = decision.status === 'decided'
        var isSkipped = decision.status === 'skipped'
        var showInstruction = expandedInstruction === idx
          || decision.selectedOption === 'custom'
          || (hasEmbeddedOptions && decision.selectedOption && decision.instruction)

        return (
          <div
            key={idx}
            className={'rounded-xl border-2 overflow-hidden transition-all ' + (
              isDecided
                ? 'border-emerald-200 bg-emerald-50/30'
                : isSkipped
                  ? 'border-gray-200 bg-gray-50/50 opacity-60'
                  : 'border-amber-200 bg-white'
            )}
          >
            {/* Card Header */}
            <div className="px-5 pt-4 pb-3">
              <div className="flex items-start gap-3">
                <div className={'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ' + (
                  isDecided
                    ? 'bg-emerald-500 text-white'
                    : isSkipped
                      ? 'bg-gray-300 text-white'
                      : 'bg-amber-500 text-white'
                )}>
                  {isDecided ? (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isSkipped ? '—' : String(idx + 1)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={'text-sm font-medium ' + (isSkipped ? 'text-gray-400 line-through' : 'text-gray-900')}>
                    {proposal.title}
                  </p>
                  {proposal.description && (
                    <p className="text-xs text-gray-500 mt-1">{proposal.description}</p>
                  )}
                </div>
                {/* Reset button for decided items */}
                {(isDecided || isSkipped) && (
                  <button
                    onClick={function() {
                      updateDecision(idx, { selectedOption: null, status: 'pending', instruction: '' })
                      setExpandedInstruction(null)
                    }}
                    className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
                  >
                    やり直す
                  </button>
                )}
              </div>
            </div>

            {/* Options Grid */}
            {!isSkipped && (
              <div className="px-5 pb-3">
                <p className="text-xs text-gray-400 mb-2">
                  {hasEmbeddedOptions ? '方向性を選択:' : 'アクション:'}
                </p>
                <div className={'grid gap-2 ' + (
                  displayOptions.length <= 3 ? 'grid-cols-' + displayOptions.length : 'grid-cols-2 sm:grid-cols-3'
                )}>
                  {displayOptions.map(function(opt) {
                    var isSelected = decision.selectedOption === opt.id
                    return (
                      <button
                        key={opt.id}
                        onClick={function() { handleSelectOption(idx, opt.id) }}
                        className={'relative rounded-lg border-2 px-3 py-2.5 text-left transition-all ' + (
                          isSelected
                            ? 'border-blue-500 bg-blue-50 shadow-sm'
                            : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/50'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <div className={'w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ' + (
                            isSelected ? 'border-blue-500' : 'border-gray-300'
                          )}>
                            {isSelected && (
                              <div className="w-2 h-2 rounded-full bg-blue-500" />
                            )}
                          </div>
                          <span className={'text-xs font-medium ' + (isSelected ? 'text-blue-700' : 'text-gray-700')}>
                            {opt.label}
                          </span>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Instruction Input */}
            {!isSkipped && (showInstruction || (hasEmbeddedOptions && decision.selectedOption)) && (
              <div className="px-5 pb-4">
                <label className="text-xs text-gray-500 block mb-1.5">
                  指示コメント（任意 — 追加の修正指示があれば入力）:
                </label>
                <div className="flex gap-2">
                  <textarea
                    value={decision.instruction}
                    onChange={function(e) { updateDecision(idx, { instruction: e.target.value }) }}
                    placeholder="例: 人件費の内訳は正社員・契約社員・業務委託の3区分で..."
                    rows={2}
                    className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  />
                  {expandedInstruction === idx && (
                    <button
                      onClick={function() { handleConfirmInstruction(idx) }}
                      className="self-end px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 transition-colors flex-shrink-0"
                    >
                      確定
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Decided Summary */}
            {isDecided && decision.selectedOption && (
              <div className="px-5 pb-4">
                <div className="flex items-center gap-2 text-xs text-emerald-700">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="font-medium">
                    選択: {(function() {
                      var found = displayOptions.filter(function(o) { return o.id === decision.selectedOption })[0]
                      return found ? found.label : decision.selectedOption
                    })()}
                  </span>
                  {decision.instruction && (
                    <span className="text-emerald-600">
                      + 指示あり
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      })}

      {/* Apply All Button (bottom) */}
      {suggestions.length > 1 && allDecided && onApplyAll && (
        <div className="flex justify-center pt-2">
          <button
            onClick={handleApplyAll}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 transition-all shadow-md hover:shadow-lg"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            選択を確定して次へ
          </button>
        </div>
      )}
    </div>
  )
}
