'use client'

import { useState, useEffect } from 'react'
import type { IndustryKey, DriverBenchmark } from '@/data/industryBenchmarks'
import { INDUSTRY_BENCHMARKS } from '@/data/industryBenchmarks'
import { RDThemeDetailPanel } from './RDThemeDetailPanel'
import type { RDThemeItem } from './RDThemeDetailPanel'

interface PayrollRoleDetail {
  label: string
  salary: number
  headcount: number[]
  cost: number[]
}

interface SGADetail {
  payroll: {
    roles: Record<string, PayrollRoleDetail>
    total: number[]
  }
  marketing: {
    categories: Record<string, number[]>
    total: number[]
  }
  office: number[]
  system: number[]
  other: number[]
}

interface DriverSlidersProps {
  parameters: Record<string, number>
  onChange: (key: string, value: number) => void
  onBatchChange?: (changes: Record<string, number>) => void
  industry?: IndustryKey
  sgaDetail?: SGADetail
  rdThemes?: RDThemeItem[]
  onRdThemesChange?: (themes: RDThemeItem[]) => void
}

var REVENUE_DRIVERS = [
  {
    key: 'revenue_fy1',
    label: '初年度売上',
    unit: '円',
    min: 10_000_000,
    max: 1_000_000_000,
    step: 10_000_000,
    format: function(v: number) { return (v / 100_000_000).toFixed(1) + '億円' },
  },
  {
    key: 'growth_rate',
    label: '売上成長率',
    unit: '%',
    min: 0,
    max: 1.0,
    step: 0.05,
    format: function(v: number) { return (v * 100).toFixed(0) + '%' },
  },
  {
    key: 'cogs_rate',
    label: '売上原価率',
    unit: '%',
    min: 0,
    max: 0.8,
    step: 0.05,
    format: function(v: number) { return (v * 100).toFixed(0) + '%' },
  },
]

var SGA_CATEGORIES = [
  {
    key: 'payroll',
    label: '人件費',
    color: 'bg-orange-500',
    ratio: 0.45,
    min: 0,
    max: 300_000_000,
    step: 5_000_000,
    format: function(v: number) { return (v / 10_000).toFixed(0) + '万円' },
  },
  {
    key: 'sga_marketing',
    label: 'マーケティング費',
    color: 'bg-purple-500',
    ratio: 0.20,
    min: 0,
    max: 200_000_000,
    step: 5_000_000,
    format: function(v: number) { return (v / 10_000).toFixed(0) + '万円' },
  },
  {
    key: 'sga_office',
    label: 'オフィス・管理費',
    color: 'bg-gray-500',
    ratio: 0.15,
    min: 0,
    max: 100_000_000,
    step: 1_000_000,
    format: function(v: number) { return (v / 10_000).toFixed(0) + '万円' },
  },
  {
    key: 'sga_system',
    label: 'システム・開発費',
    color: 'bg-cyan-500',
    ratio: 0.10,
    min: 0,
    max: 200_000_000,
    step: 5_000_000,
    format: function(v: number) { return (v / 10_000).toFixed(0) + '万円' },
  },
  {
    key: 'sga_other',
    label: 'その他販管費',
    color: 'bg-gray-400',
    ratio: 0.10,
    min: 0,
    max: 100_000_000,
    step: 1_000_000,
    format: function(v: number) { return (v / 10_000).toFixed(0) + '万円' },
  },
]

var MKTG_LABELS: Record<string, string> = {
  digital_ad: 'デジタル広告',
  offline_ad: 'オフライン広告',
  pr: 'PR・広報',
  events: 'イベント・展示会',
  branding: 'ブランディング',
  crm: 'CRM・リテンション',
  content: 'コンテンツ制作',
  other_mktg: 'その他マーケ費',
}

var MKTG_COLORS: Record<string, string> = {
  digital_ad: 'bg-purple-600',
  offline_ad: 'bg-purple-400',
  pr: 'bg-fuchsia-500',
  events: 'bg-pink-400',
  branding: 'bg-violet-400',
  crm: 'bg-indigo-400',
  content: 'bg-purple-300',
  other_mktg: 'bg-gray-300',
}

/** Multi-angle marketing categorization tags */
var MKTG_ANGLES: {
  key: string
  label: string
  groups: { label: string; keys: string[]; color: string }[]
}[] = [
  {
    key: 'directness',
    label: '直接 / 間接',
    groups: [
      { label: '直接（獲得）', keys: ['digital_ad', 'offline_ad', 'events', 'crm'], color: 'bg-rose-500' },
      { label: '間接（認知）', keys: ['pr', 'branding', 'content', 'other_mktg'], color: 'bg-sky-400' },
    ],
  },
  {
    key: 'purpose',
    label: '目的別',
    groups: [
      { label: '獲得', keys: ['digital_ad', 'offline_ad', 'events'], color: 'bg-red-500' },
      { label: 'ブランディング', keys: ['branding', 'pr', 'content'], color: 'bg-blue-500' },
      { label: 'CRM・リテンション', keys: ['crm', 'other_mktg'], color: 'bg-green-500' },
    ],
  },
  {
    key: 'medium',
    label: '手段別',
    groups: [
      { label: '広告', keys: ['digital_ad', 'offline_ad'], color: 'bg-purple-600' },
      { label: 'PR・広報', keys: ['pr'], color: 'bg-fuchsia-500' },
      { label: 'イベント', keys: ['events'], color: 'bg-pink-400' },
      { label: 'コンテンツ', keys: ['content', 'branding'], color: 'bg-violet-400' },
      { label: 'CRM・その他', keys: ['crm', 'other_mktg'], color: 'bg-indigo-400' },
    ],
  },
]

