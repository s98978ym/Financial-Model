'use client'

import { useMemo, useState, useEffect } from 'react'
import { formatValue, categorizePL, PL_COLORS, PURPOSE_LABELS, type PLCategory } from './formatters'

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

/** Determine year index (0-4) from cell column or period field */
function getYearIndex(item: EnrichedItem): number | null {
  // From period field: "FY1" → 0, "FY2" → 1, etc.
  if (item.period) {
    var match = item.period.match(/FY(\d+)/i)
    if (match) {
      var idx = parseInt(match[1]) - 1
      if (idx >= 0 && idx < 5) return idx
    }
  }
  // From cell column: C=0, D=1, E=2, F=3, G=4
  var col = item.cell.replace(/\d/g, '').toUpperCase()
  var colMap: Record<string, number> = { C: 0, D: 1, E: 2, F: 3, G: 4 }
  if (col in colMap) return colMap[col]
  return null
}

/** Get row number from cell address: "C5" → 5 */
function getRowNumber(cell: string): number {
  return parseInt(cell.replace(/[A-Z]/gi, '')) || 0
}

/** Year-grouped row: one metric across FY1-FY5 */
interface YearGroupedRow {
  label: string
  category: string
  unit: string
  assignedConcept: string
  /** Per-year values: index 0=FY1 .. 4=FY5. null if no data */
  yearValues: (EnrichedItem | null)[]
  /** Average confidence across available years */
  avgConfidence: number
  /** Primary source type */
  primarySource: string
  /** Is estimated */
  isEstimated: boolean
  /** Row number in Excel for sorting */
  rowNumber: number
}

/** Group enriched items into year-grouped rows */
function groupByYears(items: EnrichedItem[]): YearGroupedRow[] {
  // Group by row number (same Excel row = same metric)
  var rowGroups: Record<number, EnrichedItem[]> = {}
  items.forEach(function(item) {
    var rowNum = getRowNumber(item.cell)
    if (!rowGroups[rowNum]) rowGroups[rowNum] = []
    rowGroups[rowNum].push(item)
  })

  var rows: YearGroupedRow[] = []
  var rowNums = Object.keys(rowGroups).map(Number).sort(function(a, b) { return a - b })

  rowNums.forEach(function(rowNum) {
    var group = rowGroups[rowNum]
    // Use first item's label, or find best label
    var bestLabel = ''
    var bestCategory = ''
    var bestUnit = ''
    var bestConcept = ''
    var yearValues: (EnrichedItem | null)[] = [null, null, null, null, null]
    var totalConf = 0
    var confCount = 0
    var sources: Record<string, number> = {}
    var isEstimated = false

    group.forEach(function(item) {
      // Best label = first non-empty
      if (!bestLabel && item.label) bestLabel = item.label
      if (!bestCategory && item.category) bestCategory = item.category
      if (!bestUnit && item.unit) bestUnit = item.unit
      if (!bestConcept && item.assignedConcept) bestConcept = item.assignedConcept
      if (item.derivation === 'estimated') isEstimated = true

      var yearIdx = getYearIndex(item)
      if (yearIdx !== null && yearIdx >= 0 && yearIdx < 5) {
        yearValues[yearIdx] = item
      } else if (group.length === 1) {
        // Single item with no year info - show in first column
        yearValues[0] = item
      }

      totalConf += item.confidence
      confCount++
      var src = item.source || 'unknown'
      sources[src] = (sources[src] || 0) + 1
    })

    // Primary source: most common
    var primarySource = ''
    var maxSrcCount = 0
    Object.keys(sources).forEach(function(src) {
      if (sources[src] > maxSrcCount) {
        maxSrcCount = sources[src]
        primarySource = src
      }
    })

    rows.push({
      label: bestLabel || bestConcept || '—',
      category: bestCategory,
      unit: bestUnit,
      assignedConcept: bestConcept,
      yearValues: yearValues,
      avgConfidence: confCount > 0 ? totalConf / confCount : 0,
      primarySource: primarySource,
      isEstimated: isEstimated,
      rowNumber: rowNum,
    })
  })

  return rows
}

