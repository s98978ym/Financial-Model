'use client'

import { useMemo, useState } from 'react'
import { formatValue, categorizePL, PL_COLORS, PURPOSE_LABELS, type PLCategory } from './formatters'

interface PLPreviewTableProps {
  /** Phase 5 extractions or Phase 4 assignments */
  items: any[]
  /** Phase 4 cell assignments (for enriching Phase 5 data) */
  assignments?: any[]
  /** Phase 3 sheet mappings (for sheet purposes/segments) */
  sheetMappings?: any[]
  /** Mode: 'extraction' (Phase 5) or 'assignment' (Phase 4) */
  mode?: 'extraction' | 'assignment'
  /** Callback when a row is clicked */
  onRowClick?: (item: any) => void
  /** Currently selected item */
  selectedItem?: any
}

interface GroupedSection {
  sheetName: string
  purpose: string
  segment: string
  plCategory: PLCategory
  items: EnrichedItem[]
}

interface EnrichedItem {
  // Original data
  raw: any
  // Enriched fields
  sheet: string
  cell: string
  label: string
  category: string
  segment: string
  period: string
  unit: string
  // Value fields (Phase 5)
  value?: any
  formattedValue: string
  originalText: string
  source: string
  confidence: number
  // Phase 4 fields
  assignedConcept: string
  derivation: string
  reasoning: string
}

/**
 * PLPreviewTable renders financial data in a hierarchical P&L structure,
 * grouped by sheet/category with color coding and formatted values.
 *
 * Replaces the flat AG-Grid with a financial-professional-grade table.
 */
