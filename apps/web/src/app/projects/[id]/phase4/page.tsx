'use client'

import { useState, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { PLPreviewTable } from '@/components/pl/PLPreviewTable'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { usePhaseJob } from '@/lib/usePhaseJob'

export default function Phase4Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)

  const { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState } =
    usePhaseJob({ projectId, phase: 4 })

  const assignments = result?.cell_assignments || result?.assignments || []
  const unmapped = result?.unmapped_cells || []
  const warnings = result?.warnings || []
  const hasEstimated = assignments.some((a: any) => a.derivation === 'estimated')

  // Load Phase 3 sheet mappings for enrichment
  const sheetMappings = useMemo(() => {
    const phase3Result = projectState?.phase_results?.[3]?.raw_json
    return phase3Result?.sheet_mappings || []
  }, [projectState])

  const stats = useMemo(() => {
    const total = assignments.length + unmapped.length
    const highConf = assignments.filter((a: any) => (a.confidence || 0) >= 0.8).length
    const lowConf = assignments.filter((a: any) => (a.confidence || 0) < 0.5).length
    const catObj: Record<string, boolean> = {}
    assignments.forEach(function(a: any) { if (a.category) catObj[a.category] = true })
    return { total, mapped: assignments.length, highConf, lowConf, categories: Object.keys(catObj).length }
  }, [assignments, unmapped])

  return (
    <PhaseLayout
      phase={4}
      title="モデル設計"
      subtitle="テンプレートの各セルにビジネスコンセプトを割り当て、PLの骨格を構築します"
      projectId={projectId}
    >
      {/* Trigger */}
      {!isProcessing && !isComplete && !isFailed && (
        <div className="text-center py-16 bg-gradient-to-b from-indigo-50 to-white rounded-2xl border border-indigo-100">
          <div className="text-4xl mb-4">🏗️</div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            モデル設計を実行
          </h3>
          <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
            テンプレートの各入力セルが「何を表すか」を自動判定します。
            売上・コスト・前提条件の概念マッピングを構築します。
          </p>
          <button
            onClick={() => trigger()}
            className="bg-blue-600 text-white px-8 py-3 rounded-xl hover:bg-blue-700 font-medium shadow-lg shadow-blue-200 transition-all hover:shadow-xl hover:shadow-blue-300"
          >
            設計を開始する
          </button>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="text-center py-16">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-indigo-100 rounded-full" />
            <div className="absolute inset-0 border-4 border-indigo-600 rounded-full animate-spin border-t-transparent" />
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-indigo-600">
              {progress}%
            </span>
          </div>
          <p className="text-gray-600 font-medium">モデルを設計中...</p>
          <p className="text-gray-400 text-sm mt-1">セルとビジネスコンセプトを照合しています</p>
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-red-500 text-xl mt-0.5">!</span>
            <div>
              <p className="text-sm font-medium text-red-800">設計に失敗しました</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
              <button
                onClick={() => trigger()}
                className="mt-3 text-sm bg-red-100 text-red-700 px-4 py-1.5 rounded-lg hover:bg-red-200 transition-colors"
              >
                再試行
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Warnings banner */}
      {isComplete && warnings.length > 0 && (
        <div className={`rounded-xl border p-4 mb-6 ${hasEstimated ? 'bg-amber-50 border-amber-200' : 'bg-blue-50 border-blue-200'}`}>
          <div className="flex items-start gap-2">
            <span className={hasEstimated ? 'text-amber-500' : 'text-blue-500'}>
              {hasEstimated ? '⚠' : 'ℹ'}
            </span>
            <div>
              <p className={`text-sm font-medium mb-1 ${hasEstimated ? 'text-amber-800' : 'text-blue-800'}`}>
                {hasEstimated ? '推定モード — 事業分析から自動生成' : '注意事項'}
              </p>
              <ul className="text-sm space-y-0.5">
                {warnings.map((w: string, idx: number) => (
                  <li key={idx} className={hasEstimated ? 'text-amber-700' : 'text-blue-700'}>{w}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {isComplete && assignments.length > 0 && (
        <>
          {/* Stats Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <StatCard
              label="マッピング済み"
              value={`${stats.mapped}`}
              sub={`/ ${stats.total} 項目`}
              color="blue"
            />
            <StatCard
              label="カテゴリ数"
              value={`${stats.categories}`}
              sub="PL区分"
              color="indigo"
            />
            <StatCard
              label="高確信度"
              value={`${stats.highConf}`}
              sub="80%以上"
              color="green"
            />
            <StatCard
              label="要確認"
              value={`${stats.lowConf + unmapped.length}`}
              sub="低確信度 + 未割当"
              color={stats.lowConf + unmapped.length > 0 ? 'amber' : 'green'}
            />
          </div>

          {/* PL Structure View */}
          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              <PLPreviewTable
                items={assignments}
                sheetMappings={sheetMappings}
                mode="assignment"
                onRowClick={(item) => setSelectedCell(item)}
                selectedItem={selectedCell}
              />
            </div>

            {/* Evidence Panel */}
            <div className="w-80 flex-shrink-0 hidden lg:block">
              <div className="sticky top-4">
                <EvidencePanel cell={selectedCell} />
              </div>
            </div>
          </div>

          {/* Unmapped Items */}
          {unmapped.length > 0 && (
            <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
              <h4 className="text-sm font-medium text-yellow-800 mb-2">
                未マッピング {unmapped.length} セル
              </h4>
              <div className="flex flex-wrap gap-2">
                {unmapped.map((u: any, i: number) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2.5 py-1 bg-yellow-100 text-yellow-700 rounded-lg text-xs"
                  >
                    {u.sheet}/{u.cell}
                    {u.label && <span className="ml-1 text-yellow-600">({u.label})</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={() => router.push(`/projects/${projectId}/phase5`)}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-xl hover:bg-blue-700 text-sm font-medium shadow-lg shadow-blue-200 transition-all hover:shadow-xl"
            >
              Phase 5 パラメータ抽出へ進む
            </button>
          </div>
        </>
      )}

      {/* Empty results */}
      {isComplete && assignments.length === 0 && result && (
        <div className="text-center py-12 bg-gray-50 rounded-xl border border-gray-200">
          <div className="text-3xl mb-3">📭</div>
          <p className="text-gray-600 font-medium mb-2">
            マッピング対象のセルが見つかりませんでした
          </p>
          <p className="text-gray-400 text-sm mb-4 max-w-md mx-auto">
            テンプレートExcelの入力セルが正しくハイライトされているか、
            Phase 1/2 が正しく完了しているかご確認ください。
          </p>
          <button
            onClick={() => trigger()}
            className="text-sm bg-blue-50 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-100"
          >
            再試行
          </button>
        </div>
      )}
    </PhaseLayout>
  )
}

function StatCard({
  label,
  value,
  sub,
  color,
}: {
  label: string
  value: string
  sub: string
  color: 'blue' | 'indigo' | 'green' | 'amber'
}) {
  const colors = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  }
  return (
    <div className={`rounded-xl border p-3 ${colors[color]}`}>
      <div className="text-xs font-medium text-gray-500 mb-1">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-bold">{value}</span>
        <span className="text-xs text-gray-400">{sub}</span>
      </div>
    </div>
  )
}
