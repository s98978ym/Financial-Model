/**
 * Q&A templates v2: Full data utilization
 */
import type { IndustryKey } from './industryBenchmarks'
import { INDUSTRY_BENCHMARKS } from './industryBenchmarks'

export type QACategory = 'revenue' | 'cost' | 'profitability' | 'growth' | 'risk' | 'market' | 'operations' | 'funding'
export type TargetAudience = 'investor' | 'banker' | 'board' | 'team' | 'partner'
export type DetailLevel = 'executive' | 'standard' | 'detailed'
export type AnswerLength = 'short' | 'medium' | 'long'

export interface QAItem {
  id: string
  category: QACategory
  question: string
  answer: string
  priority: number
  tags: string[]
}

export interface QASettings {
  target: TargetAudience
  detailLevel: DetailLevel
  answerLength: AnswerLength
  count: number
}

export var CATEGORY_INFO: Record<QACategory, { label: string; color: string; bgColor: string; borderColor: string; icon: string }> = {
  revenue: { label: '収益', color: 'text-blue-700', bgColor: 'bg-blue-50', borderColor: 'border-blue-200', icon: '📈' },
  cost: { label: 'コスト', color: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-200', icon: '💰' },
  profitability: { label: '収益性', color: 'text-green-700', bgColor: 'bg-green-50', borderColor: 'border-green-200', icon: '📊' },
  growth: { label: '成長性', color: 'text-purple-700', bgColor: 'bg-purple-50', borderColor: 'border-purple-200', icon: '🚀' },
  risk: { label: 'リスク', color: 'text-orange-700', bgColor: 'bg-orange-50', borderColor: 'border-orange-200', icon: '⚠️' },
  market: { label: '市場', color: 'text-cyan-700', bgColor: 'bg-cyan-50', borderColor: 'border-cyan-200', icon: '🌐' },
  operations: { label: 'オペレーション', color: 'text-amber-700', bgColor: 'bg-amber-50', borderColor: 'border-amber-200', icon: '⚙️' },
  funding: { label: '資金', color: 'text-indigo-700', bgColor: 'bg-indigo-50', borderColor: 'border-indigo-200', icon: '🏦' },
}

export var TARGET_OPTIONS: { key: TargetAudience; label: string; desc: string }[] = [
  { key: 'investor', label: '投資家', desc: 'VC・エンジェル投資家向け' },
  { key: 'banker', label: '銀行', desc: '融資審査・銀行員向け' },
  { key: 'board', label: '経営陣', desc: '取締役会・社内経営会議向け' },
  { key: 'team', label: 'チーム', desc: '社内メンバー・部門向け' },
  { key: 'partner', label: 'パートナー', desc: '提携先・外部ステークホルダー向け' },
]

export var DETAIL_OPTIONS: { key: DetailLevel; label: string; desc: string }[] = [
  { key: 'executive', label: 'エグゼクティブ', desc: '要点のみ。経営判断用' },
  { key: 'standard', label: 'スタンダード', desc: '根拠と数値を含む標準的な説明' },
  { key: 'detailed', label: '詳細', desc: '前提条件・計算根拠まで網羅' },
]

export var LENGTH_OPTIONS: { key: AnswerLength; label: string; desc: string; chars: string }[] = [
  { key: 'short', label: '短い', desc: '1-2文', chars: '50-100字' },
  { key: 'medium', label: '中程度', desc: '3-5文', chars: '150-300字' },
  { key: 'long', label: '長い', desc: 'パラグラフ', chars: '400-600字' },
]

export var COUNT_OPTIONS = [5, 10, 15, 20, 30]

function fmtYen(v: number): string {
  if (Math.abs(v) >= 100_000_000) return (v / 100_000_000).toFixed(1) + '億円'
  if (Math.abs(v) >= 10_000) return Math.round(v / 10_000).toLocaleString() + '万円'
  return v.toLocaleString() + '円'
}

function fmtPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

function fmtYear(i: number): string {
  return 'FY' + (i + 1)
}

export interface PLContext {
  parameters: Record<string, number>
  kpis?: {
    break_even_year?: string | null
    cumulative_break_even_year?: string | null
    revenue_cagr?: number
    fy5_op_margin?: number
    gp_margin?: number
    breakeven_gap?: { amount?: number; rate?: number } | null
  }
  plSummary?: {
    revenue: number[]
    cogs: number[]
    gross_profit: number[]
    opex: number[]
    operating_profit: number[]
    fcf: number[]
    cumulative_fcf: number[]
    depreciation?: number[]
    capex?: number[]
    segments?: { name: string; revenue: number[]; cogs: number[]; gross_profit: number[]; cogs_rate: number; growth_rate: number }[]
    sga_breakdown?: { payroll: number[]; marketing: number[]; office: number[]; system: number[]; other: number[] }
    sga_detail?: {
      payroll?: { roles?: Record<string, { salary?: number; headcount?: number[]; cost?: number[] }>; total?: number[] }
      marketing?: { categories?: Record<string, number[]>; total?: number[] }
    }
  }
  industry?: string
}

function findCrossover(series: number[]): number | null {
  for (var i = 1; i < series.length; i++) {
    if (series[i - 1] < 0 && series[i] >= 0) return i
  }
  return null
}

function devFromBench(value: number, b: { low: number; high: number }): string {
  if (value < b.low * 0.8) return 'below'
  if (value > b.high * 1.2) return 'aggressive'
  if (value > b.high) return 'above'
  return 'normal'
}

export function generateQA(ctx: PLContext, settings: QASettings): QAItem[] {
  var p = ctx.parameters
  var kpis = ctx.kpis
  var pl = ctx.plSummary
  var ik = (ctx.industry || 'その他') as IndustryKey
  var bench = INDUSTRY_BENCHMARKS[ik] || INDUSTRY_BENCHMARKS['その他']
  var sga = pl?.sga_breakdown
  var sgaDet = pl?.sga_detail
  var segs = pl?.segments

  var revFy1 = p.revenue_fy1 || 100_000_000
  var gr = p.growth_rate || 0.3
  var cr = p.cogs_rate || 0.3
  var opBase = p.opex_base || 80_000_000
  var opGr = p.opex_growth || 0.1
  var gm = 1 - cr
  var revFy5 = pl ? pl.revenue[4] : revFy1 * Math.pow(1 + gr, 4)
  var opFy5 = pl ? pl.operating_profit[4] : 0
  var cumFcf = pl ? pl.cumulative_fcf[4] : 0
  var brkEven = kpis?.break_even_year || null
  var cagr = kpis?.revenue_cagr || gr
  var opMarg = kpis?.fy5_op_margin || 0

  var gDev = devFromBench(gr, bench.drivers.growth_rate)
  var cDev = devFromBench(cr, bench.drivers.cogs_rate)
  var rDev = devFromBench(revFy1, bench.drivers.revenue_fy1)

  var opCross = pl ? findCrossover(pl.operating_profit) : null
  var fcfCross = pl ? findCrossover(pl.cumulative_fcf) : null

  var years = ['FY1', 'FY2', 'FY3', 'FY4', 'FY5']
  var isDet = settings.detailLevel === 'detailed'
  var tgt = settings.target

  var allQA: QAItem[] = []
  var idc = 0
  function add(cat: QACategory, q: string, a: string, pri: number, tags: string[]) {
    idc++
    allQA.push({ id: 'qa_' + idc, category: cat, question: q, answer: a, priority: pri, tags: tags })
  }

  // --- SGA totals ---
  var sgaT0 = sga ? (sga.payroll[0] + sga.marketing[0] + sga.office[0] + sga.system[0] + sga.other[0]) : opBase
  var sgaT4 = sga ? (sga.payroll[4] + sga.marketing[4] + sga.office[4] + sga.system[4] + sga.other[4]) : 0

  // ===== REVENUE =====
  var rbNote = rDev === 'aggressive' ? '業界上限を**大幅に超える強気**の設定です。' : rDev === 'below' ? '業界水準より**保守的**な設定です。' : '業界標準（' + bench.drivers.revenue_fy1.label + '）の範囲内です。'

  add('revenue', '初年度売上' + fmtYen(revFy1) + 'の根拠は？',
    '初年度売上 **' + fmtYen(revFy1) + '** を計画。' + rbNote +
    (isDet && segs && segs.length > 1 ? '\n\n**セグメント別：**\n' + segs.map(function(s) { return '- ' + s.name + '：' + fmtYen(s.revenue[0]) + '（原価率' + fmtPct(s.cogs_rate) + '）' }).join('\n') : ''),
    10, ['売上', '初年度'])

  if (pl) {
    add('revenue', '5年間の売上推移は？',
      '**' + fmtYen(pl.revenue[0]) + ' → ' + fmtYen(pl.revenue[4]) + '**（CAGR ' + fmtPct(cagr) + '）\n\n' +
      pl.revenue.map(function(r, i) {
        var yoy = i > 0 ? '（+' + fmtPct((r - pl!.revenue[i - 1]) / pl!.revenue[i - 1]) + '）' : ''
        return '- ' + years[i] + '：' + fmtYen(r) + ' ' + yoy
      }).join('\n'),
      9, ['売上', '5年推移'])
  }

  var gbNote = gDev === 'aggressive' ? '業界上限 ' + fmtPct(bench.drivers.growth_rate.high) + ' を**大幅超過**。達成には積極施策が必須。' : gDev === 'above' ? '業界上限に近い**挑戦的目標**。' : '業界標準（' + bench.drivers.growth_rate.label + '）の範囲内で**現実的**。'
  add('revenue', '年率' + fmtPct(gr) + '成長は実現可能か？',
    gbNote +
    (isDet ? '\n\n**根拠となる業界トレンド：**\n- **' + bench.trends[0].title + '**：' + bench.trends[0].plImpact.split('。')[0] + (bench.trends[1] ? '\n- **' + bench.trends[1].title + '**：' + bench.trends[1].plImpact.split('。')[0] : '') : ''),
    8, ['成長率', 'ベンチマーク'])

  // ===== COST =====
  var cbNote = cDev === 'below' ? '業界水準より**低い**（コスト優位）。' : cDev === 'above' || cDev === 'aggressive' ? '業界水準（' + bench.drivers.cogs_rate.label + '）より**高い**。改善余地あり。' : '業界標準内（' + bench.drivers.cogs_rate.label + '）。'
  add('cost', '原価率' + fmtPct(cr) + 'の妥当性は？',
    '原価率 **' + fmtPct(cr) + '**（粗利率 ' + fmtPct(gm) + '）。' + cbNote +
    (isDet && segs && segs.length > 1 ? '\n\n**セグメント別：**\n' + segs.map(function(s) { return '- ' + s.name + '：' + fmtPct(s.cogs_rate) }).join('\n') : ''),
    8, ['原価率', '粗利'])

  if (sga) {
    var pp = sgaT0 > 0 ? sga.payroll[0] / sgaT0 : 0
    var mp = sgaT0 > 0 ? sga.marketing[0] / sgaT0 : 0
    add('cost', '販管費' + fmtYen(sgaT0) + 'の内訳は？',
      '**内訳（初年度）：**\n' +
      '- 人件費：' + fmtYen(sga.payroll[0]) + '（' + fmtPct(pp) + '）\n' +
      '- マーケ：' + fmtYen(sga.marketing[0]) + '（' + fmtPct(mp) + '）\n' +
      '- オフィス：' + fmtYen(sga.office[0]) + '\n' +
      '- システム：' + fmtYen(sga.system[0]) + '\n' +
      '- その他：' + fmtYen(sga.other[0]) +
      (isDet ? '\n\nFY5合計 **' + fmtYen(sgaT4) + '**。売上成長率' + fmtPct(gr) + 'に対しOPEX増加率' + fmtPct(opGr) + 'でレバレッジが効く構造。' : ''),
      7, ['販管費', 'SGA'])
  } else {
    add('cost', '販管費の構成は？',
      '初年度 **' + fmtYen(opBase) + '**、年率' + fmtPct(opGr) + '増加。売上成長率との差が利益改善をドライブ。',
      7, ['販管費'])
  }

  if (sgaDet?.payroll?.roles) {
    var roles = sgaDet.payroll.roles
    var rk = Object.keys(roles)
    var hc0 = 0; var hc4 = 0
    rk.forEach(function(k) { var r = roles[k]; if (r.headcount) { hc0 += r.headcount[0] || 0; hc4 += r.headcount[4] || r.headcount[r.headcount.length - 1] || 0 } })
    add('cost', '人員計画は？',
      '**' + hc0 + '名 → ' + hc4 + '名**（5年間）\n\n' +
      rk.slice(0, 6).map(function(k) { var r = roles[k]; var h0 = r.headcount ? r.headcount[0] : 0; var h4 = r.headcount ? (r.headcount[4] || 0) : 0; return '- ' + k + '：' + h0 + ' → ' + h4 + '名' }).join('\n') +
      (isDet && hc0 > 0 ? '\n\n1人あたり売上：' + fmtYen(revFy1 / hc0) + ' → ' + fmtYen(revFy5 / hc4) + '（生産性向上）' : ''),
      6, ['人員', '採用'])
  } else {
    add('cost', '人件費と採用計画は？',
      '人件費は販管費の約60%（' + fmtYen(opBase * 0.6) + '）。約' + Math.round(opBase * 0.6 / 6_000_000) + '名体制でスタート。',
      6, ['人件費'])
  }

  // ===== PROFITABILITY =====
  var bea = brkEven ? '営業黒字化は **' + brkEven + '**。' : opCross !== null ? '営業利益は **' + fmtYear(opCross) + '** にプラス転換。' : '5年以内の黒字化は困難。成長投資フェーズ。'
  add('profitability', '黒字化の時期と条件は？',
    bea + (kpis?.breakeven_gap ? '追加必要売上 **' + fmtYen(kpis.breakeven_gap.amount || 0) + '**。' : '') +
    (isDet && pl ? '\n\n**営業利益推移：**\n' + pl.operating_profit.map(function(op, i) { return '- ' + years[i] + '：' + fmtYen(op) + (op >= 0 ? ' ✓' : '') }).join('\n') + '\n\n損益分岐売上：**' + fmtYen(opBase / gm) + '**' : ''),
    10, ['黒字化'])

  if (pl) {
    add('profitability', '営業利益率の改善見通しは？',
      'FY5営業利益率 **' + fmtPct(opMarg) + '**（' + fmtYen(opFy5) + '）\n\n' +
      pl.operating_profit.map(function(op, i) { var m = pl!.revenue[i] > 0 ? op / pl!.revenue[i] : 0; return '- ' + years[i] + '：' + fmtPct(m) }).join('\n') +
      (isDet && bench.competitors.length > 0 ? '\n\n**業界比較：**\n' + bench.competitors.slice(0, 3).map(function(c) { return '- ' + c.name + '：' + c.operatingProfit }).join('\n') : ''),
      9, ['営業利益率'])

    add('profitability', '累積FCFと投資回収は？',
      '5年累積FCF **' + fmtYen(cumFcf) + '**。' + (fcfCross !== null ? '累積黒字化は **' + fmtYear(fcfCross) + '**。' : cumFcf > 0 ? '投資回収済み。' : '回収に追加期間必要。') +
      (isDet ? '\n\n' + pl.fcf.map(function(f, i) { return '- ' + years[i] + '：' + fmtYen(f) + '（累積 ' + fmtYen(pl!.cumulative_fcf[i]) + '）' }).join('\n') : ''),
      8, ['FCF', '投資回収'])
  }

  // ===== GROWTH =====
  add('growth', ik + '業界における成長戦略は？',
    '**活用する業界トレンド：**\n' +
    bench.trends.slice(0, 3).map(function(t) { return '- **' + t.title + '**：' + t.plImpact.split('。')[0] }).join('\n') +
    (isDet && bench.competitionDetail ? '\n\n**KSF：** ' + bench.competitionDetail.ksf : ''),
    7, ['成長戦略', 'トレンド'])

  add('growth', 'スケーラビリティはあるか？',
    '売上成長 ' + fmtPct(gr) + ' vs コスト増加 ' + fmtPct(opGr) + '。**' + fmtPct(gr - opGr) + 'のスプレッド**でレバレッジが効く構造。' +
    (isDet && pl ? '\n\n**販管費率推移：**\n' + pl.revenue.map(function(r, i) { return '- ' + years[i] + '：' + fmtPct(pl!.opex[i] / r) }).join('\n') : ''),
    6, ['スケーラビリティ'])

  // ===== RISK =====
  add('risk', 'ダウンサイドシナリオは？',
    '**ワーストケース（売上-30%、コスト+15%）：**\n' +
    '- FY5売上：' + fmtYen(revFy5 * 0.7) + '\n' +
    '- FY5営業利益：' + fmtYen(opFy5 * 0.4) + '\n' +
    (isDet && bench.competitionDetail ? '\n**業界リスク：** ' + bench.competitionDetail.risks : '') +
    '\n\n売上20%減時点でコスト削減を発動する基準を設定。',
    8, ['ダウンサイド'])

  if (bench.competitors.length > 0 && ik !== 'その他') {
    add('risk', '競合との比較は？',
      bench.competitionDetail.marketStructure.split('。')[0] + '。\n\n**主要競合：**\n' +
      bench.competitors.slice(0, 4).map(function(c) { return '- **' + c.name + '**（' + c.revenue + '）：' + c.strengths }).join('\n') +
      (isDet ? '\n\n**参入障壁：** ' + bench.competitionDetail.entryBarriers.split('。')[0] : ''),
      7, ['競合', '差別化'])
  }

  add('risk', '主要リスクと緩和策は？',
    (bench.competitionDetail ? '**業界リスク：** ' + bench.competitionDetail.risks + '\n\n' : '') +
    '**緩和策：**\n- 収益多角化\n- バーンレート月次モニタリング\n- ' + bench.trends[0].title + 'への先行投資',
    6, ['リスク', '緩和策'])

  // ===== MARKET =====
  add('market', ik + '市場の構造は？',
    (bench.competitionDetail ? bench.competitionDetail.marketStructure : bench.competitiveEnvironment) +
    '\n\n**当社：** ' + bench.businessModel + '。初年度' + fmtYen(revFy1) + 'は市場の一部であり成長余地は十分。' +
    (isDet ? '\n\n**参入障壁：** ' + bench.competitionDetail.entryBarriers : ''),
    7, ['市場構造'])

  if (bench.kpis.length > 0) {
    add('market', '業界標準KPIとの比較は？',
      '**' + ik + '業界KPI：**\n\n' + bench.kpis.slice(0, 5).map(function(k) { return '- **' + k.label + '**：' + k.value + '　' + k.description }).join('\n'),
      5, ['KPI', '業界標準'])
  }

  if (bench.trends.length >= 3) {
    add('market', '業界トレンドのPLインパクトは？',
      bench.trends.slice(0, 4).map(function(t) { return '- **' + t.title + '**\n  ' + t.summary.split('。')[0] + '\n  → ' + t.plImpact.split('。')[0] }).join('\n\n'),
      6, ['トレンド', 'PLインパクト'])
  }

  // ===== OPERATIONS =====
  if (sga?.marketing) {
    add('operations', 'マーケティング投資計画は？',
      '初年度 **' + fmtYen(sga.marketing[0]) + '**（売上比' + fmtPct(sga.marketing[0] / revFy1) + '）\n\n' +
      sga.marketing.map(function(m, i) { var rev = pl ? pl.revenue[i] : revFy1 * Math.pow(1 + gr, i); return '- ' + years[i] + '：' + fmtYen(m) + '（売上比' + fmtPct(m / rev) + '）' }).join('\n'),
      5, ['マーケティング'])
  }

  add('operations', 'KPIモニタリング体制は？',
    '**財務KPI：** 売上成長率' + fmtPct(gr) + '、粗利率' + fmtPct(gm) + '、営業利益率（FY5: ' + fmtPct(opMarg) + '）\n\n' +
    '**事業KPI（' + ik + '）：**\n' + bench.kpis.slice(0, 3).map(function(k) { return '- ' + k.label + '（目標：' + k.value + '）' }).join('\n'),
    5, ['KPI', 'モニタリング'])

  // ===== FUNDING =====
  if (tgt === 'investor' || tgt === 'banker') {
    add('funding', '資金の使途とROIは？',
      '**配分計画：**\n' +
      (sga ? '- 人材：' + fmtYen(sga.payroll[0]) + '\n- マーケ：' + fmtYen(sga.marketing[0]) + '\n- システム：' + fmtYen(sga.system[0]) + '\n- その他：' + fmtYen(sga.office[0] + sga.other[0]) : '- プロダクト開発 40%\n- マーケティング 30%\n- 組織構築 20%\n- 運転資金 10%') +
      '\n\n→ ' + fmtPct(gr) + '成長を実現し' + (brkEven || 'FY4-5') + 'で黒字化。',
      9, ['資金調達', 'ROI'])

    add('funding', 'バリュエーションは？',
      'FY5売上 **' + fmtYen(revFy5) + '**・利益率 **' + fmtPct(opMarg) + '** ベースで、' +
      (ik === 'SaaS' ? 'ARR 8-12x → **' + fmtYen(revFy5 * 10) + '**' : 'EV/売上 3-5x → **' + fmtYen(revFy5 * 4) + '**') + ' の企業価値。' +
      (isDet && bench.competitors.length > 0 ? '\n\n**参考：**\n' + bench.competitors.slice(0, 3).map(function(c) { return '- ' + c.name + '：' + c.revenue }).join('\n') : ''),
      8, ['バリュエーション'])

    add('funding', 'ランウェイは？',
      '月次バーンレート約 **' + fmtYen(opBase / 12) + '**。' +
      (cumFcf > 0 ? '自走可能。' : '十分なランウェイ確保の上で成長投資、マイルストーン達成後に次ラウンド。') +
      (isDet && pl ? '\n\n' + pl.fcf.map(function(f, i) { return '- ' + years[i] + '：' + fmtYen(f) }).join('\n') : ''),
      7, ['ランウェイ'])
  }

  // ===== DYNAMIC: data anomalies =====
  if (gDev === 'aggressive') {
    add('risk', '業界水準超の成長率をどう正当化するか？',
      '計画 ' + fmtPct(gr) + ' は業界上限 ' + fmtPct(bench.drivers.growth_rate.high) + ' 超。\n\n**根拠：**\n- 未開拓セグメント先行参入\n- ' + bench.trends[0].title + 'による市場拡大\n- ダウンサイド（業界平均' + fmtPct(bench.drivers.growth_rate.mid) + '）でも継続可能',
      9, ['成長率', '正当化'])
  }
  if (cDev === 'below') {
    add('cost', '低原価率' + fmtPct(cr) + 'の実現方法は？',
      '業界平均' + fmtPct(bench.drivers.cogs_rate.mid) + '対し **' + fmtPct(cr) + '**。\n\n**要因：**\n- テクノロジー活用による自動化\n- スケールメリット\n- 高付加価値セグメント集中',
      7, ['原価率', 'コスト優位'])
  }
  if (pl?.capex) {
    var totalCx = pl.capex.reduce(function(s, v) { return s + v }, 0)
    if (totalCx > 0) {
      add('cost', '設備投資と減価償却は？',
        '5年累計CAPEX **' + fmtYen(totalCx) + '**\n\n' + pl.capex.map(function(c, i) { return '- ' + years[i] + '：' + fmtYen(c) + ' / 償却' + fmtYen(pl!.depreciation ? pl!.depreciation[i] : 0) }).join('\n'),
        5, ['CAPEX'])
    }
  }

  // ===== PRIORITY ADJUSTMENT =====
  allQA.forEach(function(qa) {
    if (tgt === 'investor' && (qa.category === 'funding' || qa.category === 'growth' || qa.category === 'market')) qa.priority += 2
    if (tgt === 'banker' && (qa.category === 'risk' || qa.category === 'funding' || qa.category === 'profitability')) qa.priority += 2
    if (tgt === 'board' && (qa.category === 'profitability' || qa.category === 'operations')) qa.priority += 2
    if (tgt === 'team' && (qa.category === 'operations' || qa.category === 'growth')) qa.priority += 2
    if (tgt === 'partner' && (qa.category === 'market' || qa.category === 'growth')) qa.priority += 2
  })

  allQA.sort(function(a, b) { return b.priority - a.priority })

  // ===== LENGTH TRIM =====
  if (settings.answerLength === 'short') {
    allQA.forEach(function(qa) {
      var first = qa.answer.split('\n\n')[0]
      qa.answer = first.replace(/\*\*/g, '').replace(/^- /gm, '').split('\n')[0]
    })
  } else if (settings.answerLength === 'medium') {
    allQA.forEach(function(qa) {
      qa.answer = qa.answer.split('\n\n').slice(0, 2).join('\n\n')
    })
  }

  return allQA.slice(0, settings.count)
}
