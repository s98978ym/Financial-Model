'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ParameterGrid } from '@/components/grid/ParameterGrid'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { CompletionChecklist } from '@/components/progress/CompletionChecklist'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { usePhaseJob } from '@/lib/usePhaseJob'

export default function Phase5Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)

  const { result, isProcessing, isComplete, isFailed, trigger, progress, error } =
    usePhaseJob({ projectId, phase: 5 })

  const extractions = result?.extractions || result?.extracted_values || []

  const stats = {
    total: extractions.length,
    mapped: extractions.length,
    highConf: extractions.filter((e: any) => (e.confidence || 0) >= 0.8).length,
    midConf: extractions.filter((e: any) => (e.confidence || 0) >= 0.5 && (e.confidence || 0) < 0.8).length,
    lowConf: extractions.filter((e: any) => (e.confidence || 0) < 0.5).length,
    docSource: extractions.filter((e: any) => e.source === 'document').length,
  }

  return (
    <PhaseLayout
      phase={5}
      title="パラメータ抽出"
      subtitle="文書から抽出した値の確認・編集"
      projectId={projectId}
    >
      {/* Trigger */}
      {!isProcessing && !isComplete && !isFailed && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500 mb-4">Phase 5 パラメータ抽出を開始してください</p>
          <button
            onClick={() => trigger()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            パラメータ抽出を実行
          </button>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
          <p className="text-gray-600">パラメータを抽出中... ({progress}%)</p>
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">抽出に失敗しました: {error}</p>
          <button onClick={() => trigger()} className="mt-2 text-sm text-red-600 hover:underline">再試行</button>
        </div>
      )}

      {/* Results */}
      {isComplete && extractions.length > 0 && (
        <>
          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              <ParameterGrid
                data={extractions}
                columns={[
                  { field: 'sheet', headerName: 'シート', width: 120 },
                  { field: 'cell', headerName: 'セル', width: 70 },
                  { field: 'value', headerName: '値', width: 120, editable: true },
                  { field: 'original_text', headerName: '原文', width: 150 },
                  { field: 'source', headerName: 'ソース', width: 90, type: 'source' },
                  { field: 'confidence', headerName: '確信度', width: 90, type: 'confidence' },
                ]}
                onCellClick={(cell: any) => setSelectedCell(cell)}
              />
            </div>
            <div className="w-80 flex-shrink-0">
              <EvidencePanel cell={selectedCell} />
            </div>
          </div>

          <div className="mt-6">
            <CompletionChecklist
              stats={stats}
              nextActions={[
                stats.lowConf > 0 ? `低確信度 ${stats.lowConf} セルの値を確認` : null,
                'シナリオ プレイグラウンドでPLを確認',
                'Excel エクスポート',
              ].filter(Boolean) as string[]}
            />
          </div>

          <div className="mt-4 flex justify-end gap-3">
            <button
              onClick={() => router.push(`/projects/${projectId}/scenarios`)}
              className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 text-sm"
            >
              シナリオ プレイグラウンド
            </button>
            <button
              onClick={() => router.push(`/projects/${projectId}/export`)}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 text-sm"
            >
              Excel エクスポート
            </button>
          </div>
        </>
      )}

      {/* Raw JSON fallback */}
      {isComplete && extractions.length === 0 && result && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500 mb-2">抽出結果（生データ）</p>
          <pre className="text-xs bg-white p-4 rounded max-h-64 overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </PhaseLayout>
  )
}
