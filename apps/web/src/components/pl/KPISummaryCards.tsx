'use client'

import { useMemo } from 'react'
import { formatJPY } from './formatters'

interface KPISummaryCardsProps {
  extractions: any[]
  assignments?: any[]
  sheetMappings?: any[]
}

interface KPICard {
  label: string
  value: string
  subtext: string
  color: 'blue' | 'green' | 'orange' | 'red' | 'slate'
  icon: string
}

export function KPISummaryCards({ extractions, assignments, sheetMappings }: KPISummaryCardsProps) {
  const cards = useMemo(() => {
    const result: KPICard[] = []

    // Build assignment lookup for categories
    const assignmentLookup: Record<string, any> = {};
    (assignments || []).forEach(function(a: any) {
      assignmentLookup[a.sheet + ':' + a.cell] = a
    })

    // Build sheet purpose lookup
    const sheetPurposeLookup: Record<string, string> = {};
    (sheetMappings || []).forEach(function(sm: any) {
      sheetPurposeLookup[sm.sheet_name || sm.sheet || ''] = sm.sheet_purpose || sm.purpose || ''
    })

    // Categorize extractions
    const revenueItems: number[] = []
    const costItems: number[] = []
    let docSourceCount = 0
    const totalCount = extractions.length
    let highConfCount = 0
    const segmentNames: Record<string, boolean> = {}

    extractions.forEach(function(ext: any) {
      const key = ext.sheet + ':' + ext.cell
      const assignment = assignmentLookup[key]
      const sheetPurpose = sheetPurposeLookup[ext.sheet] || ''

      const category = (assignment && assignment.category) || ''
      const segment = (assignment && assignment.segment) || ''
      if (segment) segmentNames[segment] = true

      const val = typeof ext.value === 'number' ? ext.value : parseFloat(String(ext.value || '0').replace(/,/g, ''))

      if (category.includes('売上') || category.includes('収益') || sheetPurpose === 'revenue_model') {
        if (!isNaN(val) && val > 0) revenueItems.push(val)
      } else if (category.includes('原価') || category.includes('変動費') || category.includes('固定費') ||
                 category.includes('人件費') || category.includes('販管費') || sheetPurpose === 'cost_detail') {
        if (!isNaN(val) && val > 0) costItems.push(val)
      }

      if (ext.source === 'document') docSourceCount++
      if ((ext.confidence || 0) >= 0.8) highConfCount++
    })

    const segmentCount = Object.keys(segmentNames).length

    // Card 1: Total Parameters
    result.push({
      label: 'パラメータ数',
      value: '' + totalCount,
      subtext: segmentCount + ' セグメント',
      color: 'blue',
      icon: '📊',
    })

    // Card 2: Data Quality
    const docPct = totalCount > 0 ? Math.round((docSourceCount / totalCount) * 100) : 0
    result.push({
      label: 'データ品質',
      value: `${docPct}%`,
      subtext: `${docSourceCount}/${totalCount} 文書由来`,
      color: docPct >= 70 ? 'green' : docPct >= 40 ? 'orange' : 'red',
      icon: '✅',
    })

    // Card 3: High Confidence
    const confPct = totalCount > 0 ? Math.round((highConfCount / totalCount) * 100) : 0
    result.push({
      label: '高確信度',
      value: `${confPct}%`,
      subtext: `${highConfCount} 項目が確信度80%以上`,
      color: confPct >= 70 ? 'green' : confPct >= 40 ? 'orange' : 'red',
      icon: '🎯',
    })

    // Card 4: Revenue items found
    if (revenueItems.length > 0) {
      const maxRev = Math.max(...revenueItems)
      result.push({
        label: '売上関連',
        value: `${revenueItems.length} 項目`,
        subtext: `最大 ${formatJPY(maxRev)}`,
        color: 'blue',
        icon: '📈',
      })
    } else {
      // Cost items instead
      result.push({
        label: 'コスト関連',
        value: `${costItems.length} 項目`,
        subtext: costItems.length > 0 ? `最大 ${formatJPY(Math.max(...costItems))}` : '—',
        color: 'orange',
        icon: '🏢',
      })
    }

    return result
  }, [extractions, assignments, sheetMappings])

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
      {cards.map((card, i) => {
        return (
          <div
            key={i}
            className="bg-white rounded-3xl shadow-warm p-5 transition-all hover:shadow-warm-md"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-sand-400 tracking-wide">
                {card.label}
              </span>
              <div className="w-8 h-8 rounded-xl bg-cream-200 flex items-center justify-center text-sm">
                {card.icon}
              </div>
            </div>
            <div className="text-2xl font-bold text-dark-900 mb-0.5">
              {card.value}
            </div>
            <div className="text-xs text-sand-400">
              {card.subtext}
            </div>
          </div>
        )
      })}
    </div>
  )
}
