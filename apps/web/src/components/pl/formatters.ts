/**
 * Financial formatting utilities for Japanese Yen and other units.
 * Follows Japanese business convention: 万 (10K), 億 (100M).
 */

/**
 * Format a numeric value with appropriate Japanese unit suffix.
 * Examples:
 *   5800     → "5,800"
 *   58000    → "5.8万"
 *   58000000 → "5,800万"
 *   580000000 → "5.8億"
 */
export function formatJPY(value: number | string | null | undefined): string {
  if (value == null || value === '') return '—'
  const num = typeof value === 'string' ? parseFloat(value.replace(/,/g, '')) : value
  if (isNaN(num)) return String(value)

  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''

  if (abs >= 100_000_000) {
    // 億 (100M+)
    const oku = abs / 100_000_000
    return `${sign}${oku % 1 === 0 ? oku.toFixed(0) : oku.toFixed(1)}億円`
  }
  if (abs >= 10_000) {
    // 万 (10K+)
    const man = abs / 10_000
    if (man >= 1000) {
      return `${sign}${Math.round(man).toLocaleString()}万円`
    }
    return `${sign}${man % 1 === 0 ? man.toFixed(0) : man.toFixed(1)}万円`
  }
  return `${sign}${abs.toLocaleString()}円`
}

/**
 * Format a value with its unit context.
 * Handles: 円/万円/億円, %, 人, 件, etc.
 */
export function formatValue(
  value: number | string | null | undefined,
  unit?: string
): string {
  if (value == null || value === '') return '—'

  const strVal = String(value)

  // Already formatted (contains 万, 億, %)
  if (/[万億%人件月年]/.test(strVal)) return strVal

  const num = typeof value === 'string' ? parseFloat(value.replace(/,/g, '')) : value
  if (isNaN(num)) return strVal

  // Percentage
  if (unit === '%' || unit === 'パーセント' || unit === '％') {
    if (num <= 1 && num >= -1) return `${(num * 100).toFixed(1)}%`
    return `${num.toFixed(1)}%`
  }

  // People count
  if (unit === '人' || unit === '名') {
    return `${Math.round(num).toLocaleString()}${unit}`
  }

  // Count units
  if (unit === '件' || unit === '社' || unit === '店' || unit === '台') {
    return `${Math.round(num).toLocaleString()}${unit}`
  }

  // Currency (default)
  if (!unit || unit === '円' || unit === '千円' || unit === '万円' || unit === '億円') {
    // Adjust for unit scale
    let actualNum = num
    if (unit === '千円') actualNum = num * 1000
    else if (unit === '万円') actualNum = num * 10000
    else if (unit === '億円') actualNum = num * 100000000
    return formatJPY(actualNum)
  }

  // Other units
  return `${num.toLocaleString()}${unit}`
}

/**
 * Determine the P&L category color scheme.
 */
export type PLCategory = 'revenue' | 'cogs' | 'opex' | 'profit' | 'assumption' | 'other'

export function categorizePL(category: string, sheetPurpose?: string): PLCategory {
  const cat = (category || '').toLowerCase()
  const purpose = (sheetPurpose || '').toLowerCase()

  // Revenue
  if (cat.includes('売上') || cat.includes('収益') || cat.includes('ltv') ||
      cat.includes('mrr') || cat.includes('revenue') ||
      purpose === 'revenue_model') {
    return 'revenue'
  }

  // COGS
  if (cat.includes('原価') || cat.includes('変動費') || cat.includes('cogs')) {
    return 'cogs'
  }

  // OPEX
  if (cat.includes('販管費') || cat.includes('固定費') || cat.includes('人件費') ||
      cat.includes('開発費') || cat.includes('広告') || cat.includes('opex') ||
      cat.includes('営業費') || purpose === 'cost_detail') {
    return 'opex'
  }

  // Profit
  if (cat.includes('利益') || cat.includes('profit') || cat.includes('margin')) {
    return 'profit'
  }

  // Assumptions
  if (cat.includes('前提') || cat.includes('assumption') || cat.includes('kpi') ||
      cat.includes('成長率') || purpose === 'assumptions') {
    return 'assumption'
  }

  return 'other'
}

export const PL_COLORS: Record<PLCategory, {
  bg: string
  border: string
  text: string
  headerBg: string
  headerText: string
  icon: string
}> = {
  revenue: {
    bg: 'bg-blue-50/50',
    border: 'border-transparent',
    text: 'text-blue-700',
    headerBg: 'bg-dark-900',
    headerText: 'text-white',
    icon: '📈',
  },
  cogs: {
    bg: 'bg-red-50/50',
    border: 'border-transparent',
    text: 'text-red-700',
    headerBg: 'bg-dark-900',
    headerText: 'text-white',
    icon: '📦',
  },
  opex: {
    bg: 'bg-orange-50/50',
    border: 'border-transparent',
    text: 'text-orange-700',
    headerBg: 'bg-dark-900',
    headerText: 'text-white',
    icon: '🏢',
  },
  profit: {
    bg: 'bg-emerald-50/50',
    border: 'border-transparent',
    text: 'text-emerald-700',
    headerBg: 'bg-dark-900',
    headerText: 'text-white',
    icon: '💰',
  },
  assumption: {
    bg: 'bg-cream-100',
    border: 'border-transparent',
    text: 'text-sand-600',
    headerBg: 'bg-dark-900',
    headerText: 'text-white',
    icon: '⚙️',
  },
  other: {
    bg: 'bg-cream-100',
    border: 'border-transparent',
    text: 'text-sand-600',
    headerBg: 'bg-dark-800',
    headerText: 'text-white',
    icon: '📋',
  },
}

/**
 * Purpose labels for sheet types.
 */
export const PURPOSE_LABELS: Record<string, string> = {
  revenue_model: '収益モデル',
  cost_detail: 'コスト詳細',
  pl_summary: 'PL集計',
  assumptions: '前提条件',
  headcount: '人員計画',
  capex: '設備投資',
  other: 'その他',
}
