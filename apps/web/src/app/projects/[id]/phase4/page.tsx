'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ParameterGrid } from '@/components/grid/ParameterGrid'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { CompletionChecklist } from '@/components/progress/CompletionChecklist'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { usePhaseJob } from '@/lib/usePhaseJob'

export default function Phase4Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)

  const { result, isProcessing, isComplete, isFailed, trigger, progress, error } =
    usePhaseJob({ projectId, phase: 4 })

  const assignments = result?.cell_assignments || result?.assignments || []
  const unmapped = result?.unmapped_cells || []

  const stats = {
    total: assignments.length + unmapped.length,
    mapped: assignments.length,
    highConf: assignments.filter((a: any) => (a.confidence || 0) >= 0.8).length,
    midConf: assignments.filter((a: any) => (a.confidence || 0) >= 0.5 && (a.confidence || 0) < 0.8).length,
    lowConf: assignments.filter((a: any) => (a.confidence || 0) < 0.5).length,
    docSource: assignments.filter((a: any) => !(a.warnings?.length)).length,
  }

  return (
    <PhaseLayout
      phase={4}
      title="モデル設計"
      subtitle="セルとビジネスコンセプトのマッピング"
      projectId={projectId}
    >
      {/* Trigger */}
      {!isProcessing && !isComplete && !isFailed && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500 mb-4">Phase 4 モデル設計を開始してください</p>
          <button
            onClick={() => trigger()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            モデル設計を実行
          </button>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
          <p className="text-gray-600">モデルを設計中... ({progress}%)</p>
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">設計に失敗しました: {error}</p>
          <button onClick={() => trigger()} className="mt-2 text-sm text-red-600 hover:underline">再試行</button>
        </div>
      )}

      {/* Results */}
      {isComplete && assignments.length > 0 && (
        <>
          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              <ParameterGrid
                data={assignments}
                columns={[
                  { field: 'sheet', headerName: 'シート', width: 120 },
                  { field: 'cell', headerName: 'セル', width: 70 },
                  { field: 'label_match', headerName: 'ラベル', width: 120 },
                  { field: 'concept', headerName: 'コンセプト', width: 150, editable: true },
                  { field: 'category', headerName: 'カテゴリ', width: 100 },
                  { field: 'segment', headerName: 'セグメント', width: 130 },
                  { field: 'period', headerName: '期間', width: 70 },
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
                unmapped.length > 0 ? `未マッピング ${unmapped.length} セルを確認` : null,
                stats.lowConf > 0 ? `低確信度 ${stats.lowConf} セルのエビデンスを補完` : null,
                'Phase 5 (パラメータ抽出) へ進む',
              ].filter(Boolean) as string[]}
            />
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => router.push(`/projects/${projectId}/phase5`)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
            >
              Phase 5 へ進む
            </button>
          </div>
        </>
      )}

      {/* Raw JSON fallback */}
      {isComplete && assignments.length === 0 && result && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500 mb-2">設計結果（生データ）</p>
          <pre className="text-xs bg-white p-4 rounded max-h-64 overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </PhaseLayout>
  )
}
