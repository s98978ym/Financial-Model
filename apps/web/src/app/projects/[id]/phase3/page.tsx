'use client'

import { useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { usePhaseJob } from '@/lib/usePhaseJob'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function Phase3Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string

  const { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState } =
    usePhaseJob({ projectId, phase: 3 })

  // Load Phase 2 proposals from project state for proper data flow
  const phase2Proposal = useMemo(() => {
    const phase2Result = projectState?.phase_results?.[2]?.raw_json
    if (!phase2Result) return null
    const proposals = phase2Result.proposals || []
    return proposals[0] || null
  }, [projectState])

  const mappings = result?.sheet_mappings || result?.mappings || []

  const purposeLabels: Record<string, string> = {
    revenue_model: '収益モデル',
    pl_summary: 'PL集計',
    assumptions: '前提条件',
    cost_detail: 'コスト詳細',
    headcount: '人員計画',
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
            onClick={() => trigger({ selected_proposal: phase2Proposal || {} })}
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
            onClick={() => trigger({ selected_proposal: phase2Proposal || {} })}
            className="mt-2 text-sm text-red-600 hover:underline"
          >
            再試行
          </button>
        </div>
      )}

      {/* Result table */}
      {isComplete && mappings.length > 0 && (
        <>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
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
                {mappings.map((m: any, idx: number) => (
                  <tr key={m.sheet || idx} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{m.sheet || m.sheet_name}</td>
                    <td className="px-4 py-3">
                      <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded">
                        {purposeLabels[m.sheet_purpose] || purposeLabels[m.purpose] || m.sheet_purpose || m.purpose || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{m.mapped_segment || m.segment || '—'}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                        (m.confidence || 0) >= 0.8 ? 'bg-green-100 text-green-700' :
                        (m.confidence || 0) >= 0.5 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {Math.round((m.confidence || 0) * 100)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={() => router.push(`/projects/${projectId}/phase4`)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
            >
              Phase 4 へ進む
            </button>
          </div>
        </>
      )}

      {/* Overall structure description */}
      {isComplete && result?.overall_structure && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-blue-800">{result.overall_structure}</p>
        </div>
      )}

      {/* Suggestions */}
      {isComplete && result?.suggestions?.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <p className="text-sm font-medium text-amber-800 mb-2">提案</p>
          <ul className="text-sm text-amber-700 space-y-1 list-disc list-inside">
            {result.suggestions.map((s: string, idx: number) => (
              <li key={idx}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty result fallback */}
      {isComplete && mappings.length === 0 && result && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600 mb-3">
            シートマッピングが生成されませんでした。以下をご確認ください:
          </p>
          <ul className="text-sm text-gray-500 space-y-1 list-disc list-inside mb-4">
            <li>Phase 1 でテンプレートのシート構造が正しく読み取られているか</li>
            <li>Phase 2 で事業セグメントが正しく分析されているか</li>
          </ul>
          <div className="flex gap-3">
            <button onClick={() => trigger({ selected_proposal: phase2Proposal || {} })} className="text-sm text-blue-600 hover:underline">再試行</button>
            <button
              onClick={() => router.push(`/projects/${projectId}/phase4`)}
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