var CAPEX_DRIVERS = [
  {
    key: 'capex',
    label: 'CAPEX（年間）',
    unit: '円',
    min: 0,
    max: 200_000_000,
    step: 5_000_000,
    format: function(v: number) { return (v / 10_000).toFixed(0) + '万円' },
  },
]

var USEFUL_LIFE_OPTIONS = [
  { value: 3, label: '3年（ソフトウェア）' },
  { value: 5, label: '5年（IT機器）' },
  { value: 7, label: '7年（設備）' },
  { value: 10, label: '10年（建物附属）' },
]

function formatYen(v: number): string {
  if (Math.abs(v) >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(v) >= 10_000) return (v / 10_000).toFixed(0) + '万円'
  return v.toLocaleString() + '円'
}

function BenchmarkTooltip({ benchmark, driverKey }: { benchmark: DriverBenchmark; driverKey: string }) {
  var isRate = driverKey.includes('rate') || driverKey.includes('growth')
  var formatVal = function(v: number) {
    if (isRate) return (v * 100).toFixed(0) + '%'
    if (v >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
    return (v / 10_000).toFixed(0) + '万円'
  }

  return (
    <div className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg pointer-events-none">
      <div className="font-medium mb-1.5 text-blue-300">業界水準</div>
      <div className="space-y-1">
        <div className="flex justify-between">
          <span className="text-gray-400">低位:</span>
          <span>{formatVal(benchmark.low)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">中央:</span>
          <span className="text-blue-300 font-medium">{formatVal(benchmark.mid)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">高位:</span>
          <span>{formatVal(benchmark.high)}</span>
        </div>
      </div>
      <div className="mt-2 pt-1.5 border-t border-gray-700 text-gray-400 leading-tight">
        {benchmark.label}
      </div>
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
    </div>
  )
}

function BenchmarkBar({ benchmark, driver, value }: { benchmark: DriverBenchmark; driver: { min: number; max: number }; value: number }) {
  var range = driver.max - driver.min
  if (range <= 0) return null

  var lowPct = ((benchmark.low - driver.min) / range) * 100
  var highPct = ((benchmark.high - driver.min) / range) * 100
  var midPct = ((benchmark.mid - driver.min) / range) * 100

  // Clamp
  lowPct = Math.max(0, Math.min(100, lowPct))
  highPct = Math.max(0, Math.min(100, highPct))
  midPct = Math.max(0, Math.min(100, midPct))

  return (
    <div className="relative h-1.5 mt-0.5 mb-1">
      {/* Benchmark range bar */}
      <div
        className="absolute h-full bg-blue-200 rounded-full opacity-60"
        style={{ left: lowPct + '%', width: (highPct - lowPct) + '%' }}
      />
      {/* Mid marker */}
      <div
        className="absolute w-1.5 h-1.5 bg-blue-500 rounded-full -translate-x-1/2"
        style={{ left: midPct + '%' }}
      />
    </div>
  )
}

/** FY1-FY5 mini bar for a category */
function FYMiniBar({ values, color }: { values: number[]; color: string }) {
  if (!values || values.length < 5) return null
  var maxVal = Math.max(...values) || 1
  return (
    <div className="flex items-end gap-0.5 h-4">
      {values.map(function(v, i) {
        var pct = Math.max((v / maxVal) * 100, 4)
        return (
          <div key={i} className="flex-1 flex flex-col items-center">
            <div className={color + ' rounded-sm w-full transition-all'} style={{ height: pct + '%' }} title={'FY' + (i + 1) + ': ' + formatYen(v)} />
          </div>
        )
      })}
    </div>
  )
}

function FYRow({ values }: { values: number[] }) {
  if (!values || values.length < 5) return null
  return (
    <div className="flex gap-0.5 mt-1">
      {values.map(function(v, i) {
        return (
          <div key={i} className="flex-1 text-center">
            <div className="text-[8px] text-gray-400">{'FY' + (i + 1)}</div>
            <div className="text-[9px] font-mono text-gray-600">{formatYen(v)}</div>
          </div>
        )
      })}
    </div>
  )
}

/** Role-based payroll detail panel */
function PayrollDetailPanel({
  roles,
  parameters,
  onRoleChange,
}: {
  roles: Record<string, PayrollRoleDetail>
  parameters: Record<string, number>
  onRoleChange: (subKey: string, value: number) => void
}) {
  var roleEntries = Object.entries(roles)
  if (roleEntries.length === 0) return null

  return (
    <div className="mt-2 bg-orange-50 rounded-lg p-3 border border-orange-100">
      <div className="text-[11px] text-orange-700 font-medium mb-2">人件費内訳（平均年収 x 人数 = コスト）</div>
      <div className="space-y-2.5">
        {roleEntries.map(function([roleKey, role]) {
          var salaryKey = 'pr_' + roleKey + '_salary'
          var hcKey = 'pr_' + roleKey + '_hc'
          var localSalary = parameters[salaryKey] != null ? parameters[salaryKey] : role.salary
          var localHc = parameters[hcKey] != null ? parameters[hcKey] : (role.headcount[0] || 0)
          var fy1Cost = localSalary * localHc

          return (
            <div key={roleKey} className="bg-white rounded p-2 border border-orange-100">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-700">{role.label}</span>
                <span className="text-xs font-mono text-orange-700">{formatYen(fy1Cost)}/年</span>
              </div>
              {/* FY1-FY5 cost row */}
              <FYRow values={role.cost} />
              <div className="grid grid-cols-2 gap-2 mt-1.5">
                <div>
                  <label className="text-[10px] text-gray-500 block mb-0.5">平均年収</label>
                  <input
                    type="range"
                    min={3_000_000}
                    max={15_000_000}
                    step={500_000}
                    value={localSalary}
                    onChange={function(e) { onRoleChange(salaryKey, parseFloat(e.target.value)) }}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                  />
                  <div className="text-[10px] font-mono text-gray-600 text-center mt-0.5">
                    {(localSalary / 10_000).toFixed(0)}万円
                  </div>
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 block mb-0.5">FY1 人数</label>
                  <input
                    type="range"
                    min={0}
                    max={50}
                    step={1}
                    value={localHc}
                    onChange={function(e) { onRoleChange(hcKey, parseFloat(e.target.value)) }}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                  />
                  <div className="text-[10px] font-mono text-gray-600 text-center mt-0.5">
                    {localHc}人 → {role.headcount[4] || Math.round(localHc * 1.2 ** 4)}人(FY5)
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** Marketing subcategory detail panel with multi-angle categorization */
function MarketingDetailPanel({
  categories,
  total,
  parameters,
  onSubChange,
}: {
  categories: Record<string, number[]>
  total: number[]
  parameters: Record<string, number>
  onSubChange: (subKey: string, value: number) => void
}) {
  var catEntries = Object.entries(categories)

  // Compute local total from subcategory params (source of truth)
  var localTotal = 0
  catEntries.forEach(function([catKey, values]) {
    var localVal = parameters['mk_' + catKey]
    localTotal += (localVal != null ? localVal : (values[0] || 0))
  })

  // Compute angle-based grouping
  function getAngleData(angleIdx: number) {
    var angle = MKTG_ANGLES[angleIdx]
    if (!angle) return []
    return angle.groups.map(function(group) {
      var sum = 0
      group.keys.forEach(function(k) {
        var catVals = categories[k]
        if (catVals) {
          var localVal = parameters['mk_' + k]
          sum += (localVal != null ? localVal : (catVals[0] || 0))
        }
      })
      return { label: group.label, value: sum, color: group.color, keys: group.keys }
    })
  }

  return (
    <div className="mt-2 bg-purple-50 rounded-lg p-3 border border-purple-100">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] text-purple-700 font-medium">
          マーケティング費内訳（FY1）
          <span className="text-[10px] text-purple-500 ml-1">合計: {formatYen(localTotal)}</span>
        </div>
      </div>

      {/* FY1-FY5 summary */}
      <FYRow values={total} />

      {/* Multi-angle composition bars */}
      <div className="space-y-2 my-3">
        {MKTG_ANGLES.map(function(angle, ai) {
          var data = getAngleData(ai)
          var angleTotal = data.reduce(function(s, d) { return s + d.value }, 0) || 1
          return (
            <div key={angle.key}>
              <div className="text-[10px] text-gray-500 mb-0.5">{angle.label}</div>
              <div className="h-5 rounded-full overflow-hidden flex bg-gray-200">
                {data.map(function(d, di) {
                  var pct = (d.value / angleTotal) * 100
                  return (
                    <div
                      key={di}
                      className={d.color + ' transition-all relative group flex items-center justify-center'}
                      style={{ width: Math.max(pct, 2) + '%' }}
                    >
                      {pct > 15 && (
                        <span className="text-[9px] text-white font-medium truncate px-1">
                          {d.label}
                        </span>
                      )}
                      <div className="absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block">
                        <div className="bg-gray-900 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap shadow-lg">
                          {d.label}: {formatYen(d.value)} ({pct.toFixed(0)}%)
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="flex flex-wrap gap-x-2 mt-0.5">
                {data.map(function(d, di) {
                  var pct = (d.value / angleTotal) * 100
                  return (
                    <div key={di} className="flex items-center gap-0.5">
                      <div className={'w-1.5 h-1.5 rounded-full ' + d.color} />
                      <span className="text-[9px] text-gray-500">{d.label} {pct.toFixed(0)}%</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Per-category sliders */}
      <div className="border-t border-purple-200 pt-2">
        <div className="text-[10px] text-purple-600 font-medium mb-1.5">カテゴリ別予算配分</div>
        <div className="h-3 rounded-full overflow-hidden flex mb-2">
          {catEntries.map(function([catKey, values]) {
            var localVal = parameters['mk_' + catKey]
            var val = localVal != null ? localVal : (values[0] || 0)
            var pct = localTotal > 0 ? (val / localTotal) * 100 : 12.5
            return (
              <div
                key={catKey}
                className={(MKTG_COLORS[catKey] || 'bg-gray-300') + ' transition-all'}
                style={{ width: Math.max(pct, 1) + '%' }}
                title={(MKTG_LABELS[catKey] || catKey) + ': ' + formatYen(val)}
              />
            )
          })}
        </div>
        <div className="space-y-1.5">
          {catEntries.map(function([catKey, values]) {
            var localVal = parameters['mk_' + catKey]
            var val = localVal != null ? localVal : (values[0] || 0)
            return (
              <div key={catKey}>
                <div className="flex items-center justify-between mb-0.5">
                  <div className="flex items-center gap-1">
                    <div className={'w-1.5 h-1.5 rounded-full ' + (MKTG_COLORS[catKey] || 'bg-gray-300')} />
                    <label className="text-[11px] text-gray-700">{MKTG_LABELS[catKey] || catKey}</label>
                  </div>
                  <span className="text-[11px] font-mono text-gray-600">{formatYen(val)}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={50_000_000}
                  step={500_000}
                  value={val}
                  onChange={function(e) { onSubChange('mk_' + catKey, parseFloat(e.target.value)) }}
                  className="w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/** Helper: get current value for an SGA category */
function getCatVal(parameters: Record<string, number>, catKey: string, opexBase: number, ratio: number): number {
  return parameters[catKey] != null ? parameters[catKey] : opexBase * ratio
}

/** Helper: compute total payroll from role parameters */
function computePayrollTotal(parameters: Record<string, number>, roles?: Record<string, PayrollRoleDetail>): number {
  if (!roles) return parameters.payroll || 0
  var total = 0
  Object.entries(roles).forEach(function([roleKey, role]) {
    var salary = parameters['pr_' + roleKey + '_salary'] != null ? parameters['pr_' + roleKey + '_salary'] : role.salary
    var hc = parameters['pr_' + roleKey + '_hc'] != null ? parameters['pr_' + roleKey + '_hc'] : (role.headcount[0] || 0)
    total += salary * hc
  })
  return total
}

/** Helper: compute total marketing from subcategory parameters */
function computeMktgTotal(parameters: Record<string, number>, categories?: Record<string, number[]>): number {
  if (!categories) return parameters.sga_marketing || 0
  var total = 0
  Object.entries(categories).forEach(function([catKey, values]) {
    var localVal = parameters['mk_' + catKey]
    total += (localVal != null ? localVal : (values[0] || 0))
  })
  return total
}

export function DriverSliders({ parameters, onChange, onBatchChange, industry, sgaDetail, rdThemes, onRdThemesChange }: DriverSlidersProps) {
  var [hoveredDriver, setHoveredDriver] = useState<string | null>(null)
  var [sgaExpanded, setSgaExpanded] = useState(false)
  var [payrollExpanded, setPayrollExpanded] = useState(false)
  var [mktgExpanded, setMktgExpanded] = useState(false)
  var [rdExpanded, setRdExpanded] = useState(false)
  var [sgaMaterialized, setSgaMaterialized] = useState(false)
  var [deprMode, setDeprMode] = useState<'manual' | 'auto'>(
    parameters.depreciation_mode === 1 ? 'auto' : 'manual'
  )

  // Sync deprMode with parent parameters when depreciation_mode changes
  useEffect(function() {
    var newMode: 'manual' | 'auto' = parameters.depreciation_mode === 1 ? 'auto' : 'manual'
    setDeprMode(newMode)
  }, [parameters.depreciation_mode])

  var benchmarks = industry ? INDUSTRY_BENCHMARKS[industry]?.drivers : null

  var opexBase = parameters.opex_base || 80_000_000

  // Materialize SGA categories into explicit params on first expand
  // This breaks the circular dependency: opexBase*ratio ↔ sum of categories
  function materializeSgaCategories() {
    if (sgaMaterialized) return
    var needsBatch = false
    var batch: Record<string, number> = {}
    SGA_CATEGORIES.forEach(function(cat) {
      if (parameters[cat.key] == null) {
        batch[cat.key] = Math.round(opexBase * cat.ratio)
        needsBatch = true
      }
    })
    if (needsBatch && onBatchChange) {
      onBatchChange(batch)
    }
    setSgaMaterialized(true)
  }

  // Materialize payroll role params so sliders don't bounce on sgaDetail changes
  function materializePayrollRoles() {
    if (!sgaDetail) return
    var batch: Record<string, number> = {}
    var needsBatch = false
    Object.entries(sgaDetail.payroll.roles).forEach(function([roleKey, role]) {
      var salaryKey = 'pr_' + roleKey + '_salary'
      var hcKey = 'pr_' + roleKey + '_hc'
      if (parameters[salaryKey] == null) {
        batch[salaryKey] = role.salary
        needsBatch = true
      }
      if (parameters[hcKey] == null) {
        batch[hcKey] = role.headcount[0] || 0
        needsBatch = true
      }
    })
    if (needsBatch && onBatchChange) {
      onBatchChange(batch)
    }
  }

  // Materialize marketing subcategory params
  function materializeMktgCategories() {
    if (!sgaDetail) return
    var batch: Record<string, number> = {}
    var needsBatch = false
    Object.entries(sgaDetail.marketing.categories).forEach(function([catKey, values]) {
      var paramKey = 'mk_' + catKey
      if (parameters[paramKey] == null) {
        batch[paramKey] = values[0] || 0
        needsBatch = true
      }
    })
    if (needsBatch && onBatchChange) {
      onBatchChange(batch)
    }
  }

  // --- Batch helper: update multiple params + trigger recalc ---
  function batchUpdate(changes: Record<string, number>) {
    if (onBatchChange) {
      onBatchChange(changes)
    } else {
      Object.entries(changes).forEach(function([k, v]) { onChange(k, v) })
    }
  }

  // --- Top-down: OPEX total → distribute to categories proportionally ---
  function handleOpexTotalChange(newTotal: number) {
    var currentTotal = SGA_CATEGORIES.reduce(function(sum, c) {
      return sum + getCatVal(parameters, c.key, opexBase, c.ratio)
    }, 0)
    var ratio = currentTotal > 0 ? newTotal / currentTotal : 1
    var batch: Record<string, number> = { opex_base: newTotal }
    SGA_CATEGORIES.forEach(function(cat) {
      batch[cat.key] = Math.round(getCatVal(parameters, cat.key, opexBase, cat.ratio) * ratio)
    })
    batchUpdate(batch)
  }

  // --- Category slider → update that category + recompute opex_base as sum ---
  function handleCategoryChange(catKey: string, newVal: number) {
    var batch: Record<string, number> = {}
    batch[catKey] = newVal
    // Recompute opex_base from all categories
    var newOpex = SGA_CATEGORIES.reduce(function(sum, c) {
      return sum + (c.key === catKey ? newVal : getCatVal(parameters, c.key, opexBase, c.ratio))
    }, 0)
    batch.opex_base = newOpex

    // If marketing total slider changed, redistribute to subcategories proportionally
    if (catKey === 'sga_marketing' && sgaDetail) {
      var oldMktgTotal = computeMktgTotal(parameters, sgaDetail.marketing.categories)
      if (oldMktgTotal > 0) {
        var mktgRatio = newVal / oldMktgTotal
        Object.entries(sgaDetail.marketing.categories).forEach(function([subKey, values]) {
          var localVal = parameters['mk_' + subKey]
          var oldVal = localVal != null ? localVal : (values[0] || 0)
          batch['mk_' + subKey] = Math.round(oldVal * mktgRatio)
        })
      }
    }
    batchUpdate(batch)
  }

  // --- Marketing sub → update mk_* + sga_marketing total + opex_base ---
  function handleMktgSubChange(subParamKey: string, newVal: number) {
    var batch: Record<string, number> = {}
    batch[subParamKey] = newVal
    // Compute new marketing total
    var newMktgTotal = 0
    if (sgaDetail) {
      Object.entries(sgaDetail.marketing.categories).forEach(function([catKey, values]) {
        var paramKey = 'mk_' + catKey
        newMktgTotal += (paramKey === subParamKey ? newVal : (parameters[paramKey] != null ? parameters[paramKey] : (values[0] || 0)))
      })
    }
    batch.sga_marketing = newMktgTotal
    // Recompute opex_base
    batch.opex_base = SGA_CATEGORIES.reduce(function(sum, c) {
      return sum + (c.key === 'sga_marketing' ? newMktgTotal : getCatVal(parameters, c.key, opexBase, c.ratio))
    }, 0)
    batchUpdate(batch)
  }

  // --- Payroll role sub → update pr_* + payroll total + opex_base ---
  function handlePayrollSubChange(subParamKey: string, newVal: number) {
    var batch: Record<string, number> = {}
    batch[subParamKey] = newVal
    // Compute new payroll total from roles
    if (sgaDetail) {
      var newPayrollTotal = 0
      Object.entries(sgaDetail.payroll.roles).forEach(function([roleKey, role]) {
        var salaryKey = 'pr_' + roleKey + '_salary'
        var hcKey = 'pr_' + roleKey + '_hc'
        var salary = salaryKey === subParamKey ? newVal : (parameters[salaryKey] != null ? parameters[salaryKey] : role.salary)
        var hc = hcKey === subParamKey ? newVal : (parameters[hcKey] != null ? parameters[hcKey] : (role.headcount[0] || 0))
        newPayrollTotal += salary * hc
      })
      batch.payroll = newPayrollTotal
      // Recompute opex_base
      batch.opex_base = SGA_CATEGORIES.reduce(function(sum, c) {
        return sum + (c.key === 'payroll' ? newPayrollTotal : getCatVal(parameters, c.key, opexBase, c.ratio))
      }, 0)
    }
    batchUpdate(batch)
  }

  function handleDeprModeChange(mode: 'manual' | 'auto') {
    setDeprMode(mode)
    batchUpdate({ depreciation_mode: mode === 'auto' ? 1 : 0 } as any)
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-5 space-y-1">
      <h3 className="font-medium text-gray-900">ドライバー調整</h3>
      <p className="text-xs text-gray-500 pb-2">
        スライダーを動かすとPLがリアルタイムで変化します
        {benchmarks && <span className="text-blue-500 ml-1">(青帯=業界水準)</span>}
      </p>

      {/* Revenue Section */}
      <div className="pb-3 border-b border-gray-100">
        <div className="flex items-center gap-1.5 mb-3">
          <div className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">売上</span>
        </div>
        {REVENUE_DRIVERS.map(function(driver) {
          var value = parameters[driver.key] != null ? parameters[driver.key] : driver.min
          var benchmark = benchmarks ? benchmarks[driver.key as keyof typeof benchmarks] : null
          var isHovered = hoveredDriver === driver.key

          return (
            <div
              key={driver.key}
              className="relative mb-3"
              onMouseEnter={function() { setHoveredDriver(driver.key) }}
              onMouseLeave={function() { setHoveredDriver(null) }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <label className="text-sm text-gray-700">{driver.label}</label>
                  {benchmark && (
                    <span className="relative">
                      <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] cursor-help">
                        i
                      </span>
                      {isHovered && <BenchmarkTooltip benchmark={benchmark} driverKey={driver.key} />}
                    </span>
                  )}
                </div>
                <span className="text-sm font-mono font-medium text-gray-900">
                  {driver.format(value)}
                </span>
              </div>
              {benchmark && (
                <BenchmarkBar benchmark={benchmark} driver={driver} value={value} />
              )}
              <input
                type="range"
                min={driver.min}
                max={driver.max}
                step={driver.step}
                value={value}
                onChange={function(e) { onChange(driver.key, parseFloat(e.target.value)) }}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 touch-pan-x"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                <span>{driver.format(driver.min)}</span>
                <span>{driver.format(driver.max)}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* SGA Section */}
      <div className="py-3 border-b border-gray-100">
        <button
          onClick={function() {
            if (!sgaExpanded) materializeSgaCategories()
            setSgaExpanded(!sgaExpanded)
          }}
          className="w-full flex items-center justify-between mb-2"
        >
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-orange-500" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">販管費明細</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-gray-500">
              {(opexBase / 10_000).toFixed(0)}万円/年
            </span>
            <svg
              className={'w-4 h-4 text-gray-400 transition-transform ' + (sgaExpanded ? 'rotate-180' : '')}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>

        {!sgaExpanded && (
          /* Simple OPEX slider when collapsed — top-down distribution */
          <div className="mb-2">
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm text-gray-700">OPEX合計</label>
              <span className="text-sm font-mono font-medium text-gray-900">
                {(opexBase / 100_000_000).toFixed(1)}億円
              </span>
            </div>
            <input
              type="range"
              min={10_000_000}
              max={500_000_000}
              step={5_000_000}
              value={opexBase}
              onChange={function(e) { handleOpexTotalChange(parseFloat(e.target.value)) }}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>0.1億円</span>
              <span>5億円</span>
            </div>
            <p className="text-[10px] text-gray-400 mt-1">合計を変更すると各カテゴリに比例配分されます</p>
          </div>
        )}

        {sgaExpanded && (
          <div className="space-y-3">
            {/* Step 1: OPEX total (top-down entry point) */}
            <div className="bg-orange-50 rounded-lg p-2.5 border border-orange-100">
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-orange-800">販管費合計（OPEX）</label>
                <span className="text-sm font-mono font-bold text-orange-900">
                  {formatYen(opexBase)}
                </span>
              </div>
              <input
                type="range"
                min={10_000_000}
                max={500_000_000}
                step={5_000_000}
                value={opexBase}
                onChange={function(e) { handleOpexTotalChange(parseFloat(e.target.value)) }}
                className="w-full h-2 bg-orange-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
              />
              <p className="text-[10px] text-orange-500 mt-0.5">合計を変更すると下のカテゴリに比例配分されます</p>
            </div>

            {/* Step 2: Category composition bar */}
            <div className="h-3 rounded-full overflow-hidden flex">
              {SGA_CATEGORIES.map(function(cat) {
                var val = getCatVal(parameters, cat.key, opexBase, cat.ratio)
                var pct = opexBase > 0 ? (val / opexBase) * 100 : 20
                return (
                  <div
                    key={cat.key}
                    className={cat.color + ' transition-all'}
                    style={{ width: pct + '%' }}
                    title={cat.label + ': ' + cat.format(val) + ' (' + pct.toFixed(0) + '%)'}
                  />
                )
              })}
            </div>

            {/* Step 3: Category sliders (each updates parent total) */}
            {SGA_CATEGORIES.map(function(cat) {
              var value = getCatVal(parameters, cat.key, opexBase, cat.ratio)
              var isPayroll = cat.key === 'payroll'
              var isMktg = cat.key === 'sga_marketing'
              // FY1-FY5 data from sgaDetail
              var fyValues: number[] | null = null
              if (sgaDetail) {
                if (isPayroll) fyValues = sgaDetail.payroll.total
                else if (isMktg) fyValues = sgaDetail.marketing.total
                else if (cat.key === 'sga_office') fyValues = sgaDetail.office
                else if (cat.key === 'sga_system') fyValues = sgaDetail.system
                else if (cat.key === 'sga_other') fyValues = sgaDetail.other
              }
              var pct = opexBase > 0 ? ((value / opexBase) * 100).toFixed(0) : '—'

              return (
                <div key={cat.key}>
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-1.5">
                      <div className={'w-2 h-2 rounded-full ' + cat.color} />
                      <label className="text-sm text-gray-700">{cat.label}</label>
                      <span className="text-[10px] text-gray-400">{pct}%</span>
                      {isPayroll && sgaDetail && (
                        <button
                          onClick={function() {
                            if (!payrollExpanded) materializePayrollRoles()
                            setPayrollExpanded(!payrollExpanded)
                          }}
                          className="text-[10px] text-orange-500 hover:text-orange-700 ml-1"
                        >
                          {payrollExpanded ? '▲閉じる' : '▼詳細'}
                        </button>
                      )}
                      {isMktg && sgaDetail && (
                        <button
                          onClick={function() {
                            if (!mktgExpanded) materializeMktgCategories()
                            setMktgExpanded(!mktgExpanded)
                          }}
                          className="text-[10px] text-purple-500 hover:text-purple-700 ml-1"
                        >
                          {mktgExpanded ? '▲閉じる' : '▼詳細'}
                        </button>
                      )}
                      {cat.key === 'sga_system' && (
                        <button
                          onClick={function() { setRdExpanded(!rdExpanded) }}
                          className="text-[10px] text-cyan-500 hover:text-cyan-700 ml-1"
                        >
                          {rdExpanded ? '▲閉じる' : '▼詳細'}
                        </button>
                      )}
                    </div>
                    <span className="text-sm font-mono font-medium text-gray-900">
                      {cat.format(value)}
                    </span>
                  </div>
                  {/* FY1-FY5 mini bar */}
                  {fyValues && <FYMiniBar values={fyValues} color={cat.color} />}
                  <input
                    type="range"
                    min={cat.min}
                    max={cat.max}
                    step={cat.step}
                    value={value}
                    onChange={function(e) { handleCategoryChange(cat.key, parseFloat(e.target.value)) }}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                  />

                  {/* Payroll role-level detail → updates payroll total + opex */}
                  {isPayroll && payrollExpanded && sgaDetail && (
                    <PayrollDetailPanel
                      roles={sgaDetail.payroll.roles}
                      parameters={parameters}
                      onRoleChange={handlePayrollSubChange}
                    />
                  )}

                  {/* Marketing subcategory detail → updates sga_marketing total + opex */}
                  {isMktg && mktgExpanded && sgaDetail && (
                    <MarketingDetailPanel
                      categories={sgaDetail.marketing.categories}
                      total={sgaDetail.marketing.total}
                      parameters={parameters}
                      onSubChange={handleMktgSubChange}
                    />
                  )}

                  {/* R&D theme detail → editable categories, items, and amounts */}
                  {cat.key === 'sga_system' && rdExpanded && (
                    <RDThemeDetailPanel
                      themes={rdThemes || []}
                      onThemesChange={function(themes) {
                        // Sync sga_system total from R&D amounts
                        var total = 0
                        themes.forEach(function(t) {
                          if (t.amounts) t.amounts.forEach(function(a) { total += (a || 0) })
                        })
                        if (total > 0 && total !== value) {
                          handleCategoryChange(cat.key, total)
                        }
                        if (onRdThemesChange) onRdThemesChange(themes)
                      }}
                      systemTotal={value}
                    />
                  )}
                </div>
              )
            })}

            {/* OPEX growth rate (affects FY2-FY5) */}
            <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm text-gray-700">OPEX 年間増加率</label>
                <span className="text-sm font-mono font-medium text-gray-900">
                  {((parameters.opex_growth || 0.1) * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={0.5}
                step={0.05}
                value={parameters.opex_growth || 0.1}
                onChange={function(e) { onChange('opex_growth', parseFloat(e.target.value)) }}
                className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              />
              <p className="text-[10px] text-gray-400 mt-0.5">FY2〜FY5の各カテゴリに年率で適用されます</p>
            </div>
          </div>
        )}
      </div>

      {/* CAPEX & Depreciation Section */}
      <div className="pt-3">
        <div className="flex items-center gap-1.5 mb-3">
          <div className="w-2 h-2 rounded-full bg-slate-500" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">CAPEX・減価償却</span>
        </div>

        {/* CAPEX slider */}
        {CAPEX_DRIVERS.map(function(driver) {
          var value = parameters[driver.key] != null ? parameters[driver.key] : 0
          return (
            <div key={driver.key} className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm text-gray-700">{driver.label}</label>
                <span className="text-sm font-mono font-medium text-gray-900">
                  {driver.format(value)}
                </span>
              </div>
              <input
                type="range"
                min={driver.min}
                max={driver.max}
                step={driver.step}
                value={value}
                onChange={function(e) { onChange(driver.key, parseFloat(e.target.value)) }}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-slate-500"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                <span>{driver.format(driver.min)}</span>
                <span>{driver.format(driver.max)}</span>
              </div>
            </div>
          )
        })}

        {/* Depreciation mode toggle */}
        <div className="bg-gray-50 rounded-lg p-3 mt-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">減価償却費</span>
            <div className="flex bg-gray-200 rounded-md p-0.5">
              <button
                onClick={function() { handleDeprModeChange('manual') }}
                className={'px-2.5 py-1 text-[11px] rounded transition-colors ' + (
                  deprMode === 'manual'
                    ? 'bg-white text-gray-800 shadow-sm font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                )}
              >
                手動入力
              </button>
              <button
                onClick={function() { handleDeprModeChange('auto') }}
                className={'px-2.5 py-1 text-[11px] rounded transition-colors ' + (
                  deprMode === 'auto'
                    ? 'bg-white text-gray-800 shadow-sm font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                )}
              >
                CAPEX連動
              </button>
            </div>
          </div>

          {deprMode === 'manual' ? (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-gray-600">年間減価償却費</label>
                <span className="text-sm font-mono font-medium text-gray-900">
                  {((parameters.depreciation || 0) / 10_000).toFixed(0)}万円
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100_000_000}
                step={1_000_000}
                value={parameters.depreciation || 0}
                onChange={function(e) { onChange('depreciation', parseFloat(e.target.value)) }}
                className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-slate-500"
              />
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-[11px] text-gray-500">
                CAPEXを入力すると、耐用年数に応じて減価償却費が自動計算されます
              </p>
              <div>
                <label className="text-xs text-gray-600 block mb-1">耐用年数</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1">
                  {USEFUL_LIFE_OPTIONS.map(function(opt) {
                    var current = parameters.useful_life || 5
                    var isActive = current === opt.value
                    return (
                      <button
                        key={opt.value}
                        onClick={function() { onChange('useful_life', opt.value) }}
                        className={'px-2 py-1.5 text-[11px] rounded border transition-colors ' + (
                          isActive
                            ? 'border-slate-400 bg-slate-100 text-slate-800 font-medium'
                            : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
                        )}
                      >
                        {opt.value}年
                      </button>
                    )
                  })}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-600 block mb-1">償却方法</label>
                <div className="grid grid-cols-2 gap-1">
                  <button
                    onClick={function() { onChange('depreciation_method' as any, 0) }}
                    className={'px-2 py-1.5 text-[11px] rounded border transition-colors ' + (
                      (parameters.depreciation_method || 0) === 0
                        ? 'border-slate-400 bg-slate-100 text-slate-800 font-medium'
                        : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
                    )}
                  >
                    定額法
                  </button>
                  <button
                    onClick={function() { onChange('depreciation_method' as any, 1) }}
                    className={'px-2 py-1.5 text-[11px] rounded border transition-colors ' + (
                      (parameters.depreciation_method as any) === 1
                        ? 'border-slate-400 bg-slate-100 text-slate-800 font-medium'
                        : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
                    )}
                  >
                    定率法
                  </button>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-gray-600">既存資産の償却費</label>
                  <span className="text-xs font-mono text-gray-700">
                    {((parameters.existing_depreciation || 0) / 10_000).toFixed(0)}万円
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={50_000_000}
                  step={1_000_000}
                  value={parameters.existing_depreciation || 0}
                  onChange={function(e) { onChange('existing_depreciation', parseFloat(e.target.value)) }}
                  className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-slate-500"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
