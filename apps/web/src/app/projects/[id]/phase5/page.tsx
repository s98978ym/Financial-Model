'use client'

import { useState, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { PLPreviewTable } from '@/components/pl/PLPreviewTable'
import { KPISummaryCards } from '@/components/pl/KPISummaryCards'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { usePhaseJob } from '@/lib/usePhaseJob'

export default function Phase5Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)
  const [viewMode, setViewMode] = useState<'pl' | 'flat'>('pl')

  const { result, isProcessing, isComplete, isFailed, trigger, progress, error, projectState } =
    usePhaseJob({ projectId, phase: 5 })

  const extractions = result?.extractions || result?.extracted_values || []
  const warnings = result?.warnings || []

  // Cross-reference Phase 4 assignments and Phase 3 sheet mappings
  const { assignments, sheetMappings } = useMemo(() => {
    const phase4Result = projectState?.phase_results?.[4]?.raw_json
    const phase3Result = projectState?.phase_results?.[3]?.raw_json
    return {
      assignments: phase4Result?.cell_assignments || [],
      sheetMappings: phase3Result?.sheet_mappings || [],
    }
  }, [projectState])

  const stats = useMemo(() => {
    const total = extractions.length
    const docSource = extractions.filter((e: any) => e.source === 'document').length
    const highConf = extractions.filter((e: any) => (e.confidence || 0) >= 0.8).length
    const lowConf = extractions.filter((e: any) => (e.confidence || 0) < 0.5).length
    return { total, docSource, highConf, lowConf }
  }, [extractions])

  return (
    <PhaseLayout
      phase={5}
      title="パラメータ抽出"
      subtitle="事業計画書から抽出した値を確認・編集し、PLモデルを完成させましょう"
      projectId={projectId}
    >
      {/* Trigger */}
      {!isProcessing && !isComplete && !isFailed && (
        <div className="text-center py-16 bg-gradient-to-b from-blue-50 to-white rounded-2xl border border-blue-100">
          <div className="text-4xl mb-4">📄</div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            パラメータ抽出を実行
          </h3>
          <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
            事業計画書から売上・コスト・前提条件の数値を自動抽出し、
            PLモデルに反映します。
          </p>
          <button
            onClick={() => trigger()}
            className="bg-blue-600 text-white px-8 py-3 rounded-xl hover:bg-blue-700 font-medium shadow-lg shadow-blue-200 transition-all hover:shadow-xl hover:shadow-blue-300"
          >
            抽出を開始する
          </button>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="text-center py-16">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-blue-100 rounded-full" />
            <div className="absolute inset-0 border-4 border-blue-600 rounded-full animate-spin border-t-transparent" />
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-blue-600">
              {progress}%
            </span>
          </div>
          <p className="text-gray-600 font-medium">パラメータを抽出中...</p>
          <p className="text-gray-400 text-sm mt-1">事業計画書を分析しています</p>
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-red-500 text-xl mt-0.5">!</span>
            <div>
              <p className="text-sm font-medium text-red-800">抽出に失敗しました</p>
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

      {/* Results */}
      {isComplete && extractions.length > 0 && (
        <>
          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
              <div className="flex items-start gap-2">
                <span className="text-amber-500">⚠</span>
                <div className="text-sm text-amber-700">
                  {warnings.map((w: string, i: number) => (
                    <p key={i}>{w}</p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* KPI Summary Cards */}
          <KPISummaryCards
            extractions={extractions}
            assignments={assignments}
            sheetMappings={sheetMappings}
          />

          {/* View Mode Toggle */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">抽出結果</h3>
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('pl')}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  viewMode === 'pl'
                    ? 'bg-white text-gray-800 shadow-sm font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                PL構造ビュー
              </button>
              <button
                onClick={() => setViewMode('flat')}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  viewMode === 'flat'
                    ? 'bg-white text-gray-800 shadow-sm font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                フラットビュー
              </button>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              {viewMode === 'pl' ? (
                <PLPreviewTable
                  items={extractions}
                  assignments={assignments}
                  sheetMappings={sheetMappings}
                  mode="extraction"
                  onRowClick={(item) => setSelectedCell(item)}
                  selectedItem={selectedCell}
                />
              ) : (
                <FlatExtractionTable
                  extractions={extractions}
                  onRowClick={(item) => setSelectedCell(item)}
                  selectedItem={selectedCell}
                />
              )}
            </div>

            {/* Evidence Panel */}
            <div className="w-80 flex-shrink-0 hidden lg:block">
              <div className="sticky top-4">
                <EvidencePanel cell={selectedCell} />
              </div>
            </div>
          </div>

          {/* Summary & Actions */}
          <div className="mt-8 bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-800">次のステップ</h3>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span className="inline-flex w-2 h-2 rounded-full bg-green-500" />
                {stats.highConf}/{stats.total} 高確信度
                <span className="mx-2">·</span>
                <span className="inline-flex w-2 h-2 rounded-full bg-blue-500" />
                {stats.docSource}/{stats.total} 文書由来
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {stats.lowConf > 0 && (
                <NextStepCard
                  icon="🔍"
                  title={`低確信度 ${stats.lowConf} 件を確認`}
                  description="推定値を文書の正確な数値に置き換えましょう"
                  priority="medium"
                />
              )}
              <NextStepCard
                icon="🎮"
                title="シナリオでPLを確認"
                description="パラメータを調整して損益の変化を体感"
                onClick={() => router.push(`/projects/${projectId}/scenarios`)}
              />
              <NextStepCard
                icon="📥"
                title="Excelエクスポート"
                description="完成したPLモデルをExcelで出力"
                onClick={() => router.push(`/projects/${projectId}/export`)}
              />
            </div>
          </div>
        </>
      )}

      {/* Empty results */}
      {isComplete && extractions.length === 0 && result && (
        <div className="text-center py-12 bg-gray-50 rounded-xl border border-gray-200">
          <div className="text-3xl mb-3">📭</div>
          <p className="text-gray-600 font-medium mb-2">抽出結果がありません</p>
          <p className="text-gray-400 text-sm mb-4">
            Phase 4 のモデル設計が正しく完了しているか確認してください
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

/**
 * Flat table view (alternative to PLPreviewTable).
 */
function FlatExtractionTable({
  extractions,
  onRowClick,
  selectedItem,
}: {
  extractions: any[]
  onRowClick?: (item: any) => void
  selectedItem?: any
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">シート</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">セル</th>
            <th className="text-right px-4 py-3 text-xs font-medium text-gray-500">値</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">原文</th>
            <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">ソース</th>
            <th className="text-right px-4 py-3 text-xs font-medium text-gray-500">確信度</th>
          </tr>
        </thead>
        <tbody>
          {extractions.map((ext: any, idx: number) => {
            const isSelected = selectedItem?.sheet === ext.sheet && selectedItem?.cell === ext.cell
            const pct = Math.round((ext.confidence || 0) * 100)
            const confColor = pct >= 80 ? 'text-green-700' : pct >= 50 ? 'text-yellow-700' : 'text-red-600'
            return (
              <tr
                key={`${ext.sheet}-${ext.cell}-${idx}`}
                onClick={() => onRowClick?.(ext)}
                className={`border-b border-gray-50 cursor-pointer transition-colors ${
                  isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-4 py-2.5 text-gray-700 whitespace-nowrap">{ext.sheet}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-gray-400">{ext.cell}</td>
                <td className="px-4 py-2.5 text-right font-mono font-semibold text-blue-700">
                  {typeof ext.value === 'number' ? ext.value.toLocaleString() : ext.value}
                </td>
                <td className="px-4 py-2.5 text-gray-500 truncate max-w-[200px]">{ext.original_text}</td>
                <td className="px-4 py-2.5 text-center">
                  <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    ext.source === 'document' ? 'bg-blue-100 text-blue-700' :
                    ext.source === 'inferred' ? 'bg-amber-100 text-amber-700' :
                    'bg-gray-100 text-gray-500'
                  }`}>
                    {ext.source === 'document' ? '文書' : ext.source === 'inferred' ? '推定' : '初期値'}
                  </span>
                </td>
                <td className={`px-4 py-2.5 text-right font-mono text-xs font-semibold ${confColor}`}>
                  {pct}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** Next step action card */
function NextStepCard({
  icon,
  title,
  description,
  onClick,
  priority,
}: {
  icon: string
  title: string
  description: string
  onClick?: () => void
  priority?: 'high' | 'medium'
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-xl border transition-all hover:shadow-md ${
        priority === 'medium'
          ? 'border-amber-200 bg-amber-50 hover:bg-amber-100'
          : 'border-gray-200 bg-white hover:bg-gray-50'
      }`}
    >
      <div className="text-xl mb-2">{icon}</div>
      <div className="text-sm font-medium text-gray-800">{title}</div>
      <div className="text-xs text-gray-500 mt-1">{description}</div>
    </button>
  )
}
