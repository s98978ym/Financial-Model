'use client'

import { useState } from 'react'

interface ProposalItem {
  key: string
  label: string
  currentValue: number
  proposedValue: number
  accepted: boolean
}

export interface ParameterProposalData {
  source: string        // e.g., 'Phase 5 検出', '自然言語入力', 'AI提案'
  sourceDetail?: string  // e.g., the NL input text
  changes: Record<string, number>
}

interface ParameterProposalProps {
  proposal: ParameterProposalData
  currentParams: Record<string, number>
  onAccept: (accepted: Record<string, number>) => void
  onReject: () => void
}

var PARAM_LABELS: Record<string, string> = {
  revenue_fy1: '初年度売上',
  growth_rate: '売上成長率',
  cogs_rate: '売上原価率',
  opex_base: '初年度OPEX',
  opex_growth: 'OPEX増加率',
  capex: '年間CAPEX',
  depreciation: '年間償却費',
  depreciation_mode: '償却モード',
  useful_life: '耐用年数',
  existing_depreciation: '既存資産償却',
  target_breakeven_fy: '単年黒字目標',
  target_cum_breakeven_fy: '累積黒字目標',
}

function getParamLabel(key: string): string {
  if (PARAM_LABELS[key]) return PARAM_LABELS[key]
  // Payroll role params
  if (key.startsWith('pr_') && key.endsWith('_salary')) {
    var role = key.replace('pr_', '').replace('_salary', '')
    return role + ' 年収'
  }
  if (key.startsWith('pr_') && key.endsWith('_hc')) {
    var role2 = key.replace('pr_', '').replace('_hc', '')
    return role2 + ' 人数'
  }
  // SGA category params
  if (key.startsWith('sga_')) {
    var cat = key.replace('sga_', '').replace('_ratio', '')
    var labels: Record<string, string> = { payroll: '人件費', marketing: 'マーケ費', office: 'オフィス', system: 'システム', other: 'その他' }
    return (labels[cat] || cat) + (key.includes('ratio') ? '比率' : '')
  }
  // Segment params
  if (key.startsWith('seg_')) return 'セグメント: ' + key.replace('seg_', '')
  return key
}

function formatValue(key: string, value: number): string {
  if (key.includes('rate') || key.includes('growth') || key.includes('ratio') || key.includes('margin')) {
    return (value * 100).toFixed(1) + '%'
  }
  if (key === 'depreciation_mode') return value === 1 ? '自動' : '手動'
  if (key === 'useful_life' || key === 'target_breakeven_fy' || key === 'target_cum_breakeven_fy') {
    return value + '年'
  }
  if (key.endsWith('_hc')) return value + '人'
  // Yen values
  if (Math.abs(value) >= 100_000_000) return (value / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(value) >= 10_000) return (value / 10_000).toFixed(0) + '万円'
  return value.toLocaleString() + '円'
}

function ChangeArrow() {
  return (
    <svg className="w-3 h-3 text-gray-400 mx-1 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
    </svg>
  )
}

export function ParameterProposal({ proposal, currentParams, onAccept, onReject }: ParameterProposalProps) {
  var initialItems: ProposalItem[] = Object.keys(proposal.changes).map(function(key) {
    return {
      key: key,
      label: getParamLabel(key),
      currentValue: currentParams[key] ?? 0,
      proposedValue: proposal.changes[key],
      accepted: true,
    }
  })

  var [items, setItems] = useState(initialItems)

  function toggleItem(index: number) {
    var updated = items.map(function(item, i) {
      if (i === index) return Object.assign({}, item, { accepted: !item.accepted })
      return item
    })
    setItems(updated)
  }

  function toggleAll(val: boolean) {
    setItems(items.map(function(item) { return Object.assign({}, item, { accepted: val }) }))
  }

  function handleAccept() {
    var accepted: Record<string, number> = {}
    items.forEach(function(item) {
      if (item.accepted) {
        accepted[item.key] = item.proposedValue
      }
    })
    if (Object.keys(accepted).length > 0) {
      onAccept(accepted)
    } else {
      onReject()
    }
  }

  var acceptedCount = items.filter(function(it) { return it.accepted }).length
  var allAccepted = acceptedCount === items.length
  var noneAccepted = acceptedCount === 0

  // Source icon
  var sourceIcon = '💡'
  if (proposal.source.includes('Phase')) sourceIcon = '📄'
  else if (proposal.source.includes('自然言語') || proposal.source.includes('NL')) sourceIcon = '💬'

  return (
    <div className="bg-white rounded-lg border-2 border-blue-300 shadow-lg overflow-hidden animate-in slide-in-from-top-2 duration-300">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">{sourceIcon}</span>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">パラメーター提案</h3>
              <p className="text-[11px] text-gray-500">{proposal.source}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-gray-400">{acceptedCount}/{items.length}件選択</span>
          </div>
        </div>
        {proposal.sourceDetail && (
          <div className="mt-1.5 text-[11px] text-indigo-600 bg-indigo-50 rounded px-2 py-1 border border-indigo-100">
            {proposal.sourceDetail}
          </div>
        )}
      </div>

      {/* Parameter change list */}
      <div className="px-4 py-2 max-h-60 overflow-y-auto">
        {/* Select all / none */}
        <div className="flex items-center gap-2 pb-1.5 mb-1 border-b border-gray-100">
          <button
            onClick={function() { toggleAll(!allAccepted) }}
            className="text-[10px] text-blue-600 hover:text-blue-800"
          >
            {allAccepted ? '全て解除' : '全て選択'}
          </button>
        </div>

        {items.map(function(item, i) {
          var changed = item.currentValue !== item.proposedValue
          var increased = item.proposedValue > item.currentValue
          return (
            <button
              key={item.key}
              onClick={function() { toggleItem(i) }}
              className={'w-full flex items-center gap-2 py-2 px-1 rounded transition-all text-left ' +
                (item.accepted
                  ? 'bg-blue-50/50 hover:bg-blue-50'
                  : 'opacity-50 hover:opacity-70'
                ) +
                (i < items.length - 1 ? ' border-b border-gray-50' : '')
              }
            >
              {/* Checkbox */}
              <div className={'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors ' +
                (item.accepted ? 'bg-blue-500 border-blue-500' : 'border-gray-300 bg-white')}>
                {item.accepted && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>

              {/* Label */}
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-medium text-gray-700 truncate">{item.label}</div>
              </div>

              {/* Current → Proposed */}
              <div className="flex items-center flex-shrink-0">
                <span className="text-[11px] font-mono text-gray-400">
                  {formatValue(item.key, item.currentValue)}
                </span>
                {changed && (
                  <>
                    <ChangeArrow />
                    <span className={'text-[11px] font-mono font-semibold ' +
                      (increased ? 'text-green-600' : 'text-red-500')}>
                      {formatValue(item.key, item.proposedValue)}
                    </span>
                  </>
                )}
                {!changed && (
                  <span className="text-[10px] text-gray-400 ml-2">変更なし</span>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* Action buttons */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <button
          onClick={onReject}
          className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded border border-gray-300 hover:bg-white transition-colors"
        >
          却下
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAccept}
            disabled={noneAccepted}
            className={'text-xs font-semibold px-4 py-1.5 rounded transition-colors ' +
              (noneAccepted
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
              )
            }
          >
            {allAccepted ? '全て適用' : acceptedCount + '件を適用'}
          </button>
        </div>
      </div>
    </div>
  )
}
