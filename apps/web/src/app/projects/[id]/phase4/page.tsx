'use client'

import { useState, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { PLPreviewTable } from '@/components/pl/PLPreviewTable'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { MobileEvidenceSheet } from '@/components/grid/MobileEvidenceSheet'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { usePhaseJob } from '@/lib/usePhaseJob'

export default function Phase4Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)
  const [showEstimationConfirm, setShowEstimationConfirm] = useState(false)

  const { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState } =
    usePhaseJob({ projectId, phase: 4 })

  const assignments = result?.cell_assignments || []
  const unmapped = result?.unmapped_cells || []
  const warnings = result?.warnings || []
  const hasEstimated = assignments.some((a: any) => a.derivation === 'estimated')

  // Phase 3 prerequisite status
  const phase3Result = projectState?.phase_results?.[3]
  const phase3Exists = !!phase3Result
  const phase3Empty = phase3Exists && !(phase3Result.raw_json?.sheet_mappings?.length)

  // Load Phase 3 sheet mappings for enrichment
  const sheetMappings = useMemo(() => {
    const phase3Raw = projectState?.phase_results?.[3]?.raw_json
    return phase3Raw?.sheet_mappings || []
  }, [projectState])

  // Handle trigger with Phase 3 prerequisite check
  const handleTrigger = () => {
    if (!phase3Exists) return // Should not happen since button is hidden
    if (phase3Empty) {
      setShowEstimationConfirm(true)
      return
    }
    trigger()
  }

  const handleEstimationConfirm = () => {
    setShowEstimationConfirm(false)
    trigger({ allow_estimation: true })
  }

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
      {/* Phase 3 not completed — block trigger */}
      {!isProcessing && !isComplete && !isFailed && !phase3Exists && projectState && (
        <div className="text-center py-16 bg-white rounded-3xl shadow-warm">
          <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4 text-2xl">⛔</div>
          <h3 className="text-lg font-semibold text-dark-900 mb-2">
            Phase 3を先に完了してください
          </h3>
          <p className="text-sand-500 text-sm mb-6 max-w-md mx-auto">
            モデル設計にはPhase 3（テンプレートマッピング）の結果が必要です。
          </p>
          <button
            onClick={() => router.push(`/projects/${projectId}/phase3`)}
            className="bg-dark-900 text-white px-6 py-3 rounded-2xl hover:bg-dark-800 font-medium shadow-warm-md transition-all"
          >
            Phase 3へ移動する
          </button>
        </div>
      )}

      {/* Estimation confirmation dialog */}
      {showEstimationConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-warm-lg p-6 max-w-md mx-4">
            <div className="text-center mb-4">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 flex items-center justify-center mx-auto mb-3 text-2xl">⚠️</div>
              <h3 className="text-lg font-semibold text-dark-900">推定モードで続行しますか？</h3>
            </div>
            <p className="text-sm text-sand-500 mb-4">
              Phase 3は完了しましたが、テンプレートのシートマッピングが空です。
              推定モードではLLMを使って事業分析結果からPL概念マッピングを自動生成します。
            </p>
            <div className="bg-cream-100 rounded-2xl p-3 mb-5">
              <ul className="text-xs text-sand-600 space-y-1">
                <li>・セル位置は仮配置になります</li>
                <li>・テンプレートの実際の構造と異なる場合があります</li>
                <li>・生成後に手動で調整が必要な場合があります</li>
              </ul>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowEstimationConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-2xl bg-cream-200 text-dark-900 hover:bg-cream-300 text-sm font-medium transition-all"
              >
                キャンセル
              </button>
              <button
                onClick={handleEstimationConfirm}
                className="flex-1 px-4 py-2.5 rounded-2xl bg-dark-900 text-white hover:bg-dark-800 text-sm font-medium shadow-warm-md transition-all"
              >
                推定モードで続行
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trigger — Phase 3 exists */}
      {!isProcessing && !isComplete && !isFailed && phase3Exists && (
        <div className="text-center py-16 bg-white rounded-3xl shadow-warm">
          <div className="w-14 h-14 rounded-2xl bg-cream-200 flex items-center justify-center mx-auto mb-4 text-2xl">🏗️</div>
          <h3 className="text-lg font-semibold text-dark-900 mb-2">
            モデル設計を実行
          </h3>
          <p className="text-sand-500 text-sm mb-6 max-w-md mx-auto">
            テンプレートの各入力セルが「何を表すか」を自動判定します。
            売上・コスト・前提条件の概念マッピングを構築します。
          </p>
          {phase3Empty && (
            <div className="bg-cream-100 rounded-2xl p-3 mb-4 max-w-md mx-auto">
              <p className="text-xs text-sand-500">
                Phase 3のシートマッピングが空です。推定モードで実行されます。
              </p>
            </div>
          )}
          <button
            onClick={handleTrigger}
            className="bg-dark-900 text-white px-8 py-3 rounded-2xl hover:bg-dark-800 font-medium shadow-warm-md transition-all"
          >
            設計を開始する
          </button>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="text-center py-16">
          <div className="relative w-14 h-14 mx-auto mb-6">
            <div className="absolute inset-0 border-3 border-cream-300 rounded-full" />
            <div className="absolute inset-0 border-3 border-gold-500 rounded-full animate-spin border-t-transparent" />
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-gold-600">
              {progress}%
            </span>
          </div>
          <p className="text-dark-900 font-medium">モデルを設計中...</p>
          <p className="text-sand-400 text-sm mt-1">セルとビジネスコンセプトを照合しています</p>
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div className="bg-red-50 rounded-2xl p-5 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-red-500 text-xl mt-0.5">!</span>
            <div>
              <p className="text-sm font-medium text-red-600">設計に失敗しました</p>
              <p className="text-sm text-red-500 mt-1">{error}</p>
              <div className="flex gap-2 mt-3">
                {error && error.indexOf('Phase 3') >= 0 ? (
                  <button
                    onClick={() => router.push(`/projects/${projectId}/phase3`)}
                    className="text-sm bg-red-100 text-red-600 px-4 py-1.5 rounded-xl hover:bg-red-200 transition-colors"
                  >
                    Phase 3へ移動する
                  </button>
                ) : (
                  <button
                    onClick={() => trigger()}
                    className="text-sm bg-red-100 text-red-600 px-4 py-1.5 rounded-xl hover:bg-red-200 transition-colors"
                  >
                    再試行
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Warnings banner */}
      {isComplete && warnings.length > 0 && (
        <div className="bg-white rounded-3xl shadow-warm p-5 mb-5">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-cream-200 flex items-center justify-center flex-shrink-0">
              <span className="text-gold-500">{hasEstimated ? '⚠' : 'ℹ'}</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-dark-900 mb-1">
                {hasEstimated ? '推定モード — 事業分析から自動生成' : '注意事項'}
              </p>
              <ul className="text-sm space-y-0.5">
                {warnings.map((w: string, idx: number) => (
                  <li key={idx} className="text-sand-500">{w}</li>
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
            <div className="bg-white rounded-3xl shadow-warm p-4">
              <div className="text-xs font-medium text-sand-400 mb-1">マッピング済み</div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold text-dark-900">{stats.mapped}</span>
                <span className="text-xs text-sand-400">/ {stats.total} 項目</span>
              </div>
            </div>
            <div className="bg-white rounded-3xl shadow-warm p-4">
              <div className="text-xs font-medium text-sand-400 mb-1">カテゴリ数</div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold text-dark-900">{stats.categories}</span>
                <span className="text-xs text-sand-400">PL区分</span>
              </div>
            </div>
            <div className="bg-white rounded-3xl shadow-warm p-4">
              <div className="text-xs font-medium text-sand-400 mb-1">高確信度</div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold text-dark-900">{stats.highConf}</span>
                <span className="text-xs text-sand-400">80%以上</span>
              </div>
            </div>
            <div className="bg-white rounded-3xl shadow-warm p-4">
              <div className="text-xs font-medium text-sand-400 mb-1">要確認</div>
              <div className="flex items-baseline gap-1">
                <span className={'text-xl font-bold ' + ((stats.lowConf + unmapped.length) > 0 ? 'text-amber-600' : 'text-dark-900')}>{stats.lowConf + unmapped.length}</span>
                <span className="text-xs text-sand-400">低確信度 + 未割当</span>
              </div>
            </div>
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

            {/* Evidence Panel - Desktop */}
            <div className="w-80 flex-shrink-0 hidden lg:block">
              <div className="sticky top-4">
                <EvidencePanel cell={selectedCell} />
              </div>
            </div>
          </div>

          {/* Evidence Panel - Mobile Bottom Sheet */}
          <MobileEvidenceSheet
            cell={selectedCell}
            onClose={() => setSelectedCell(null)}
          />

          {/* Unmapped Items */}
          {unmapped.length > 0 && (
            <div className="mt-6 bg-white rounded-3xl shadow-warm p-5">
              <h4 className="text-sm font-semibold text-dark-900 mb-3">
                未マッピング {unmapped.length} セル
              </h4>
              <div className="flex flex-wrap gap-2">
                {unmapped.map((u: any, i: number) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2.5 py-1 bg-cream-200 text-sand-600 rounded-full text-xs"
                  >
                    {u.sheet}/{u.cell}
                    {u.label && <span className="ml-1 text-sand-400">({u.label})</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={() => router.push(`/projects/${projectId}/phase5`)}
              className="bg-dark-900 text-white px-6 py-3 rounded-2xl hover:bg-dark-800 text-sm font-medium shadow-warm-md transition-all"
            >
              Phase 5 パラメータ抽出へ進む
            </button>
          </div>
        </>
      )}

      {/* Empty results */}
      {isComplete && assignments.length === 0 && result && (
        <div className="text-center py-12 bg-white rounded-3xl shadow-warm">
          <div className="w-12 h-12 rounded-2xl bg-cream-200 flex items-center justify-center mx-auto mb-3 text-xl">📭</div>
          <p className="text-dark-900 font-medium mb-2">
            マッピング対象のセルが見つかりませんでした
          </p>
          <p className="text-sand-400 text-sm mb-4 max-w-md mx-auto">
            テンプレートExcelの入力セルが正しくハイライトされているか、
            Phase 1/2 が正しく完了しているかご確認ください。
          </p>
          <button
            onClick={() => trigger()}
            className="text-sm bg-cream-200 text-gold-600 px-4 py-2.5 rounded-xl hover:bg-cream-300 font-medium transition-colors"
          >
            再試行
          </button>
        </div>
      )}
    </PhaseLayout>
  )
}
