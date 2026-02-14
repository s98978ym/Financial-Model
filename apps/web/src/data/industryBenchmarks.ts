/**
 * Industry benchmark data for Scenario Playground.
 *
 * Provides typical parameter ranges by industry and scale,
 * plus key KPIs for reference.
 * Source: industry.py definitions + standard financial benchmarks.
 */

export type IndustryKey =
  | 'SaaS'
  | '教育'
  | '人材'
  | 'EC'
  | '小売'
  | '飲食'
  | 'メーカー'
  | 'ヘルスケア'
  | 'その他'

export type ScaleKey = 'seed' | 'early' | 'growth' | 'mature'

export interface DriverBenchmark {
  /** Typical low end */
  low: number
  /** Typical midpoint */
  mid: number
  /** Typical high end */
  high: number
  /** Display label */
  label: string
}

export interface IndustryKPI {
  key: string
  label: string
  value: string
  description: string
}

export interface IndustryInfo {
  label: string
  description: string
  /** Benchmark ranges for the 5 main drivers */
  drivers: {
    revenue_fy1: DriverBenchmark
    growth_rate: DriverBenchmark
    cogs_rate: DriverBenchmark
    opex_base: DriverBenchmark
    opex_growth: DriverBenchmark
  }
  /** Industry-specific KPIs for reference */
  kpis: IndustryKPI[]
  /** Typical business model */
  businessModel: string
}

export const SCALE_LABELS: Record<ScaleKey, string> = {
  seed: 'シード期',
  early: 'アーリー期',
  growth: 'グロース期',
  mature: '成熟期',
}

export const SCALE_REVENUE_MULTIPLIERS: Record<ScaleKey, number> = {
  seed: 0.3,
  early: 1.0,
  growth: 3.0,
  mature: 5.0,
}

