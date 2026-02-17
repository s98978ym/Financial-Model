'use client'

/**
 * Revenue Model Configurator — per-segment archetype selector + config panels.
 *
 * Progressive disclosure: collapsed = archetype badge + key metric,
 * expanded = full configuration panel for the selected archetype.
 */

import { useState, useCallback, useMemo } from 'react'
import type { ArchetypeId, SegmentRevenueModel, ArchetypeConfig } from './types'
import { ARCHETYPES, getArchetypeMeta, getDefaultConfig } from './defaults'
import type { ArchetypeCategory } from './types'
import { suggestArchetype } from './suggest'
import { UnitEconomicsPanel } from './UnitEconomicsPanel'
import { ConsultingPanel } from './ConsultingPanel'
import { AcademyPanel } from './AcademyPanel'
import { SubscriptionPanel } from './SubscriptionPanel'
import { MarketplacePanel } from './MarketplacePanel'
import { UsagePanel } from './UsagePanel'
import { AdvertisingPanel } from './AdvertisingPanel'
import { LicensingPanel } from './LicensingPanel'
import { StaffingPanel } from './StaffingPanel'
import { RentalPanel } from './RentalPanel'
import { FranchisePanel } from './FranchisePanel'

interface SegmentInput {
  name: string
  model_type?: string
  revenue_formula?: string
  revenue_drivers?: Array<{ name: string; unit?: string; description?: string }>
  key_assumptions?: string[]
}

interface Props {
  /** Segments from Phase 2 BM analysis */
  segments: SegmentInput[]
  /** Current configs (loaded from edits) */
  value: SegmentRevenueModel[]
  onChange: (models: SegmentRevenueModel[]) => void
}

