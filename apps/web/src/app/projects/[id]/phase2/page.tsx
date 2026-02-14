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

  var { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState } =
    usePhaseJob({ projectId, phase: 2 })

  // Get document_id from project state
  var documentId = projectState?.documents?.[0]?.id || ''

  // Extract proposals from result
  var proposals = result?.proposals || []

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
  })

  function handleSelectAndProceed() {
    if (selectedIndex != null) {
      saveSelection.mutate(selectedIndex)
    }
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
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500 mb-4">Phase 2 分析を開始してください</p>
          {!projectState ? (
            <p className="text-sm text-gray-400">プロジェクト情報を読み込み中...</p>
          ) : (
            <button
              onClick={function() { trigger({ document_id: documentId }) }}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
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
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
          <p className="text-gray-600">ビジネスモデルを分析中... ({progress}%)</p>
          <p className="text-xs text-gray-400 mt-1">LLMが事業計画書を読み解いています</p>
        </div>
      )}

      {/* Error state */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">分析に失敗しました: {error}</p>
          <button
            onClick={function() { trigger({ document_id: documentId }) }}
            className="mt-2 text-sm text-red-600 hover:underline"
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
                className={'text-left p-5 rounded-lg border-2 transition-all ' + (
                  selectedIndex === idx
                    ? 'border-blue-500 bg-blue-50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">{proposal.label}</h3>
                  <span className={'text-xs font-medium px-2 py-0.5 rounded ' + (
                    (proposal.confidence || 0) >= 0.8 ? 'bg-green-100 text-green-700' :
                    (proposal.confidence || 0) >= 0.5 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                  )}>
                    {Math.round((proposal.confidence || 0) * 100)}%
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-3">{proposal.executive_summary || proposal.description || ''}</p>
                <div className="flex flex-wrap gap-1">
                  {(proposal.segments || []).map(function(seg: any) {
                    var segName = typeof seg === 'string' ? seg : seg.name
                    return (
                      <span
                        key={segName}
                        className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
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
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500 mb-2">分析結果（生データ）</p>
          <pre className="text-xs bg-white p-4 rounded max-h-64 overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      {/* Selected proposal → next phase */}
      {selectedIndex != null && (
        <div className="mt-6 flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700">
            <strong>{proposals[selectedIndex]?.label}</strong> を選択しました。
          </p>
          <button
            onClick={handleSelectAndProceed}
            disabled={saveSelection.isPending}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
          >
            {saveSelection.isPending ? '保存中...' : 'Phase 3 へ進む'}
          </button>
        </div>
      )}
    </PhaseLayout>
  )
}