export const INDUSTRY_BENCHMARKS: Record<IndustryKey, IndustryInfo> = {
  SaaS: {
    label: 'SaaS',
    description: 'クラウドベースのサブスクリプション型ソフトウェア事業',
    drivers: {
      revenue_fy1: { low: 30_000_000, mid: 100_000_000, high: 500_000_000, label: 'ARR 0.3〜5億円' },
      growth_rate: { low: 0.2, mid: 0.5, high: 1.0, label: 'T2D3基準: 年50-100%成長' },
      cogs_rate: { low: 0.15, mid: 0.25, high: 0.35, label: 'サーバー+CS費用: 15-35%' },
      opex_base: { low: 50_000_000, mid: 120_000_000, high: 300_000_000, label: '人件費+マーケ: 0.5〜3億円' },
      opex_growth: { low: 0.1, mid: 0.2, high: 0.4, label: '採用拡大ペース: 10-40%' },
    },
    kpis: [
      { key: 'ltv_cac', label: 'LTV/CAC比率', value: '3x以上', description: '顧客生涯価値÷獲得コスト。3x以上が健全' },
      { key: 'nrr', label: 'NRR', value: '110-130%', description: 'ネットレベニューリテンション。既存顧客からの売上維持・拡大率' },
      { key: 'churn', label: '月次チャーン', value: '1-3%', description: '月次解約率。SMBで3-5%、エンタープライズで0.5-1%' },
      { key: 'magic_number', label: 'マジックナンバー', value: '0.75以上', description: '営業効率指標。新規ARR÷前期S&M費用' },
      { key: 'rule_of_40', label: 'Rule of 40', value: '40%以上', description: '成長率+利益率。40%以上が優良SaaS' },
      { key: 'payback', label: 'CAC回収期間', value: '12-18ヶ月', description: '顧客獲得コストの回収にかかる期間' },
    ],
    businessModel: 'B2B / B2C サブスクリプション',
  },

  教育: {
    label: '教育',
    description: '学校・塾・オンライン教育・EdTech事業',
    drivers: {
      revenue_fy1: { low: 20_000_000, mid: 80_000_000, high: 300_000_000, label: '生徒数×受講料: 0.2〜3億円' },
      growth_rate: { low: 0.1, mid: 0.2, high: 0.4, label: '安定成長: 10-40%' },
      cogs_rate: { low: 0.3, mid: 0.45, high: 0.6, label: '講師人件費中心: 30-60%' },
      opex_base: { low: 30_000_000, mid: 60_000_000, high: 150_000_000, label: '施設+管理費: 0.3〜1.5億円' },
      opex_growth: { low: 0.05, mid: 0.1, high: 0.2, label: '施設拡張ペース: 5-20%' },
    },
    kpis: [
      { key: 'retention', label: '継続率', value: '80-95%', description: '生徒の年次継続率。高いほど安定収益' },
      { key: 'students_per_teacher', label: '生徒/講師比', value: '15-30人', description: '講師1人あたり生徒数。効率の指標' },
      { key: 'completion', label: '修了率', value: '60-85%', description: 'コース修了率。品質の指標' },
      { key: 'tuition', label: '年間授業料', value: '30-120万円', description: '生徒1人あたり年間受講料' },
    ],
    businessModel: 'B2C / B2B2C',
  },

  人材: {
    label: '人材',
    description: '人材紹介・派遣・HR Tech事業',
    drivers: {
      revenue_fy1: { low: 30_000_000, mid: 100_000_000, high: 500_000_000, label: '成約数×手数料: 0.3〜5億円' },
      growth_rate: { low: 0.15, mid: 0.3, high: 0.6, label: '市場連動: 15-60%' },
      cogs_rate: { low: 0.05, mid: 0.15, high: 0.3, label: 'DB・ツール費用: 5-30%' },
      opex_base: { low: 40_000_000, mid: 80_000_000, high: 200_000_000, label: 'コンサルタント人件費: 0.4〜2億円' },
      opex_growth: { low: 0.1, mid: 0.15, high: 0.3, label: '採用拡大: 10-30%' },
    },
    kpis: [
      { key: 'fee_rate', label: '手数料率', value: '25-35%', description: '想定年収に対する紹介手数料率' },
      { key: 'conversion', label: '成約率', value: '5-15%', description: '候補者紹介→内定承諾の転換率' },
      { key: 'productivity', label: '1人あたり売上', value: '2,000-5,000万円', description: 'コンサルタント1人あたり年間売上' },
      { key: 'time_to_fill', label: '充足期間', value: '30-60日', description: '求人開始から成約までの平均日数' },
    ],
    businessModel: 'B2B (成功報酬型)',
  },

  EC: {
    label: 'EC',
    description: 'ECサイト・マーケットプレイス・D2C事業',
    drivers: {
      revenue_fy1: { low: 50_000_000, mid: 200_000_000, high: 1_000_000_000, label: 'GMV/売上: 0.5〜10億円' },
      growth_rate: { low: 0.15, mid: 0.3, high: 0.8, label: 'EC市場成長率+α: 15-80%' },
      cogs_rate: { low: 0.4, mid: 0.55, high: 0.7, label: '商品原価+物流: 40-70%' },
      opex_base: { low: 30_000_000, mid: 80_000_000, high: 250_000_000, label: 'マーケ+管理: 0.3〜2.5億円' },
      opex_growth: { low: 0.05, mid: 0.15, high: 0.3, label: '広告費拡大: 5-30%' },
    },
    kpis: [
      { key: 'aov', label: '平均注文単価', value: '3,000-15,000円', description: '1注文あたり平均金額 (AOV)' },
      { key: 'repeat_rate', label: 'リピート率', value: '20-40%', description: '既存顧客の再購入率' },
      { key: 'cac', label: 'CAC', value: '1,000-5,000円', description: '新規顧客獲得コスト' },
      { key: 'take_rate', label: 'テイクレート', value: '10-25%', description: 'マーケットプレイスの手数料率' },
    ],
    businessModel: 'B2C / マーケットプレイス',
  },

  小売: {
    label: '小売',
    description: '実店舗小売・チェーン展開事業',
    drivers: {
      revenue_fy1: { low: 50_000_000, mid: 200_000_000, high: 1_000_000_000, label: '店舗数×店舗売上: 0.5〜10億円' },
      growth_rate: { low: 0.05, mid: 0.15, high: 0.3, label: '出店ペース依存: 5-30%' },
      cogs_rate: { low: 0.5, mid: 0.6, high: 0.75, label: '商品仕入: 50-75%' },
      opex_base: { low: 40_000_000, mid: 100_000_000, high: 300_000_000, label: '賃料+人件費: 0.4〜3億円' },
      opex_growth: { low: 0.05, mid: 0.1, high: 0.2, label: '出店拡大: 5-20%' },
    },
    kpis: [
      { key: 'revenue_per_store', label: '店舗あたり売上', value: '3,000-8,000万円/年', description: '1店舗あたりの年間売上' },
      { key: 'basket', label: '客単価', value: '1,500-5,000円', description: '1会計あたり購入金額' },
      { key: 'inventory_turn', label: '在庫回転率', value: '6-12回/年', description: '年間の在庫回転回数。高いほど効率的' },
      { key: 'rent_ratio', label: '賃料比率', value: '8-15%', description: '売上に対する賃料の比率' },
    ],
    businessModel: 'B2C (店舗型)',
  },

  飲食: {
    label: '飲食',
    description: 'レストラン・カフェ・フードデリバリー事業',
    drivers: {
      revenue_fy1: { low: 30_000_000, mid: 100_000_000, high: 500_000_000, label: '席数×回転×単価: 0.3〜5億円' },
      growth_rate: { low: 0.05, mid: 0.15, high: 0.3, label: '出店ペース: 5-30%' },
      cogs_rate: { low: 0.28, mid: 0.35, high: 0.45, label: '食材原価 (FL比率): 28-45%' },
      opex_base: { low: 30_000_000, mid: 70_000_000, high: 200_000_000, label: '人件費+賃料: 0.3〜2億円' },
      opex_growth: { low: 0.05, mid: 0.1, high: 0.2, label: '出店拡大: 5-20%' },
    },
    kpis: [
      { key: 'fl_ratio', label: 'FL比率', value: '55-65%', description: 'Food + Labor コスト。60%以下が目標' },
      { key: 'turnover', label: '回転率', value: '1.5-3.0回/日', description: '座席1日あたりの回転数' },
      { key: 'check_avg', label: '客単価', value: '800-5,000円', description: '1人あたりの平均支払額' },
      { key: 'occupancy', label: '座席稼働率', value: '60-85%', description: '座席の稼働率。ランチ・ディナーで異なる' },
    ],
    businessModel: 'B2C (店舗型)',
  },

  メーカー: {
    label: 'メーカー',
    description: '製造業・ハードウェア・消費財事業',
    drivers: {
      revenue_fy1: { low: 100_000_000, mid: 500_000_000, high: 2_000_000_000, label: '生産数×単価: 1〜20億円' },
      growth_rate: { low: 0.05, mid: 0.1, high: 0.25, label: '設備投資連動: 5-25%' },
      cogs_rate: { low: 0.5, mid: 0.65, high: 0.8, label: '原材料+製造: 50-80%' },
      opex_base: { low: 50_000_000, mid: 150_000_000, high: 500_000_000, label: '管理+開発: 0.5〜5億円' },
      opex_growth: { low: 0.03, mid: 0.08, high: 0.15, label: '安定成長: 3-15%' },
    },
    kpis: [
      { key: 'yield', label: '歩留まり率', value: '90-99%', description: '良品率。95%以上が一般的な目標' },
      { key: 'utilization', label: '設備稼働率', value: '70-90%', description: '設備の稼働率。高いほど効率的' },
      { key: 'inventory_months', label: '在庫月数', value: '1-3ヶ月', description: '在庫の月数。短いほど効率的' },
      { key: 'gross_margin', label: '粗利率', value: '20-50%', description: '業種により大きく異なる' },
    ],
    businessModel: 'B2B / B2C',
  },

  ヘルスケア: {
    label: 'ヘルスケア',
    description: '医療・ヘルステック・ウェルネス事業',
    drivers: {
      revenue_fy1: { low: 30_000_000, mid: 150_000_000, high: 800_000_000, label: '患者数×単価: 0.3〜8億円' },
      growth_rate: { low: 0.1, mid: 0.25, high: 0.5, label: '規制・認可依存: 10-50%' },
      cogs_rate: { low: 0.2, mid: 0.35, high: 0.5, label: '機器・薬剤: 20-50%' },
      opex_base: { low: 50_000_000, mid: 120_000_000, high: 400_000_000, label: '専門人材+R&D: 0.5〜4億円' },
      opex_growth: { low: 0.05, mid: 0.15, high: 0.3, label: 'R&D拡大: 5-30%' },
    },
    kpis: [
      { key: 'patients', label: '患者/利用者数', value: '1,000-10,000人', description: '月間アクティブ患者・利用者数' },
      { key: 'arpu', label: '患者単価', value: '5,000-50,000円/月', description: '患者1人あたり月額収入' },
      { key: 'rd_ratio', label: 'R&D比率', value: '15-30%', description: '売上に対する研究開発費の比率' },
      { key: 'regulatory', label: '許認可コスト', value: '500-5,000万円', description: '薬事・認可取得にかかる費用' },
    ],
    businessModel: 'B2C / B2B2C',
  },

  その他: {
    label: 'その他',
    description: '一般的な事業モデル',
    drivers: {
      revenue_fy1: { low: 30_000_000, mid: 100_000_000, high: 500_000_000, label: '業種により異なる: 0.3〜5億円' },
      growth_rate: { low: 0.1, mid: 0.2, high: 0.5, label: '一般的: 10-50%' },
      cogs_rate: { low: 0.2, mid: 0.4, high: 0.65, label: '業種により異なる: 20-65%' },
      opex_base: { low: 30_000_000, mid: 80_000_000, high: 200_000_000, label: '人件費+管理費: 0.3〜2億円' },
      opex_growth: { low: 0.05, mid: 0.1, high: 0.25, label: '一般的: 5-25%' },
    },
    kpis: [
      { key: 'gross_margin', label: '粗利率', value: '30-60%', description: '売上総利益率。業種平均は40-50%' },
      { key: 'op_margin', label: '営業利益率', value: '5-20%', description: '営業利益率。10%以上が健全' },
      { key: 'burn_rate', label: 'バーンレート', value: '500-3,000万円/月', description: '月間キャッシュ消費額' },
      { key: 'runway', label: 'ランウェイ', value: '12-24ヶ月', description: '現金が持続する月数' },
    ],
    businessModel: '多様',
  },
}

