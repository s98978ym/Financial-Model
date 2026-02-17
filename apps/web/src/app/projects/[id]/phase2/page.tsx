'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { usePhaseJob } from '@/lib/usePhaseJob'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { api } from '@/lib/api'

export default function Phase2Page() {
  var params = useParams()
  var router = useRouter()
  var projectId = params.id as string
  var [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  var { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState, logMsg } =
    usePhaseJob({ projectId, phase: 2 })

  // Get document_id from project state
  var documentId = projectState?.documents?.[0]?.id || ''

  // Extract proposals from result
  var proposals = result?.proposals || []

  var [saveError, setSaveError] = useState<string | null>(null)

  // Save selected proposal index to DB then navigate
  var saveSelection = useMutation({
    mutationFn: function(idx: number) {
      return api.saveEdit({
        project_id: projectId,
        phase: 2,
        patch_json: { selected_proposal_index: idx },
      })
    },
    onSuccess: function() {
      router.push('/projects/' + projectId + '/phase3')
    },
    onError: function(err: Error) {
      console.error('[Phase2] saveSelection error:', err.message)
      setSaveError(err.message)
    },
  })

  function handleSelectAndProceed() {
    if (selectedIndex != null) {
      setSaveError(null)
      saveSelection.mutate(selectedIndex)
    }
  }

  function handleSkipAndProceed() {
    router.push('/projects/' + projectId + '/phase3')
  }

  return (
    <PhaseLayout
      phase={2}
      title="ビジネスモデル分析"
      subtitle="AIが提案する収益構造を選択してください"
      projectId={projectId}
    >
      {/* Trigger button (if not started) */}
      {!isProcessing && !isComplete && !isFailed && (
        <div className="text-center py-16 bg-white rounded-3xl shadow-warm">
          <div className="w-14 h-14 rounded-2xl bg-cream-200 flex items-center justify-center mx-auto mb-4 text-2xl">📊</div>
          <p className="text-sand-500 mb-5">Phase 2 分析を開始してください</p>
          {!projectState ? (
            <p className="text-sm text-sand-400">プロジェクト情報を読み込み中...</p>
          ) : (
            <button
              onClick={function() { trigger({ document_id: documentId }) }}
              className="bg-dark-900 text-white px-6 py-3 rounded-2xl hover:bg-dark-800 font-medium shadow-warm-md transition-all"
            >
              ビジネスモデル分析を実行
            </button>
          )}
          {projectState && !documentId && (
            <p className="text-sm text-amber-600 mt-3">
              ドキュメントが見つかりません。Phase 1でアップロードしてください。
            </p>
          )}
        </div>
      )}

      {/* Processing state */}
      {isProcessing && (
        <div className="text-center py-16">
          <div className="relative w-14 h-14 mx-auto mb-6">
            <div className="absolute inset-0 border-3 border-cream-300 rounded-full" />
            <div className="absolute inset-0 border-3 border-gold-500 rounded-full animate-spin border-t-transparent" />
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-gold-600">
              {progress}%
            </span>
          </div>
          <p className="text-dark-900 font-medium">ビジネスモデルを分析中...</p>
          <div className="w-64 mx-auto mt-3 h-1.5 bg-cream-300 rounded-full overflow-hidden">
            <div
              className="h-full bg-gold-500 rounded-full transition-all duration-500"
              style={{ width: progress + '%' }}
            />
          </div>
          <p className="text-xs text-sand-400 mt-2">
            {logMsg || (progress < 20
              ? 'ドキュメントを準備中...'
              : progress < 80
                ? 'LLMが事業計画書を分析中...'
                : '最終処理中です。もうしばらくお待ちください')}
          </p>
        </div>
      )}

      {/* Error state */}
      {isFailed && (
        <div className="bg-red-50 rounded-2xl p-5 mb-6">
          <p className="text-sm text-red-600">分析に失敗しました: {error}</p>
          <button
            onClick={function() { trigger({ document_id: documentId }) }}
            className="mt-3 text-sm text-red-500 hover:text-red-600 font-medium transition-colors"
          >
            再試行
          </button>
        </div>
      )}

      {/* Proposals */}
      {isComplete && proposals.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
          {proposals.map(function(proposal: any, idx: number) {
            return (
              <button
                key={proposal.label || idx}
                onClick={function() { setSelectedIndex(idx) }}
                className={'text-left p-6 rounded-3xl transition-all ' + (
                  selectedIndex === idx
                    ? 'bg-white ring-2 ring-gold-400 shadow-warm-md'
                    : 'bg-white shadow-warm hover:shadow-warm-md'
                )}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-dark-900">{proposal.label}</h3>
                  <span className={'text-xs font-medium px-2.5 py-1 rounded-full ' + (
                    (proposal.confidence || 0) >= 0.8 ? 'bg-emerald-50 text-emerald-700' :
                    (proposal.confidence || 0) >= 0.5 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-600'
                  )}>
                    {Math.round((proposal.confidence || 0) * 100)}%
                  </span>
                </div>
                <p className="text-sm text-sand-500 mb-3">{proposal.executive_summary || proposal.description || ''}</p>
                <div className="flex flex-wrap gap-1.5">
                  {(proposal.segments || []).map(function(seg: any) {
                    var segName = typeof seg === 'string' ? seg : seg.name
                    return (
                      <span
                        key={segName}
                        className="text-xs bg-cream-200 text-sand-600 px-2 py-0.5 rounded-full"
                      >
                        {segName}
                      </span>
                    )
                  })}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Completed but raw JSON view */}
      {isComplete && proposals.length === 0 && result && (
        <div className="bg-white rounded-3xl shadow-warm p-5">
          <p className="text-sm text-sand-500 mb-2">分析結果（生データ）</p>
          <pre className="text-xs bg-cream-100 p-4 rounded-2xl max-h-64 overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      {/* Selected proposal → confirmation + next phase */}
      {selectedIndex != null && proposals[selectedIndex] && (
        <div className="mt-6 p-5 bg-white rounded-3xl shadow-warm">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-dark-900 font-semibold">
              シナリオ確定: <strong>{proposals[selectedIndex].label}</strong>
            </p>
            {(proposals[selectedIndex].confidence || 0) < 0.5 && (
              <span className="text-xs bg-amber-50 text-amber-600 px-2.5 py-1 rounded-full">
                信頼度が低いため、結果の確認を推奨します
              </span>
            )}
          </div>
          {proposals[selectedIndex].executive_summary && (
            <p className="text-xs text-sand-500 mb-3">{proposals[selectedIndex].executive_summary}</p>
          )}
          {(proposals[selectedIndex].segments || []).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {proposals[selectedIndex].segments.map(function(seg: any) {
                var segName = typeof seg === 'string' ? seg : seg.name
                return (
                  <span key={segName} className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">
                    {segName}
                  </span>
                )
              })}
            </div>
          )}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={function() { setSelectedIndex(null) }}
              className="text-sm text-sand-500 hover:text-dark-900 transition-colors"
            >
              選択を変更
            </button>
            <button
              onClick={handleSelectAndProceed}
              disabled={saveSelection.isPending}
              className="bg-dark-900 text-white px-5 py-2.5 rounded-2xl hover:bg-dark-800 text-sm font-medium disabled:opacity-50 shadow-warm-sm transition-all"
            >
              {saveSelection.isPending ? '保存中...' : 'このシナリオで確定 → Phase 3'}
            </button>
          </div>
          {saveError && (
            <div className="mt-3 flex items-center justify-between bg-red-50 rounded-2xl p-3">
              <p className="text-xs text-red-500">保存に失敗しました: {saveError}</p>
              <button
                onClick={handleSkipAndProceed}
                className="text-xs text-gold-600 hover:text-gold-500 ml-3 whitespace-nowrap font-medium"
              >
                保存をスキップして進む
              </button>
            </div>
          )}
        </div>
      )}
    </PhaseLayout>
  )
}