export function RevenueModelConfigurator({ segments, value, onChange }: Props) {
  var [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  // Compute suggestions for each segment
  var suggestions = useMemo(function() {
    return segments.map(function(seg) { return suggestArchetype(seg) })
  }, [segments])

  // Ensure we have a model entry for each segment
  var models: SegmentRevenueModel[] = segments.map(function(seg, i) {
    var existing = value.find(function(v) { return v.segment_name === seg.name })
    return existing || { segment_name: seg.name, archetype: null, config: null }
  })

  function updateModel(idx: number, patch: Partial<SegmentRevenueModel>) {
    var next = models.map(function(m, i) {
      return i === idx ? { ...m, ...patch } : m
    })
    onChange(next)
  }

  function handleSelectArchetype(idx: number, archetypeId: ArchetypeId) {
    var current = models[idx]
    if (current.archetype === archetypeId) return
    updateModel(idx, {
      archetype: archetypeId,
      config: getDefaultConfig(archetypeId),
    })
    setExpandedIdx(idx)
  }

  function handleConfigChange(idx: number, config: ArchetypeConfig) {
    updateModel(idx, { config: config })
  }

  function toggleExpand(idx: number) {
    setExpandedIdx(expandedIdx === idx ? null : idx)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-5 h-5 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-3 h-3 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-dark-900">売上構成ロジック設定</h3>
          <p className="text-[10px] text-sand-500">各セグメントの売上ドライバーを詳細に設計</p>
        </div>
      </div>

      {models.map(function(model, idx) {
        var seg = segments[idx]
        var isExpanded = expandedIdx === idx
        var meta = model.archetype ? getArchetypeMeta(model.archetype) : null
        var suggestion = suggestions[idx]
        var suggestedMeta = suggestion ? getArchetypeMeta(suggestion.archetype) : null

        return (
          <div key={seg.name} className="bg-white rounded-xl border border-cream-200 overflow-hidden">
            {/* --- Segment header --- */}
            <button
              onClick={function() { toggleExpand(idx) }}
              className="w-full px-4 py-3 flex items-center gap-3 hover:bg-cream-50 transition-colors"
            >
              <div className="flex-1 min-w-0 text-left">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-dark-900">{seg.name}</span>
                  {seg.model_type && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-cream-100 text-sand-500">{seg.model_type}</span>
                  )}
                </div>
                {seg.revenue_formula && (
                  <p className="text-[10px] text-sand-400 mt-0.5 truncate">{seg.revenue_formula}</p>
                )}
              </div>
              {meta && (
                <div className={'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium ' + meta.color + '/10 ' + meta.textColor}>
                  <span className={'w-4 h-4 rounded text-[10px] font-bold flex items-center justify-center text-white ' + meta.color}>
                    {meta.icon}
                  </span>
                  {meta.label}
                </div>
              )}
              {!meta && suggestedMeta && (
                <div className="flex items-center gap-1 text-xs text-sand-400">
                  <span className={'w-3.5 h-3.5 rounded text-[9px] font-bold flex items-center justify-center text-white opacity-60 ' + suggestedMeta.color}>
                    {suggestedMeta.icon}
                  </span>
                  <span className="opacity-60">{suggestedMeta.label}</span>
                  <span className="text-[9px] text-sand-300">推奨</span>
                </div>
              )}
              {!meta && !suggestedMeta && (
                <span className="text-xs text-sand-400">モデル未選択</span>
              )}
              <svg
                className={'w-4 h-4 text-sand-400 transition-transform ' + (isExpanded ? 'rotate-180' : '')}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* --- Expanded content --- */}
            {isExpanded && (
              <div className="border-t border-cream-200">
                {/* Archetype selector — grouped by MECE category */}
                <div className="px-4 py-3 bg-cream-50 border-b border-cream-200">
                  <div className="text-[10px] font-medium text-sand-500 mb-2">売上モデルを選択</div>
                  {(['取引型', '継続型', '仲介型', '権利・教育型'] as ArchetypeCategory[]).map(function(cat) {
                    var catArchetypes = ARCHETYPES.filter(function(a) { return a.category === cat })
                    if (catArchetypes.length === 0) return null
                    return (
                      <div key={cat} className="mb-2 last:mb-0">
                        <div className="text-[9px] text-sand-400 font-medium mb-1">{cat}</div>
                        <div className="flex gap-1.5 flex-wrap">
                          {catArchetypes.map(function(arch) {
                            var isSelected = model.archetype === arch.id
                            return (
                              <button
                                key={arch.id}
                                onClick={function(e) { e.stopPropagation(); handleSelectArchetype(idx, arch.id) }}
                                className={'flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-[11px] transition-all '
                                  + (isSelected
                                    ? arch.color + ' text-white border-transparent shadow-warm'
                                    : 'bg-white border-cream-200 text-sand-600 hover:border-cream-300'
                                  )}
                              >
                                <span className={'w-4 h-4 rounded text-[10px] font-bold flex items-center justify-center '
                                  + (isSelected ? 'bg-white/30 text-white' : arch.color + ' text-white')}>
                                  {arch.icon}
                                </span>
                                {arch.label}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                  {model.archetype && meta && (
                    <p className="text-[10px] text-sand-400 mt-2">{meta.description}</p>
                  )}
                </div>

                {/* Archetype-specific config panel */}
                {model.archetype && model.config && (
                  <div className="px-4 py-4">
                    {model.archetype === 'unit_economics' && (
                      <UnitEconomicsPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'consulting' && (
                      <ConsultingPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'academy' && (
                      <AcademyPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'subscription' && (
                      <SubscriptionPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'marketplace' && (
                      <MarketplacePanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'usage' && (
                      <UsagePanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'advertising' && (
                      <AdvertisingPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'licensing' && (
                      <LicensingPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'staffing' && (
                      <StaffingPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'rental' && (
                      <RentalPanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                    {model.archetype === 'franchise' && (
                      <FranchisePanel
                        config={model.config as any}
                        onChange={function(c) { handleConfigChange(idx, c) }}
                      />
                    )}
                  </div>
                )}

                {/* No archetype selected — show suggestion or placeholder */}
                {!model.archetype && (
                  <div className="px-4 py-6 text-center">
                    {suggestion && suggestedMeta ? (
                      <div>
                        <p className="text-xs text-sand-400 mb-2">Phase 2 の分析結果に基づく推奨モデル:</p>
                        <button
                          onClick={function() { handleSelectArchetype(idx, suggestion!.archetype) }}
                          className={'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white shadow-warm transition-all hover:shadow-warm-md ' + suggestedMeta.color}
                        >
                          <span className="w-5 h-5 rounded bg-white/30 text-[11px] font-bold flex items-center justify-center">
                            {suggestedMeta.icon}
                          </span>
                          {suggestedMeta.label}を適用
                        </button>
                        <p className="text-[10px] text-sand-400 mt-1.5">{suggestedMeta.description}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-sand-400">上のボタンから売上モデルを選択してください</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
