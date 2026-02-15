'use client'

import { useMemo, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { usePhaseJob } from '@/lib/usePhaseJob'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { api } from '@/lib/api'
import ProposalCards from '@/components/proposals/ProposalCards'
import { RevenueModelConfigurator } from '@/components/revenue'
import type { SegmentRevenueModel } from '@/components/revenue'

export default function Phase3Page() {
  var params = useParams()
  var router = useRouter()
  var projectId = params.id as string

  var { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState } =
    usePhaseJob({ projectId, phase: 3 })

  var [proposalDecisions, setProposalDecisions] = useState<any[]>([])
  var [saveError, setSaveError] = useState<string | null>(null)
  var [revenueModels, setRevenueModels] = useState<SegmentRevenueModel[]>([])
  var [savingRevenue, setSavingRevenue] = useState(false)

  // Load Phase 2 edits to get user's selected proposal index
  var phase2Edits = useQuery({
    queryKey: ['edits', projectId, 2],
    queryFn: function() { return api.getEdits(projectId, 2) },
    enabled: !!projectId,
    retry: 1,
  })

  // Load Phase 3 edits (to restore revenue model configs)
  var phase3Edits = useQuery({
    queryKey: ['edits', projectId, 3],
    queryFn: function() { return api.getEdits(projectId, 3) },
    enabled: !!projectId,
    retry: 1,
  })

  // Restore revenue model configs from saved edits
  useMemo(function() {
    if (!phase3Edits.data) return
    var edits = phase3Edits.data || []
    for (var i = edits.length - 1; i >= 0; i--) {
      if (edits[i].patch_json && edits[i].patch_json.revenue_model_configs) {
        setRevenueModels(edits[i].patch_json.revenue_model_configs)
        break
      }
    }
  }, [phase3Edits.data])

  // Get the correct selected proposal from Phase 2 (respect user selection)
  var phase2Proposal = useMemo(function() {
    var phase2Result = projectState?.phase_results?.[2]?.raw_json
    if (!phase2Result) return null
    var proposals = phase2Result.proposals || []
    if (!proposals.length) return null

    var edits = phase2Edits.data || []
    var selectedIdx = 0
    for (var i = edits.length - 1; i >= 0; i--) {
      if (edits[i].patch_json && edits[i].patch_json.selected_proposal_index != null) {
        selectedIdx = edits[i].patch_json.selected_proposal_index
        break
      }
    }
    return proposals[selectedIdx] || proposals[0] || null
  }, [projectState, phase2Edits.data])

  // Extract segments from the selected Phase 2 proposal (including drivers for auto-suggestion)
  var segments = useMemo(function() {
    if (!phase2Proposal) return []
    return (phase2Proposal.segments || []).map(function(seg: any) {
      return {
        name: seg.name || '',
        model_type: seg.model_type || '',
        revenue_formula: seg.revenue_formula || '',
        revenue_drivers: seg.revenue_drivers || [],
        key_assumptions: seg.key_assumptions || [],
      }
    })
  }, [phase2Proposal])

  var mappings = result?.sheet_mappings || result?.mappings || []

  var purposeLabels: Record<string, string> = {
    revenue_model: '収益モデル',
    pl_summary: 'PL集計',
    assumptions: '前提条件',
    cost_detail: 'コスト詳細',
    headcount: '人員計画',
    capex: '設備投資',
  }

  // Save revenue model configs
  function handleSaveRevenueModels() {
    setSavingRevenue(true)
    setSaveError(null)
    api.saveEdit({
      project_id: projectId,
      phase: 3,
      patch_json: { revenue_model_configs: revenueModels },
    }).then(function() {
      setSavingRevenue(false)
    }).catch(function(err: Error) {
      console.error('[Phase3] save revenue models error:', err.message)
      setSaveError(err.message)
      setSavingRevenue(false)
    })
  }

  // Save Phase 3 decisions to DB then navigate to Phase 4
  var saveDecisions = useMutation({
    mutationFn: function(decisions: any[]) {
      return api.saveEdit({
        project_id: projectId,
        phase: 3,
        patch_json: {
          proposal_decisions: decisions,
          adopted: decisions.filter(function(d: any) { return d.status === 'decided' && d.selectedOption !== 'skip' }),
          skipped: decisions.filter(function(d: any) { return d.status === 'skipped' || d.selectedOption === 'skip' }),
        },
      })
    },
    onSuccess: function() {
      router.push('/projects/' + projectId + '/phase4')
    },
    onError: function(err: Error) {
      console.error('[Phase3] saveDecisions error:', err.message)
      setSaveError(err.message)
    },
  })

  var handleApplyDecisions = useCallback(function(decisions: any[]) {
    setSaveError(null)
    setProposalDecisions(decisions)
    saveDecisions.mutate(decisions)
  }, [saveDecisions])

  // Navigate to Phase 4, saving revenue models first if configured
  function handleProceedToPhase4() {
    var hasConfigs = revenueModels.some(function(m) { return m.archetype != null })
    if (hasConfigs) {
      setSavingRevenue(true)
      api.saveEdit({
        project_id: projectId,
        phase: 3,
        patch_json: { revenue_model_configs: revenueModels },
      }).then(function() {
        setSavingRevenue(false)
        router.push('/projects/' + projectId + '/phase4')
      }).catch(function() {
        setSavingRevenue(false)
        router.push('/projects/' + projectId + '/phase4')
      })
    } else {
      router.push('/projects/' + projectId + '/phase4')
    }
  }

  return (
    <PhaseLayout
      phase={3}
      title="テンプレート構造マッピング"
      subtitle="シートとビジネスセグメントの対応関係"
      projectId={projectId}
    >
      {/* Trigger button */}
      {!isProcessing && !isComplete && !isFailed && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500 mb-4">Phase 3 マッピングを開始してください</p>
          <button
            onClick={function() { trigger({ selected_proposal: phase2Proposal || {} }) }}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 active:bg-blue-800"
          >
            テンプレートマッピングを実行
          </button>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
          <p className="text-gray-600">テンプレートをマッピング中... ({progress}%)</p>
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">マッピングに失敗しました: {error}</p>
          <button
            onClick={function() { trigger({ selected_proposal: phase2Proposal || {} }) }}
            className="mt-2 text-sm text-red-600 hover:underline"
          >
            再試行
          </button>
        </div>
      )}

      {/* Result table + Revenue Model Configurator */}
      {isComplete && mappings.length > 0 && (
        <>
          {result?.overall_structure && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-blue-700 mb-1">テンプレート概要</p>
                  <p className="text-sm text-blue-800">{result.overall_structure}</p>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-500 font-medium">シート名</th>
                  <th className="text-left px-4 py-3 text-gray-500 font-medium">目的</th>
                  <th className="text-left px-4 py-3 text-gray-500 font-medium">対応セグメント</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">確信度</th>
                </tr>
              </thead>
              <tbody>
                {mappings.map(function(m: any, idx: number) {
                  return (
                    <tr key={m.sheet || idx} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{m.sheet || m.sheet_name}</td>
                      <td className="px-4 py-3">
                        <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded">
                          {purposeLabels[m.sheet_purpose] || purposeLabels[m.purpose] || m.sheet_purpose || m.purpose || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{m.mapped_segment || m.segment || '—'}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={'text-xs font-medium px-2 py-0.5 rounded ' + (
                          (m.confidence || 0) >= 0.8 ? 'bg-green-100 text-green-700' :
                          (m.confidence || 0) >= 0.5 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                        )}>
                          {Math.round((m.confidence || 0) * 100)}%
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* ═══ REVENUE MODEL CONFIGURATOR ═══ */}
          {segments.length > 0 && (
            <div className="mb-6">
              <RevenueModelConfigurator
                segments={segments}
                value={revenueModels}
                onChange={function(models) {
                  setRevenueModels(models)
                }}
              />
              {/* Auto-save indicator */}
              {revenueModels.some(function(m) { return m.archetype != null }) && (
                <div className="mt-3 flex items-center justify-end gap-3">
                  <button
                    onClick={handleSaveRevenueModels}
                    disabled={savingRevenue}
                    className="text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                  >
                    {savingRevenue ? '保存中...' : '設定を保存'}
                  </button>
                </div>
              )}
            </div>
          )}

          {result?.suggestions && result.suggestions.length > 0 && (
            <ProposalCards
              suggestions={result.suggestions}
              onDecisionsChange={setProposalDecisions}
              onApplyAll={handleApplyDecisions}
            />
          )}

          {/* Phase 4 navigation */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleProceedToPhase4}
              disabled={savingRevenue || saveDecisions.isPending}
              className="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
            >
              {savingRevenue ? '保存中...' : 'Phase 4 へ進む'}
            </button>
          </div>

          {saveError && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
              <p className="text-xs text-red-600">保存に失敗しました: {saveError}</p>
              <button
                onClick={function() { router.push('/projects/' + projectId + '/phase4') }}
                className="text-xs text-blue-600 hover:underline ml-3 whitespace-nowrap"
              >
                保存をスキップして進む
              </button>
            </div>
          )}

          {saveDecisions.isPending && (
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-500">提案を保存中...</p>
            </div>
          )}
        </>
      )}

      {isComplete && mappings.length === 0 && result && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600 mb-3">
            シートマッピングが生成されませんでした。
          </p>
          <div className="flex gap-3">
            <button onClick={function() { trigger({ selected_proposal: phase2Proposal || {} }) }} className="text-sm text-blue-600 hover:underline">再試行</button>
            <button
              onClick={function() { router.push('/projects/' + projectId + '/phase4') }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
            >
              Phase 4 へ進む
            </button>
          </div>
        </div>
      )}
    </PhaseLayout>
  )
}