var YEAR_HEADERS = ['1年目', '2年目', '3年目', '4年目', '5年目']
var YEAR_HEADERS_SHORT = ['1Y', '2Y', '3Y', '4Y', '5Y']

/**
 * PLPreviewTable renders financial data in a hierarchical P&L structure,
 * grouped by sheet/category with color coding and formatted values.
 *
 * In extraction mode: year-grouped view with FY1-FY5 columns.
 * In assignment mode: concept mapping view.
 */
export function PLPreviewTable({
  items,
  assignments,
  sheetMappings,
  mode = 'extraction',
  onRowClick,
  selectedItem,
}: PLPreviewTableProps) {
  var [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({})

  // Build lookups
  var { sections, totalItems } = useMemo(function() {
    // Phase 4 assignment lookup: sheet:cell → assignment
    var assignmentLookup: Record<string, any> = {};
    (assignments || []).forEach(function(a: any) {
      assignmentLookup[a.sheet + ':' + a.cell] = a
    })

    // Phase 3 sheet purpose lookup: sheetName → { purpose, segment }
    var sheetInfoLookup: Record<string, { purpose: string; segment: string }> = {};
    (sheetMappings || []).forEach(function(sm: any) {
      var name = sm.sheet_name || sm.sheet || ''
      sheetInfoLookup[name] = {
        purpose: sm.sheet_purpose || sm.purpose || 'other',
        segment: sm.mapped_segment || sm.segment || '',
      }
    })

    // Enrich items
    var enriched: EnrichedItem[] = items.map(function(item: any) {
      var sheet = item.sheet || ''
      var cell = item.cell || ''
      var key = sheet + ':' + cell
      var assignment = assignmentLookup[key]
      var sheetInfo = sheetInfoLookup[sheet]

      var label = item.label || (assignment && assignment.label) || (assignment && assignment.assigned_concept) || ''
      var category = item.category || (assignment && assignment.category) || ''
      var segment = item.segment || (assignment && assignment.segment) || (sheetInfo && sheetInfo.segment) || ''
      var period = item.period || (assignment && assignment.period) || ''
      var unit = item.unit || (assignment && assignment.unit) || ''

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
    var sheetGroupsObj: Record<string, EnrichedItem[]> = {}
    enriched.forEach(function(item) {
      if (!sheetGroupsObj[item.sheet]) {
        sheetGroupsObj[item.sheet] = []
      }
      sheetGroupsObj[item.sheet].push(item)
    })

    // Sort and categorize sections
    var sectionsList: GroupedSection[] = []
    var categoryOrder: PLCategory[] = ['revenue', 'cogs', 'opex', 'assumption', 'profit', 'other']

    Object.keys(sheetGroupsObj).forEach(function(sheetName) {
      var sheetItems = sheetGroupsObj[sheetName]
      var sheetInfo = sheetInfoLookup[sheetName]
      var purpose = (sheetInfo && sheetInfo.purpose) || 'other'
      var segment = (sheetInfo && sheetInfo.segment) || ''

      var firstCategory = (sheetItems[0] && sheetItems[0].category) || ''
      var plCategory = categorizePL(firstCategory, purpose)

      // Sort items by cell address
      sheetItems.sort(function(a, b) {
        var aRow = getRowNumber(a.cell)
        var bRow = getRowNumber(b.cell)
        if (aRow !== bRow) return aRow - bRow
        return a.cell.localeCompare(b.cell)
      })

      sectionsList.push({ sheetName: sheetName, purpose: purpose, segment: segment, plCategory: plCategory, items: sheetItems })
    })

    // Sort sections by P&L order
    sectionsList.sort(function(a, b) {
      var aIdx = categoryOrder.indexOf(a.plCategory)
      var bIdx = categoryOrder.indexOf(b.plCategory)
      return aIdx - bIdx
    })

    return { sections: sectionsList, totalItems: enriched.length }
  }, [items, assignments, sheetMappings, mode])

  function toggleSection(sheetName: string) {
    setCollapsedSections(function(prev) {
      var next = Object.assign({}, prev)
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
      {sections.map(function(section) {
        var colors = PL_COLORS[section.plCategory]
        var isCollapsed = collapsedSections[section.sheetName]
        var purposeLabel = PURPOSE_LABELS[section.purpose] || section.purpose

        return (
          <div
            key={section.sheetName}
            className={'rounded-xl border ' + colors.border + ' overflow-hidden shadow-sm'}
          >
            {/* Section Header */}
            <button
              onClick={function() { toggleSection(section.sheetName) }}
              className={'w-full flex items-center justify-between px-4 py-3 ' + colors.headerBg + ' ' + colors.headerText + ' transition-colors hover:opacity-90'}
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
                  className={'w-4 h-4 transition-transform ' + (isCollapsed ? '' : 'rotate-180')}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            {/* Section Content */}
            {!isCollapsed && (
              <div className={colors.bg}>
                {mode === 'extraction'
                  ? <YearGroupedTable
                      items={section.items}
                      colors={colors}
                      onRowClick={onRowClick}
                      selectedItem={selectedItem}
                    />
                  : <AssignmentTable
                      items={section.items}
                      colors={colors}
                      onRowClick={onRowClick}
                      selectedItem={selectedItem}
                    />
                }
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/** Mobile card view for a single year-grouped row */
function MobileYearCard({
  row,
  colors,
  onRowClick,
  isSelected,
}: {
  row: YearGroupedRow
  colors: typeof PL_COLORS[PLCategory]
  onRowClick?: (item: any) => void
  isSelected: boolean
}) {
  var [expanded, setExpanded] = useState(false)
  var pct = Math.round(row.avgConfidence * 100)
  var confColor = pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-yellow-600' : 'text-red-600'
  var confBg = pct >= 80 ? 'bg-green-100' : pct >= 50 ? 'bg-yellow-100' : 'bg-red-100'

  // Find first non-null year value for quick display
  var firstVal: EnrichedItem | null = null
  row.yearValues.forEach(function(yv) { if (!firstVal && yv) firstVal = yv })

  return (
    <div
      className={
        'rounded-lg border p-3 transition-all ' +
        (isSelected ? 'ring-2 ring-blue-400 border-blue-200 bg-blue-50/50' : 'border-gray-200 bg-white')
      }
    >
      {/* Card Header */}
      <button
        onClick={function() { setExpanded(!expanded) }}
        className="w-full"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0 text-left">
            <div className="flex items-center gap-1.5">
              {row.isEstimated && (
                <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 flex-shrink-0">
                  推定
                </span>
              )}
              <span className={'font-medium text-sm truncate ' + colors.text}>
                {row.label}
              </span>
            </div>
            {row.unit && (
              <span className="text-[10px] text-gray-400 mt-0.5 block">単位: {row.unit}</span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={'text-xs font-mono font-bold px-1.5 py-0.5 rounded ' + confBg + ' ' + confColor}>
              {pct}%
            </span>
            <SourceBadge source={row.primarySource} />
            <svg
              className={'w-4 h-4 text-gray-400 transition-transform ' + (expanded ? 'rotate-180' : '')}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        {/* Quick FY1 value preview */}
        {!expanded && firstVal && (
          <div className="mt-1.5 text-left">
            <span className="text-[10px] text-gray-400">FY1: </span>
            <span className={
              'font-mono font-semibold text-sm ' +
              (firstVal.source === 'document' ? 'text-blue-700' :
               firstVal.source === 'inferred' ? 'text-amber-700' : 'text-gray-600')
            }>
              {firstVal.formattedValue}
            </span>
          </div>
        )}
      </button>

      {/* Expanded: all year values */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
          {YEAR_HEADERS.map(function(header, yi) {
            var yv = row.yearValues[yi]
            return (
              <div
                key={yi}
                onClick={function() { if (yv) onRowClick?.(yv.raw) }}
                className={
                  'flex items-center justify-between py-1.5 px-2 rounded ' +
                  (yv ? 'cursor-pointer hover:bg-blue-50 active:bg-blue-100' : '') +
                  (!yv ? ' opacity-50' : '')
                }
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-400 w-7">FY{yi + 1}</span>
                  <span className="text-xs text-gray-600">{header}</span>
                </div>
                <span className={
                  'font-mono font-semibold text-sm ' +
                  (yv
                    ? (yv.source === 'document' ? 'text-blue-700' :
                       yv.source === 'inferred' ? 'text-amber-700' : 'text-gray-600')
                    : 'text-gray-300')
                }>
                  {yv ? yv.formattedValue : '—'}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/** Year-grouped table for extraction mode: shows FY1-FY5 in columns */
function YearGroupedTable({
  items,
  colors,
  onRowClick,
  selectedItem,
}: {
  items: EnrichedItem[]
  colors: typeof PL_COLORS[PLCategory]
  onRowClick?: (item: any) => void
  selectedItem?: any
}) {
  var isMobile = useIsMobile()
  var groupedRows = useMemo(function() {
    return groupByYears(items)
  }, [items])

  // Mobile: card view
  if (isMobile) {
    return (
      <div className="space-y-2">
        {groupedRows.map(function(row, idx) {
          var isRowSelected = false
          row.yearValues.forEach(function(yv) {
            if (yv && selectedItem && selectedItem.sheet === yv.sheet && selectedItem.cell === yv.cell) {
              isRowSelected = true
            }
          })
          return (
            <MobileYearCard
              key={idx}
              row={row}
              colors={colors}
              onRowClick={onRowClick}
              isSelected={isRowSelected}
            />
          )
        })}
      </div>
    )
  }

  // Desktop: table view
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 min-w-[160px]">
              項目
            </th>
            {YEAR_HEADERS.map(function(header, i) {
              return (
                <th key={i} className="text-right px-3 py-2.5 text-xs font-medium text-gray-500 min-w-[90px]">
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] text-gray-400">FY{i + 1}</span>
                    <span>{header}</span>
                  </div>
                </th>
              )
            })}
            <th className="text-center px-3 py-2.5 text-xs font-medium text-gray-500 w-16">
              ソース
            </th>
            <th className="text-right px-3 py-2.5 text-xs font-medium text-gray-500 w-16">
              確信度
            </th>
          </tr>
        </thead>
        <tbody>
          {groupedRows.map(function(row, idx) {
            // Check if any year cell in this row is selected
            var isRowSelected = false
            row.yearValues.forEach(function(yv) {
              if (yv && selectedItem && selectedItem.sheet === yv.sheet && selectedItem.cell === yv.cell) {
                isRowSelected = true
              }
            })

            return (
              <tr
                key={idx}
                className={
                  'border-b border-gray-100 last:border-b-0 transition-colors ' +
                  (isRowSelected ? 'bg-blue-50 ring-1 ring-inset ring-blue-200' : 'hover:bg-white/60') +
                  (row.isEstimated ? ' opacity-80' : '')
                }
              >
                {/* Label */}
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {row.isEstimated && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 flex-shrink-0">
                        推定
                      </span>
                    )}
                    <div>
                      <div className={'font-medium text-sm ' + colors.text}>
                        {row.label}
                      </div>
                      {row.unit && (
                        <div className="text-[10px] text-gray-400">
                          単位: {row.unit}
                        </div>
                      )}
                    </div>
                  </div>
                </td>

                {/* Year values FY1-FY5 */}
                {row.yearValues.map(function(yv, yi) {
                  if (!yv) {
                    return (
                      <td key={yi} className="px-3 py-2.5 text-right">
                        <span className="text-gray-300">—</span>
                      </td>
                    )
                  }

                  var isThisCellSelected = selectedItem &&
                    selectedItem.sheet === yv.sheet &&
                    selectedItem.cell === yv.cell

                  return (
                    <td
                      key={yi}
                      onClick={function() { onRowClick?.(yv.raw) }}
                      className={
                        'px-3 py-2.5 text-right cursor-pointer transition-colors ' +
                        (isThisCellSelected
                          ? 'bg-blue-100 rounded'
                          : 'hover:bg-blue-50 rounded')
                      }
                    >
                      <span className={
                        'font-mono font-semibold text-sm ' +
                        (yv.source === 'document' ? 'text-blue-700' :
                         yv.source === 'inferred' ? 'text-amber-700' :
                         'text-gray-600')
                      }>
                        {yv.formattedValue}
                      </span>
                    </td>
                  )
                })}

                {/* Source */}
                <td className="px-3 py-2.5 text-center">
                  <SourceBadge source={row.primarySource} />
                </td>

                {/* Confidence */}
                <td className="px-3 py-2.5">
                  <ConfidenceBar confidence={row.avgConfidence} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** Assignment table for Phase 4 (concept mapping mode) */
function AssignmentTable({
  items,
  colors,
  onRowClick,
  selectedItem,
}: {
  items: EnrichedItem[]
  colors: typeof PL_COLORS[PLCategory]
  onRowClick?: (item: any) => void
  selectedItem?: any
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200">
          <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-12">
            セル
          </th>
          <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">
            コンセプト
          </th>
          <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-24">
            カテゴリ
          </th>
          <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 w-20">
            期間
          </th>
          <th className="text-center px-4 py-2 text-xs font-medium text-gray-500 w-20">
            ソース
          </th>
          <th className="text-right px-4 py-2 text-xs font-medium text-gray-500 w-24">
            確信度
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map(function(item, idx) {
          var isSelected = selectedItem &&
            selectedItem.sheet === item.sheet &&
            selectedItem.cell === item.cell
          var isEstimated = item.derivation === 'estimated'

          return (
            <tr
              key={item.sheet + '-' + item.cell + '-' + idx}
              onClick={function() { onRowClick?.(item.raw) }}
              className={
                'border-b border-gray-100 last:border-b-0 cursor-pointer transition-colors ' +
                (isSelected
                  ? 'bg-blue-100 ring-1 ring-inset ring-blue-300'
                  : 'hover:bg-white/60') +
                (isEstimated ? ' opacity-80' : '')
              }
            >
              {/* Cell reference */}
              <td className="px-4 py-2.5 font-mono text-xs text-gray-400">
                {item.cell}
              </td>

              {/* Concept */}
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-2">
                  {isEstimated && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 flex-shrink-0">
                      推定
                    </span>
                  )}
                  <div>
                    <div className={'font-medium ' + colors.text}>
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

              {/* Category */}
              <td className="px-4 py-2.5">
                <span className={'inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium ' + colors.bg + ' ' + colors.text}>
                  {item.category || '—'}
                </span>
              </td>

              {/* Period */}
              <td className="px-4 py-2.5 text-xs text-gray-500">
                {item.period || '—'}
              </td>

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
  )
}

/** Source badge with Japanese labels */
function SourceBadge({ source }: { source: string }) {
  if (!source) return <span className="text-gray-300">—</span>

  var config: Record<string, { bg: string; text: string; label: string }> = {
    document: { bg: 'bg-blue-100', text: 'text-blue-700', label: '文書' },
    inferred: { bg: 'bg-amber-100', text: 'text-amber-700', label: '推定' },
    default: { bg: 'bg-gray-100', text: 'text-gray-500', label: '初期値' },
    estimated: { bg: 'bg-amber-100', text: 'text-amber-700', label: '推定' },
    direct: { bg: 'bg-blue-100', text: 'text-blue-700', label: '直接' },
    calculated: { bg: 'bg-purple-100', text: 'text-purple-700', label: '算出' },
    assumption: { bg: 'bg-slate-100', text: 'text-slate-600', label: '前提' },
  }

  var c = config[source] || { bg: 'bg-gray-100', text: 'text-gray-500', label: source }

  return (
    <span className={'inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ' + c.bg + ' ' + c.text}>
      {c.label}
    </span>
  )
}

/** Confidence bar with percentage and color */
function ConfidenceBar({ confidence }: { confidence: number }) {
  var pct = Math.round(confidence * 100)
  var color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-400'
  var textColor = pct >= 80 ? 'text-green-700' : pct >= 50 ? 'text-yellow-700' : 'text-red-600'

  return (
    <div className="flex items-center gap-1.5 justify-end">
      <div className="w-10 bg-gray-200 rounded-full h-1.5 hidden sm:block">
        <div
          className={color + ' h-1.5 rounded-full transition-all'}
          style={{ width: pct + '%' }}
        />
      </div>
      <span className={'text-xs font-mono font-semibold ' + textColor + ' w-8 text-right'}>
        {pct}%
      </span>
    </div>
  )
}
