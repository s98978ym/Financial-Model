'use client'

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { PLPreviewTable } from '@/components/pl/PLPreviewTable'
import { KPISummaryCards } from '@/components/pl/KPISummaryCards'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { MobileEvidenceSheet } from '@/components/grid/MobileEvidenceSheet'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { usePhaseJob } from '@/lib/usePhaseJob'
import { api } from '@/lib/api'

export default function Phase5Page() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)
  const [viewMode, setViewMode] = useState<'pl' | 'flat'>('pl')
  const [lowConfFilter, setLowConfFilter] = useState(false)
  const [reviewMode, setReviewMode] = useState(false)
  const [reviewEdits, setReviewEdits] = useState<Record<string, { value: number | string; reason: string }>>({})
  const [approvedItems, setApprovedItems] = useState<Set<string>>(new Set())
  const [savingEdits, setSavingEdits] = useState(false)

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

  const displayedExtractions = useMemo(() => {
    if (!lowConfFilter) return extractions
    return extractions.filter((e: any) => (e.confidence || 0) < 0.5)
  }, [extractions, lowConfFilter])

  const lowConfItems = useMemo(() => {
    return extractions.filter((e: any) => (e.confidence || 0) < 0.5)
  }, [extractions])

  const getItemKey = useCallback((item: any) => {
    return `${item.sheet || ''}::${item.cell || ''}::${item.period || ''}`
  }, [])

  // 影響サマリー: 推定値が売上全体に占める割合
  const impactSummary = useMemo(() => {
    var totalValue = 0
    var lowConfValue = 0
    extractions.forEach(function(e: any) {
      var v = typeof e.value === 'number' ? Math.abs(e.value) : 0
      totalValue += v
      if ((e.confidence || 0) < 0.5) lowConfValue += v
    })
    var pct = totalValue > 0 ? Math.round((lowConfValue / totalValue) * 100) : 0
    return { totalValue: totalValue, lowConfValue: lowConfValue, pct: pct }
  }, [extractions])

  const reviewedCount = useMemo(() => {
    return approvedItems.size + Object.keys(reviewEdits).length
  }, [approvedItems, reviewEdits])

  const handleApproveItem = useCallback(function(item: any) {
    var key = getItemKey(item)
    setApprovedItems(function(prev) {
      var next = new Set(prev)
      next.add(key)
      return next
    })
    // Remove from edits if previously edited
    setReviewEdits(function(prev) {
      var next = { ...prev }
      delete next[key]
      return next
    })
  }, [getItemKey])

  const handleEditItem = useCallback(function(item: any, value: number | string, reason: string) {
    var key = getItemKey(item)
    setReviewEdits(function(prev) {
      return { ...prev, [key]: { value: value, reason: reason } }
    })
    // Remove from approved if previously approved
    setApprovedItems(function(prev) {
      var next = new Set(prev)
      next.delete(key)
      return next
    })
  }, [getItemKey])

  const handleApproveAll = useCallback(function() {
    lowConfItems.forEach(function(item: any) {
      var key = getItemKey(item)
      if (!reviewEdits[key]) {
        setApprovedItems(function(prev) {
          var next = new Set(prev)
          next.add(key)
          return next
        })
      }
    })
  }, [lowConfItems, getItemKey, reviewEdits])

  const handleSaveReviewEdits = useCallback(async function() {
    setSavingEdits(true)
    try {
      var valueOverrides: any[] = []
      Object.entries(reviewEdits).forEach(function([key, edit]) {
        var parts = key.split('::')
        valueOverrides.push({
          sheet: parts[0],
          cell: parts[1],
          period: parts[2],
          new_value: edit.value,
          reason: edit.reason,
          source: 'user',
          confidence: 1.0,
        })
      })
      var approvedKeys: string[] = []
      approvedItems.forEach(function(key) { approvedKeys.push(key) })

      await api.saveEdit({
        project_id: projectId,
        phase: 5,
        patch_json: {
          type: 'low_confidence_review',
          value_overrides: valueOverrides,
          approved_as_is: approvedKeys,
          reviewed_at: new Date().toISOString(),
        },
      })
      setReviewMode(false)
      setLowConfFilter(false)
      setViewMode('pl')
    } catch (err: any) {
      alert('保存に失敗しました: ' + (err.message || err))
    } finally {
      setSavingEdits(false)
    }
  }, [reviewEdits, approvedItems, projectId])

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
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-semibold text-gray-700">抽出結果</h3>
              {lowConfFilter && (
                <button
                  onClick={() => { setLowConfFilter(false); setViewMode('pl') }}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 hover:bg-amber-200 transition-colors"
                >
                  低確信度のみ表示中
                  <span className="ml-0.5">✕</span>
                </button>
              )}
            </div>
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              <button
                onClick={() => { setViewMode('pl'); setLowConfFilter(false) }}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  viewMode === 'pl'
                    ? 'bg-white text-gray-800 shadow-sm font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                年次ビュー（1〜5年目）
              </button>
              <button
                onClick={() => { setViewMode('flat'); setLowConfFilter(false) }}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  viewMode === 'flat' && !lowConfFilter
                    ? 'bg-white text-gray-800 shadow-sm font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                セル一覧
              </button>
            </div>
          </div>

          {/* Low Confidence Review Mode */}
          {reviewMode && lowConfItems.length > 0 ? (
            <LowConfidenceReview
              items={lowConfItems}
              impactSummary={impactSummary}
              reviewEdits={reviewEdits}
              approvedItems={approvedItems}
              reviewedCount={reviewedCount}
              savingEdits={savingEdits}
              getItemKey={getItemKey}
              onEditItem={handleEditItem}
              onApproveItem={handleApproveItem}
              onApproveAll={handleApproveAll}
              onSave={handleSaveReviewEdits}
              onCancel={() => {
                setReviewMode(false)
                setLowConfFilter(false)
                setViewMode('pl')
              }}
            />
          ) : (
            <>
              {/* Content Area */}
              <div className="flex gap-6">
                <div className="flex-1 min-w-0">
                  {viewMode === 'pl' && !lowConfFilter ? (
                    <PLPreviewTable
                      items={displayedExtractions}
                      assignments={assignments}
                      sheetMappings={sheetMappings}
                      mode="extraction"
                      onRowClick={(item) => setSelectedCell(item)}
                      selectedItem={selectedCell}
                    />
                  ) : (
                    <FlatExtractionTable
                      extractions={displayedExtractions}
                      onRowClick={(item) => setSelectedCell(item)}
                      selectedItem={selectedCell}
                    />
                  )}
                </div>

                {/* Evidence Panel - Desktop */}
                <div className="w-80 flex-shrink-0 hidden lg:block">
                  <div className="sticky top-4">
                    <EvidencePanel cell={selectedCell} />
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Evidence Panel - Mobile Bottom Sheet */}
          <MobileEvidenceSheet
            cell={selectedCell}
            onClose={() => setSelectedCell(null)}
          />

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
                  description="推定値の修正・承認を行いましょう"
                  priority="medium"
                  onClick={() => {
                    setReviewMode(true)
                    setLowConfFilter(true)
                    setViewMode('flat')
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
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

/** Hook to detect mobile viewport */
function useIsMobile(breakpoint: number = 768) {
  var [isMobile, setIsMobile] = useState(false)
  useEffect(function() {
    function check() { setIsMobile(window.innerWidth < breakpoint) }
    check()
    window.addEventListener('resize', check)
    return function() { window.removeEventListener('resize', check) }
  }, [breakpoint])
  return isMobile
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
  var isMobile = useIsMobile()
  var [searchQuery, setSearchQuery] = useState('')
  var [sourceFilter, setSourceFilter] = useState<string>('all')

  function getPeriodLabel(ext: any): string {
    // From period field
    if (ext.period) {
      const m = ext.period.match(/FY(\d+)/i)
      if (m) return m[1] + '年目'
    }
    // From cell column
    const col = (ext.cell || '').replace(/\d/g, '').toUpperCase()
    const map: Record<string, string> = { C: '1年目', D: '2年目', E: '3年目', F: '4年目', G: '5年目' }
    return map[col] || '—'
  }

  var filteredExtractions = useMemo(function() {
    return extractions.filter(function(ext: any) {
      // Source filter
      if (sourceFilter !== 'all' && ext.source !== sourceFilter) return false
      // Search filter
      if (searchQuery) {
        var q = searchQuery.toLowerCase()
        var label = (ext.label || ext.original_text || '').toLowerCase()
        var sheet = (ext.sheet || '').toLowerCase()
        if (!label.includes(q) && !sheet.includes(q)) return false
      }
      return true
    })
  }, [extractions, sourceFilter, searchQuery])

  // Mobile: card list view
  if (isMobile) {
    return (
      <div className="space-y-3">
        {/* Search & Filter */}
        <div className="space-y-2">
          <input
            type="text"
            value={searchQuery}
            onChange={function(e) { setSearchQuery(e.target.value) }}
            placeholder="ラベルで検索..."
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {[
              { key: 'all', label: '全て' },
              { key: 'document', label: '文書' },
              { key: 'inferred', label: '推定' },
              { key: 'default', label: '初期値' },
            ].map(function(f) {
              return (
                <button
                  key={f.key}
                  onClick={function() { setSourceFilter(f.key) }}
                  className={'flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors min-h-[32px] ' + (
                    sourceFilter === f.key
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                >
                  {f.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Card list */}
        <div className="space-y-2">
          {filteredExtractions.map(function(ext: any, idx: number) {
            var isSelected = selectedItem?.sheet === ext.sheet && selectedItem?.cell === ext.cell
            var pct = Math.round((ext.confidence || 0) * 100)
            var confColor = pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-yellow-600' : 'text-red-600'
            var confBg = pct >= 80 ? 'bg-green-100' : pct >= 50 ? 'bg-yellow-100' : 'bg-red-100'
            var periodLabel = getPeriodLabel(ext)

            return (
              <div
                key={ext.sheet + '-' + ext.cell + '-' + idx}
                onClick={function() { onRowClick?.(ext) }}
                className={
                  'rounded-lg border p-3 cursor-pointer active:scale-[0.98] transition-all ' +
                  (isSelected ? 'ring-2 ring-blue-400 border-blue-200 bg-blue-50/50' : 'border-gray-200 bg-white hover:bg-gray-50')
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-gray-800 truncate">
                      {ext.label || ext.original_text || '—'}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-gray-400">
                      <span className="font-mono">{ext.sheet}/{ext.cell}</span>
                      <span className={'inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-semibold ' + (
                        periodLabel === '—' ? 'bg-gray-100 text-gray-400' : 'bg-indigo-100 text-indigo-700'
                      )}>
                        {periodLabel}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="font-mono font-semibold text-sm text-blue-700">
                      {typeof ext.value === 'number' ? ext.value.toLocaleString() : ext.value}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className={'inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ' + (
                        ext.source === 'document' ? 'bg-blue-100 text-blue-700' :
                        ext.source === 'inferred' ? 'bg-amber-100 text-amber-700' :
                        'bg-gray-100 text-gray-500'
                      )}>
                        {ext.source === 'document' ? '文書' : ext.source === 'inferred' ? '推定' : '初期値'}
                      </span>
                      <span className={'text-xs font-mono font-bold px-1.5 py-0.5 rounded ' + confBg + ' ' + confColor}>
                        {pct}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
        {filteredExtractions.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            該当する項目がありません
          </div>
        )}
      </div>
    )
  }

  // Desktop: table view
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">シート</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">セル</th>
            <th className="text-left px-3 py-3 text-xs font-medium text-gray-500">ラベル</th>
            <th className="text-center px-3 py-3 text-xs font-medium text-gray-500">年次</th>
            <th className="text-right px-4 py-3 text-xs font-medium text-gray-500">値</th>
            <th className="text-center px-3 py-3 text-xs font-medium text-gray-500">ソース</th>
            <th className="text-right px-3 py-3 text-xs font-medium text-gray-500">確信度</th>
          </tr>
        </thead>
        <tbody>
          {extractions.map((ext: any, idx: number) => {
            const isSelected = selectedItem?.sheet === ext.sheet && selectedItem?.cell === ext.cell
            const pct = Math.round((ext.confidence || 0) * 100)
            const confColor = pct >= 80 ? 'text-green-700' : pct >= 50 ? 'text-yellow-700' : 'text-red-600'
            const periodLabel = getPeriodLabel(ext)
            return (
              <tr
                key={`${ext.sheet}-${ext.cell}-${idx}`}
                onClick={() => onRowClick?.(ext)}
                className={`border-b border-gray-50 cursor-pointer transition-colors ${
                  isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-4 py-2.5 text-gray-700 whitespace-nowrap text-xs">{ext.sheet}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-gray-400">{ext.cell}</td>
                <td className="px-3 py-2.5 text-gray-700 text-xs truncate max-w-[140px]">
                  {ext.label || ext.original_text || '—'}
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    periodLabel === '—' ? 'bg-gray-100 text-gray-400' : 'bg-indigo-100 text-indigo-700'
                  }`}>
                    {periodLabel}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono font-semibold text-blue-700">
                  {typeof ext.value === 'number' ? ext.value.toLocaleString() : ext.value}
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    ext.source === 'document' ? 'bg-blue-100 text-blue-700' :
                    ext.source === 'inferred' ? 'bg-amber-100 text-amber-700' :
                    'bg-gray-100 text-gray-500'
                  }`}>
                    {ext.source === 'document' ? '文書' : ext.source === 'inferred' ? '推定' : '初期値'}
                  </span>
                </td>
                <td className={`px-3 py-2.5 text-right font-mono text-xs font-semibold ${confColor}`}>
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

/**
 * Low confidence review panel.
 * Provides per-item edit/approve and batch actions.
 */
function LowConfidenceReview({
  items,
  impactSummary,
  reviewEdits,
  approvedItems,
  reviewedCount,
  savingEdits,
  getItemKey,
  onEditItem,
  onApproveItem,
  onApproveAll,
  onSave,
  onCancel,
}: {
  items: any[]
  impactSummary: { totalValue: number; lowConfValue: number; pct: number }
  reviewEdits: Record<string, { value: number | string; reason: string }>
  approvedItems: Set<string>
  reviewedCount: number
  savingEdits: boolean
  getItemKey: (item: any) => string
  onEditItem: (item: any, value: number | string, reason: string) => void
  onApproveItem: (item: any) => void
  onApproveAll: () => void
  onSave: () => void
  onCancel: () => void
}) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-base font-semibold text-amber-900 flex items-center gap-2">
              <span className="text-amber-500">!</span>
              要確認: 低確信度パラメータ {items.length} 件
            </h3>
            <p className="text-sm text-amber-700 mt-1">
              {impactSummary.pct > 0
                ? `モデル全体の金額ベースで約 ${impactSummary.pct}% が推定値です。`
                : '以下の項目は文書に十分な根拠がなく、推定値が使用されています。'}
              各項目を確認し、値の修正または承認を行ってください。
            </p>
          </div>
          <button
            onClick={onCancel}
            className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1"
          >
            閉じる
          </button>
        </div>

        {/* Progress */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-amber-700 mb-1">
            <span>レビュー進捗</span>
            <span>{reviewedCount} / {items.length} 件完了</span>
          </div>
          <div className="w-full bg-amber-200 rounded-full h-2">
            <div
              className="h-2 rounded-full bg-amber-500 transition-all"
              style={{ width: items.length > 0 ? `${Math.round((reviewedCount / items.length) * 100)}%` : '0%' }}
            />
          </div>
        </div>
      </div>

      {/* Review Items */}
      <div className="space-y-3">
        {items.map(function(item: any, idx: number) {
          var key = getItemKey(item)
          var isApproved = approvedItems.has(key)
          var editData = reviewEdits[key]
          var isEdited = !!editData
          return (
            <ReviewItemCard
              key={key + '-' + idx}
              item={item}
              itemKey={key}
              isApproved={isApproved}
              isEdited={isEdited}
              editData={editData}
              onEdit={onEditItem}
              onApprove={onApproveItem}
            />
          )
        })}
      </div>

      {/* Batch Actions */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onApproveAll}
            className="text-sm text-amber-700 bg-amber-100 px-4 py-2 rounded-lg hover:bg-amber-200 transition-colors"
          >
            残り全て承認
          </button>
          <span className="text-xs text-gray-400">
            未対応の推定値を現在の値のまま確定します
          </span>
        </div>
        <button
          onClick={onSave}
          disabled={savingEdits || reviewedCount === 0}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {savingEdits ? '保存中...' : `レビュー結果を保存 (${reviewedCount}件)`}
        </button>
      </div>
    </div>
  )
}

/**
 * Individual review item card with edit/approve actions.
 */
function ReviewItemCard({
  item,
  itemKey,
  isApproved,
  isEdited,
  editData,
  onEdit,
  onApprove,
}: {
  item: any
  itemKey: string
  isApproved: boolean
  isEdited: boolean
  editData?: { value: number | string; reason: string }
  onEdit: (item: any, value: number | string, reason: string) => void
  onApprove: (item: any) => void
}) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState(editData?.value?.toString() || '')
  const [editReason, setEditReason] = useState(editData?.reason || '')

  var pct = Math.round((item.confidence || 0) * 100)
  var sourceLabel = item.source === 'document' ? '文書' : item.source === 'inferred' ? '推定' : '初期値'
  var evidence = item.evidence

  // Period label
  var periodLabel = '—'
  if (item.period) {
    var m = item.period.match(/FY(\d+)/i)
    if (m) periodLabel = m[1] + '年目'
  } else {
    var col = (item.cell || '').replace(/\d/g, '').toUpperCase()
    var map: Record<string, string> = { C: '1年目', D: '2年目', E: '3年目', F: '4年目', G: '5年目' }
    periodLabel = map[col] || '—'
  }

  function handleSubmitEdit() {
    var numVal = parseFloat(editValue.replace(/,/g, ''))
    if (isNaN(numVal)) {
      onEdit(item, editValue, editReason)
    } else {
      onEdit(item, numVal, editReason)
    }
    setEditing(false)
  }

  // Completed state (approved or edited)
  if (isApproved || isEdited) {
    return (
      <div className={`rounded-xl border p-4 transition-all ${
        isEdited ? 'bg-blue-50 border-blue-200' : 'bg-green-50 border-green-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-lg ${isEdited ? '' : ''}`}>{isEdited ? '\u270F\uFE0F' : '\u2705'}</span>
            <div>
              <span className="text-sm font-medium text-gray-800">
                {item.label || item.original_text || item.cell}
              </span>
              <span className="text-xs text-gray-400 ml-2">{periodLabel}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isEdited && editData ? (
              <div className="text-right">
                <span className="text-xs text-gray-400 line-through mr-2">
                  {typeof item.value === 'number' ? item.value.toLocaleString() : item.value}
                </span>
                <span className="text-sm font-mono font-bold text-blue-700">
                  {typeof editData.value === 'number' ? editData.value.toLocaleString() : editData.value}
                </span>
              </div>
            ) : (
              <span className="text-sm font-mono font-semibold text-gray-700">
                {typeof item.value === 'number' ? item.value.toLocaleString() : item.value}
              </span>
            )}
            <button
              onClick={function() {
                if (isEdited) {
                  setEditing(true)
                  setEditValue(editData?.value?.toString() || '')
                  setEditReason(editData?.reason || '')
                } else {
                  setEditing(true)
                  setEditValue('')
                  setEditReason('')
                }
              }}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              変更
            </button>
          </div>
        </div>
        {isEdited && editData?.reason && (
          <p className="text-xs text-blue-600 mt-1 ml-9">理由: {editData.reason}</p>
        )}
      </div>
    )
  }

  // Editing state
  if (editing) {
    return (
      <div className="rounded-xl border border-blue-300 bg-blue-50 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-gray-800">
              {item.label || item.original_text || item.cell}
            </span>
            <span className="text-xs text-gray-400 ml-2">{periodLabel}</span>
          </div>
          <span className="text-xs text-gray-400">
            現在値: {typeof item.value === 'number' ? item.value.toLocaleString() : item.value}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">修正値</label>
            <input
              type="text"
              value={editValue}
              onChange={function(e) { setEditValue(e.target.value) }}
              placeholder="例: 50000000"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-300 focus:border-blue-400 outline-none"
              autoFocus
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">修正理由（任意）</label>
            <input
              type="text"
              value={editReason}
              onChange={function(e) { setEditReason(e.target.value) }}
              placeholder="例: 実績ベースで修正"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-300 focus:border-blue-400 outline-none"
            />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={function() { setEditing(false) }}
            className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5"
          >
            キャンセル
          </button>
          <button
            onClick={handleSubmitEdit}
            disabled={!editValue.trim()}
            className="text-xs bg-blue-600 text-white px-4 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            確定
          </button>
        </div>
      </div>
    )
  }

  // Default state: pending review
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800">
              {item.label || item.original_text || item.cell}
            </span>
            <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${
              item.source === 'document' ? 'bg-blue-100 text-blue-700' :
              item.source === 'inferred' ? 'bg-amber-100 text-amber-700' :
              'bg-gray-100 text-gray-500'
            }`}>
              {sourceLabel}
            </span>
            <span className="text-xs text-red-500 font-mono font-semibold">{pct}%</span>
            <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold ${
              periodLabel === '—' ? 'bg-gray-100 text-gray-400' : 'bg-indigo-100 text-indigo-700'
            }`}>
              {periodLabel}
            </span>
          </div>
          {/* Evidence / Rationale */}
          <div className="mt-2 text-xs text-gray-500">
            {evidence?.quote ? (
              <span>&ldquo;{evidence.quote}&rdquo;</span>
            ) : evidence?.rationale ? (
              <span>{evidence.rationale}</span>
            ) : item.reasoning ? (
              <span>{item.reasoning}</span>
            ) : (
              <span className="text-gray-400">文書に記載なし — 推定値を使用</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-4">
          <span className="text-lg font-mono font-bold text-blue-700 mr-2">
            {typeof item.value === 'number' ? item.value.toLocaleString() : item.value}
          </span>
          <button
            onClick={function() {
              setEditing(true)
              setEditValue('')
              setEditReason('')
            }}
            className="text-xs border border-gray-300 text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors"
          >
            値を修正
          </button>
          <button
            onClick={function() { onApprove(item) }}
            className="text-xs border border-green-300 text-green-700 px-3 py-1.5 rounded-lg hover:bg-green-50 transition-colors"
          >
            承認
          </button>
        </div>
      </div>
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