export function PLPreviewTable({
  items,
  assignments,
  sheetMappings,
  mode = 'extraction',
  onRowClick,
  selectedItem,
}: PLPreviewTableProps) {
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({})

  // Build lookups
  const { sections, totalItems } = useMemo(() => {
    // Phase 4 assignment lookup: sheet:cell → assignment
    const assignmentLookup: Record<string, any> = {};
    (assignments || []).forEach(function(a: any) {
      assignmentLookup[a.sheet + ':' + a.cell] = a
    })

    // Phase 3 sheet purpose lookup: sheetName → { purpose, segment }
    const sheetInfoLookup: Record<string, { purpose: string; segment: string }> = {};
    (sheetMappings || []).forEach(function(sm: any) {
      const name = sm.sheet_name || sm.sheet || ''
      sheetInfoLookup[name] = {
        purpose: sm.sheet_purpose || sm.purpose || 'other',
        segment: sm.mapped_segment || sm.segment || '',
      }
    })

    // Enrich items
    const enriched: EnrichedItem[] = items.map(function(item: any) {
      const sheet = item.sheet || ''
      const cell = item.cell || ''
      const key = sheet + ':' + cell
      const assignment = assignmentLookup[key]
      const sheetInfo = sheetInfoLookup[sheet]

      const label = item.label || (assignment && assignment.label) || (assignment && assignment.assigned_concept) || ''
      const category = item.category || (assignment && assignment.category) || ''
      const segment = item.segment || (assignment && assignment.segment) || (sheetInfo && sheetInfo.segment) || ''
      const period = item.period || (assignment && assignment.period) || ''
      const unit = item.unit || (assignment && assignment.unit) || ''

      return {
        raw: item,
        sheet: sheet,
        cell: cell,
        label: label,
        category: category,
        segment: segment,
        period: period,
        unit: unit,
        value: item.value,
        formattedValue: mode === 'extraction'
          ? formatValue(item.value, unit)
          : '',
        originalText: item.original_text || '',
        source: item.source || item.derivation || '',
        confidence: item.confidence || 0,
        assignedConcept: item.assigned_concept || (assignment && assignment.assigned_concept) || '',
        derivation: item.derivation || (assignment && assignment.derivation) || '',
        reasoning: item.reasoning || (assignment && assignment.reasoning) || '',
      }
    })

    // Group by sheet
    const sheetGroupsObj: Record<string, EnrichedItem[]> = {}
    enriched.forEach(function(item) {
      if (!sheetGroupsObj[item.sheet]) {
        sheetGroupsObj[item.sheet] = []
      }
      sheetGroupsObj[item.sheet].push(item)
    })

    // Sort and categorize sections
    const sections: GroupedSection[] = []
    const categoryOrder: PLCategory[] = ['revenue', 'cogs', 'opex', 'assumption', 'profit', 'other']

    Object.keys(sheetGroupsObj).forEach(function(sheetName) {
      const sheetItems = sheetGroupsObj[sheetName]
      const sheetInfo = sheetInfoLookup[sheetName]
      const purpose = (sheetInfo && sheetInfo.purpose) || 'other'
      const segment = (sheetInfo && sheetInfo.segment) || ''

      // Determine PL category from first item or sheet purpose
      const firstCategory = (sheetItems[0] && sheetItems[0].category) || ''
      const plCategory = categorizePL(firstCategory, purpose)

      // Sort items by cell address
      sheetItems.sort(function(a, b) {
        const aRow = parseInt(a.cell.replace(/[A-Z]/g, '')) || 0
        const bRow = parseInt(b.cell.replace(/[A-Z]/g, '')) || 0
        if (aRow !== bRow) return aRow - bRow
        return a.cell.localeCompare(b.cell)
      })

      sections.push({ sheetName: sheetName, purpose: purpose, segment: segment, plCategory: plCategory, items: sheetItems })
    })

    // Sort sections by P&L order
    sections.sort(function(a, b) {
      const aIdx = categoryOrder.indexOf(a.plCategory)
      const bIdx = categoryOrder.indexOf(b.plCategory)
      return aIdx - bIdx
    })

    return { sections: sections, totalItems: enriched.length }
  }, [items, assignments, sheetMappings, mode])

  const toggleSection = (sheetName: string) => {
    setCollapsedSections(function(prev) {
      const next = Object.assign({}, prev)
      if (next[sheetName]) {
        delete next[sheetName]
      } else {
        next[sheetName] = true
      }
      return next
    })
  }

  if (totalItems === 0) {
    return (
      <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
        <p className="text-gray-400 text-sm">データがありません</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {sections.map((section) => {
        const colors = PL_COLORS[section.plCategory]
        const isCollapsed = collapsedSections[section.sheetName]
        const purposeLabel = PURPOSE_LABELS[section.purpose] || section.purpose

        return (
          <div
            key={section.sheetName}
            className={`rounded-xl border ${colors.border} overflow-hidden shadow-sm`}
          >
            {/* Section Header */}
            <button
              onClick={() => toggleSection(section.sheetName)}
              className={`w-full flex items-center justify-between px-4 py-3 ${colors.headerBg} ${colors.headerText} transition-colors hover:opacity-90`}
            >
              <div className="flex items-center gap-3">
                <span className="text-lg">{colors.icon}</span>
                <div className="text-left">
                  <div className="font-semibold text-sm">
                    {section.sheetName}
                    {section.segment && (
                      <span className="ml-2 opacity-80 font-normal">
                        — {section.segment}
                      </span>
                    )}
                  </div>
                  <div className="text-xs opacity-70">
                    {purposeLabel} · {section.items.length} 項目
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs opacity-70">
                  {isCollapsed ? '展開' : '折りたたむ'}
                </span>
                <svg
                  className={`w-4 h-4 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            {/* Section Content */}
            {!isCollapsed && (
              <div className={colors.bg}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-12">
                        セル
                      </th>
                      <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
                        {mode === 'extraction' ? 'ラベル / コンセプト' : 'コンセプト'}
                      </th>
                      {mode === 'extraction' && (
                        <th className="text-right px-4 py-2 text-xs font-medium text-gray-500 w-36">
                          値
                        </th>
                      )}
                      {mode === 'assignment' && (
                        <>
                          <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-24">
                            カテゴリ
                          </th>
                          <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-20">
                            期間
                          </th>
                        </>
                      )}
                      <th className="text-center px-4 py-2 text-xs font-medium text-gray-500 w-20">
                        ソース
                      </th>
                      <th className="text-right px-4 py-2 text-xs font-medium text-gray-500 w-24">
                        確信度
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {section.items.map((item, idx) => {
                      const isSelected = selectedItem &&
                        selectedItem.sheet === item.sheet &&
                        selectedItem.cell === item.cell
                      const isEstimated = item.derivation === 'estimated'

                      return (
                        <tr
                          key={`${item.sheet}-${item.cell}-${idx}`}
                          onClick={() => onRowClick?.(item.raw)}
                          className={`
                            border-b border-gray-100 last:border-b-0 cursor-pointer
                            transition-colors
                            ${isSelected
                              ? 'bg-blue-100 ring-1 ring-inset ring-blue-300'
                              : 'hover:bg-white/60'
                            }
                            ${isEstimated ? 'opacity-80' : ''}
                          `}
                        >
                          {/* Cell reference */}
                          <td className="px-4 py-2.5 font-mono text-xs text-gray-400">
                            {item.cell}
                          </td>

                          {/* Label / Concept */}
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-2">
                              {isEstimated && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 flex-shrink-0">
                                  推定
                                </span>
                              )}
                              <div>
                                <div className={`font-medium ${colors.text}`}>
                                  {item.label || item.assignedConcept || '—'}
                                </div>
                                {item.label && item.assignedConcept && item.label !== item.assignedConcept && (
                                  <div className="text-xs text-gray-400 mt-0.5">
                                    {item.assignedConcept.replace('【推定】', '')}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>

                          {/* Value (extraction mode) */}
                          {mode === 'extraction' && (
                            <td className="px-4 py-2.5 text-right">
                              <span className={`font-mono font-semibold ${
                                item.source === 'document' ? 'text-blue-700' :
                                item.source === 'inferred' ? 'text-amber-700' :
                                'text-gray-500'
                              }`}>
                                {item.formattedValue}
                              </span>
                              {item.originalText && item.originalText !== String(item.value) && (
                                <div className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[130px]">
                                  {item.originalText}
                                </div>
                              )}
                            </td>
                          )}

                          {/* Category & Period (assignment mode) */}
                          {mode === 'assignment' && (
                            <>
                              <td className="px-4 py-2.5">
                                <span className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium ${colors.bg} ${colors.text}`}>
                                  {item.category || '—'}
                                </span>
                              </td>
                              <td className="px-4 py-2.5 text-xs text-gray-500">
                                {item.period || '—'}
                              </td>
                            </>
                          )}

                          {/* Source */}
                          <td className="px-4 py-2.5 text-center">
                            <SourceBadge source={item.source} />
                          </td>

                          {/* Confidence */}
                          <td className="px-4 py-2.5">
                            <ConfidenceBar confidence={item.confidence} />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/** Source badge with Japanese labels */
function SourceBadge({ source }: { source: string }) {
  if (!source) return <span className="text-gray-300">—</span>

  const config: Record<string, { bg: string; text: string; label: string }> = {
    document: { bg: 'bg-blue-100', text: 'text-blue-700', label: '文書' },
    inferred: { bg: 'bg-amber-100', text: 'text-amber-700', label: '推定' },
    default: { bg: 'bg-gray-100', text: 'text-gray-500', label: '初期値' },
    estimated: { bg: 'bg-amber-100', text: 'text-amber-700', label: '推定' },
    direct: { bg: 'bg-blue-100', text: 'text-blue-700', label: '直接' },
    calculated: { bg: 'bg-purple-100', text: 'text-purple-700', label: '算出' },
    assumption: { bg: 'bg-slate-100', text: 'text-slate-600', label: '前提' },
  }

  const c = config[source] || { bg: 'bg-gray-100', text: 'text-gray-500', label: source }

  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  )
}

/** Confidence bar with percentage and color */
function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-400'
  const textColor = pct >= 80 ? 'text-green-700' : pct >= 50 ? 'text-yellow-700' : 'text-red-600'

  return (
    <div className="flex items-center gap-2 justify-end">
      <div className="w-16 bg-gray-200 rounded-full h-1.5 hidden sm:block">
        <div
          className={`${color} h-1.5 rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-mono font-semibold ${textColor} w-8 text-right`}>
        {pct}%
      </span>
    </div>
  )
}