/** All available industry keys */
export const INDUSTRY_KEYS: IndustryKey[] = [
  'SaaS', '教育', '人材', 'EC', '小売', '飲食', 'メーカー', 'ヘルスケア', 'その他',
]

/** Detect industry from project name or Phase 5 data */
export function detectIndustry(projectName?: string, phase5Data?: any): IndustryKey {
  if (!projectName && !phase5Data) return 'その他'

  const text = [
    projectName || '',
    phase5Data?.industry || '',
    phase5Data?.business_model || '',
    JSON.stringify(phase5Data?.extractions?.slice(0, 5) || []),
  ].join(' ').toLowerCase()

  const patterns: [IndustryKey, string[]][] = [
    ['SaaS', ['saas', 'サブスク', 'mrr', 'arr', 'churn', 'subscription', 'クラウド']],
    ['教育', ['教育', '学校', '塾', 'edtech', '受講', '生徒', '講座']],
    ['人材', ['人材', '採用', '紹介', 'hr', 'staffing', 'recruiting', '求人']],
    ['EC', ['ec', 'ecommerce', 'コマース', 'マーケットプレイス', 'd2c', '通販', 'ショッピング']],
    ['小売', ['小売', 'リテール', 'retail', '店舗', 'ストア']],
    ['飲食', ['飲食', 'レストラン', 'カフェ', 'フード', '食', 'restaurant']],
    ['メーカー', ['メーカー', '製造', 'manufacturing', '工場', '生産', 'ハードウェア']],
    ['ヘルスケア', ['ヘルスケア', '医療', 'health', 'クリニック', '患者', '薬']],
  ]

  for (var i = 0; i < patterns.length; i++) {
    var industry = patterns[i][0]
    var keywords = patterns[i][1]
    for (var j = 0; j < keywords.length; j++) {
      if (text.indexOf(keywords[j]) !== -1) {
        return industry
      }
    }
  }

  return 'その他'
}
