/**
 * Q&A templates for financial model presentation.
 * Generates categorized Q&A from PL model parameters and results.
 */

export type QACategory =
  | 'revenue'
  | 'cost'
  | 'profitability'
  | 'growth'
  | 'risk'
  | 'market'
  | 'operations'
  | 'funding'

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

interface PLContext {
  parameters: Record<string, number>
  kpis?: {
    break_even_year?: string | null
    revenue_cagr?: number
    fy5_op_margin?: number
  }
  plSummary?: {
    revenue: number[]
    cogs: number[]
    gross_profit: number[]
    opex: number[]
    operating_profit: number[]
    fcf: number[]
    cumulative_fcf: number[]
  }
  industry?: string
}

/**
 * Generate Q&A items from PL model data.
 */
export function generateQA(
  ctx: PLContext,
  settings: QASettings,
): QAItem[] {
  var params = ctx.parameters
  var kpis = ctx.kpis
  var pl = ctx.plSummary
  var industry = ctx.industry || 'その他'

  var revFy1 = params.revenue_fy1 || 100_000_000
  var growthRate = params.growth_rate || 0.3
  var cogsRate = params.cogs_rate || 0.3
  var opexBase = params.opex_base || 80_000_000
  var opexGrowth = params.opex_growth || 0.1
  var grossMargin = 1 - cogsRate
  var revFy5 = pl ? pl.revenue[4] : revFy1 * Math.pow(1 + growthRate, 4)
  var opFy5 = pl ? pl.operating_profit[4] : 0
  var cumFcf = pl ? pl.cumulative_fcf[4] : 0
  var breakEven = kpis ? kpis.break_even_year : null
  var cagr = kpis ? kpis.revenue_cagr : growthRate
  var opMargin = kpis ? kpis.fy5_op_margin : 0

  var isInvestor = settings.target === 'investor'
  var isBanker = settings.target === 'banker'
  var isBoard = settings.target === 'board'
  var isDetailed = settings.detailLevel === 'detailed'
  var isExecutive = settings.detailLevel === 'executive'

  // Build all possible Q&A items
  var allQA: QAItem[] = []
  var idCounter = 0
  function addQA(cat: QACategory, q: string, a: string, priority: number, tags: string[]) {
    idCounter++
    allQA.push({ id: 'qa_' + idCounter, category: cat, question: q, answer: a, priority: priority, tags: tags })
  }

  // === Revenue Questions ===
  addQA('revenue', '初年度の売上見通しとその根拠は？',
    '初年度売上は' + fmtYen(revFy1) + 'を見込んでいます。' +
    (industry !== 'その他' ? industry + '業界の市場規模とターゲットセグメントの規模から算出しており、' : '') +
    '保守的な前提のもとで設定しています。' +
    (isDetailed ? '売上構成は既存顧客からの安定収入と新規顧客獲得によるものです。' : ''),
    10, ['売上', '初年度'])

  addQA('revenue', '5年後の売上はどの程度まで成長する想定ですか？',
    'FY5の売上は' + fmtYen(revFy5) + 'を目標としています。年率' + fmtPct(growthRate) + 'の成長を前提としており、' +
    '5年間のCAGRは' + fmtPct(cagr || growthRate) + 'です。' +
    (isDetailed ? 'この成長率は' + industry + '業界の成長トレンドと当社の競争優位性を踏まえた設定です。' : ''),
    9, ['売上', 'FY5', '成長'])

  addQA('revenue', '売上成長率' + fmtPct(growthRate) + 'の実現可能性は？',
    '年率' + fmtPct(growthRate) + 'の成長見通しは、' + industry + '業界の市場成長率と当社の事業計画に基づいています。' +
    (isDetailed ? '初期は高い成長率が見込まれますが、規模拡大に伴い成長率は逓減する可能性があります。ベストケースでは+20%上振れ、ワーストケースでは-20%下振れも想定しています。' : ''),
    8, ['成長率', '実現性'])

  addQA('revenue', '売上の季節変動やリスク要因は？',
    industry + '事業の特性として、' +
    (industry === 'SaaS' ? 'サブスクリプション型のため月次収益は安定していますが、大型契約の更新タイミングによる四半期ごとの変動は想定しています。' :
     industry === '飲食' ? '季節・天候による来客数の変動があります。繁忙期と閑散期で売上に20-30%程度の差が出ることを見込んでいます。' :
     industry === 'EC' ? 'セール時期やイベントに連動した需要変動があります。Q4の売上が年間の30-40%を占める傾向があります。' :
     '業界固有の需要変動要因を考慮し、保守的な前提で計画を策定しています。'),
    6, ['リスク', '季節性'])

  // === Cost Questions ===
  addQA('cost', '原価率' + fmtPct(cogsRate) + 'は適切ですか？業界水準との比較は？',
    '売上原価率' + fmtPct(cogsRate) + '（粗利率' + fmtPct(grossMargin) + '）は' + industry + '業界の標準的な水準です。' +
    (isDetailed ? 'スケールメリットにより原価率は改善余地があり、FY3以降は' + fmtPct(cogsRate * 0.9) + '程度への改善を目指しています。' : ''),
    8, ['原価率', '粗利'])

  addQA('cost', '販管費の内訳と増加ペースの妥当性は？',
    '初年度販管費は' + fmtYen(opexBase) + 'で、年率' + fmtPct(opexGrowth) + 'で増加する見込みです。' +
    '主な内訳は人件費（約60%）、マーケティング費（約20%）、管理費（約20%）です。' +
    (isDetailed ? '売上成長率' + fmtPct(growthRate) + 'に対してOPEX増加率' + fmtPct(opexGrowth) + 'と低く抑えることで、オペレーティングレバレッジが効く構造です。' : ''),
    7, ['販管費', 'OPEX'])

  addQA('cost', '人件費の計画（採用計画）はどうなっていますか？',
    '販管費' + fmtYen(opexBase) + 'のうち約60%（' + fmtYen(opexBase * 0.6) + '）が人件費です。' +
    (isDetailed ? '初年度は' + Math.round(opexBase * 0.6 / 6_000_000) + '名程度の体制を想定しています。事業拡大に伴い年率' + fmtPct(opexGrowth) + 'で人件費が増加しますが、1人あたり生産性の向上により売上対比では改善します。' :
    '事業成長に合わせて段階的に採用を進めます。'),
    6, ['人件費', '採用'])

  // === Profitability Questions ===
  addQA('profitability', '黒字化の時期はいつですか？',
    breakEven ? '営業黒字化は' + breakEven + 'を見込んでいます。' + (isDetailed ? '粗利率' + fmtPct(grossMargin) + 'の事業構造において、売上が' + fmtYen(opexBase / grossMargin) + 'を超えると黒字化します。' : '') :
    '現在の前提では5年以内の黒字化が困難な見通しです。成長投資を優先し、6年目以降の黒字化を目指しています。',
    10, ['黒字化', '損益分岐'])

  addQA('profitability', 'FY5の営業利益率はどの程度ですか？',
    'FY5の営業利益率は' + fmtPct(opMargin || 0) + '（営業利益' + fmtYen(opFy5) + '）を見込んでいます。' +
    (isDetailed ? '売上成長' + fmtPct(growthRate) + 'に対してコスト増加' + fmtPct(opexGrowth) + 'と低いため、年々利益率が改善する構造です。' : ''),
    9, ['営業利益', 'マージン'])

  addQA('profitability', '累積キャッシュフローの推移は？',
    '5年間の累積FCFは' + fmtYen(cumFcf) + 'です。' +
    (cumFcf > 0 ? '初期投資を回収し、プラスに転じています。' : '初期投資の回収には追加時間が必要です。') +
    (isBanker ? '返済原資として安定的なキャッシュフロー創出が可能な事業構造です。' : ''),
    8, ['FCF', 'キャッシュフロー'])

  // === Growth Questions ===
  addQA('growth', '成長戦略は具体的にどのようなものですか？',
    '年率' + fmtPct(growthRate) + 'の成長を実現するため、' +
    (industry === 'SaaS' ? 'プロダクト改善によるチャーン率低減・NRR向上と、マーケティング投資による新規獲得の両面で成長を目指します。' :
     industry === '飲食' || industry === '小売' ? '既存店の売上向上（客単価・来客数改善）と新規出店の両軸で成長を推進します。' :
     '既存事業の深化と新規チャネル開拓の両面から成長を目指します。') +
    (isDetailed ? 'マーケティング予算は売上の15-20%を目安に配分し、ROIを管理しながら段階的に拡大します。' : ''),
    7, ['成長戦略', '拡大'])

  addQA('growth', 'スケーラビリティについてどう考えていますか？',
    '売上成長' + fmtPct(growthRate) + 'に対しコスト増加' + fmtPct(opexGrowth) + 'と低いため、オペレーティングレバレッジが効く構造です。' +
    (isDetailed ? '具体的には、固定費比率が高い一方で限界利益率' + fmtPct(grossMargin) + 'が高いため、損益分岐点を超えると利益が加速度的に拡大します。' : ''),
    6, ['スケーラビリティ', 'レバレッジ'])

  // === Risk Questions ===
  addQA('risk', 'ダウンサイドリスクのシナリオは？',
    'ワーストケースでは売上-20%、コスト+15%を想定しています。' +
    (pl ? 'この場合のFY5売上は' + fmtYen(revFy5 * 0.8) + '、営業利益率は大幅に低下しますが、' : '') +
    '事業継続に必要なキャッシュは確保できるよう、コスト構造の柔軟性を維持しています。' +
    (isInvestor ? '定期的にバーンレートをモニタリングし、必要に応じてコスト削減を実行します。' : ''),
    8, ['リスク', 'ダウンサイド'])

  addQA('risk', '競合他社との差別化ポイントは？',
    industry + '市場における当社の差別化要因は、' +
    (industry === 'SaaS' ? 'プロダクトの使いやすさ・導入の容易さ・カスタマーサクセスの質にあります。' :
     industry === '人材' ? '専門領域に特化したマッチング精度と、候補者データベースの質にあります。' :
     '事業ドメインに対する深い理解と、独自のバリュープロポジションにあります。') +
    (isDetailed ? 'この競争優位性が維持される前提で、市場シェアの拡大を計画しています。' : ''),
    7, ['競合', '差別化'])

  addQA('risk', '主要なリスク要因と対策は？',
    '主要リスクは①市場環境の変化、②人材獲得競争、③テクノロジー変化です。' +
    (isDetailed ? '①に対しては複数の収益チャネル構築、②に対してはストックオプション・リモートワーク制度、③に対してはR&D投資の継続で対応します。' :
    'それぞれに対する具体的な緩和策を策定しています。'),
    6, ['リスク', '対策'])

  // === Market Questions ===
  addQA('market', 'ターゲット市場の規模と成長性は？',
    industry + '市場のTAMは大きく、' +
    (industry === 'SaaS' ? '日本のSaaS市場は年率20%以上で成長を続けており、2025年には1兆円を超える見通しです。' :
     '当社がターゲットとするセグメントは継続的な成長が見込まれています。') +
    (isDetailed ? '当社のSAMは市場全体の5-10%程度と見込んでおり、初年度の市場シェア目標は1%未満です。' : ''),
    7, ['TAM', '市場規模'])

  addQA('market', '顧客獲得チャネルと戦略は？',
    '主要な顧客獲得チャネルは、' +
    (industry === 'SaaS' ? 'インバウンドマーケティング（コンテンツ・SEO）、アウトバウンド営業、パートナー紹介の3本柱です。' :
     industry === 'EC' ? 'デジタル広告（SNS・リスティング）、SEO、リファラルの組み合わせで新規顧客を獲得します。' :
     '業界特性に合ったマーケティングチャネルを活用し、効率的な顧客獲得を進めます。') +
    (isDetailed ? 'CAC（顧客獲得コスト）をLTVの1/3以下に抑えることを目標としています。' : ''),
    6, ['顧客獲得', 'チャネル'])

  // === Operations Questions ===
  addQA('operations', 'チーム体制と採用計画は？',
    '初年度は' + Math.round(opexBase * 0.6 / 6_000_000) + '名体制でスタートし、売上拡大に合わせて年率' + fmtPct(opexGrowth) + 'のペースで組織を拡大します。' +
    (isDetailed ? '特に' + (industry === 'SaaS' ? 'エンジニアとカスタマーサクセス' : industry === '人材' ? 'コンサルタントとデータ分析' : '事業推進と管理部門') + 'の採用を優先します。' : ''),
    5, ['体制', '採用'])

  addQA('operations', 'KPIのモニタリング体制は？',
    '月次で主要KPIをレビューし、経営判断に反映しています。' +
    (isDetailed ? '主要KPIは売上成長率、粗利率' + fmtPct(grossMargin) + '、営業利益率、バーンレート、' + (industry === 'SaaS' ? 'MRR、チャーン率、NRR' : 'CAC、LTV、顧客満足度') + 'です。' : ''),
    5, ['KPI', 'モニタリング'])

  // === Funding Questions ===
  if (isInvestor || isBanker) {
    addQA('funding', '資金調達の目的と使途は？',
      '調達資金は①プロダクト開発（40%）、②マーケティング投資（30%）、③組織構築（20%）、④運転資金（10%）に配分します。' +
      (isDetailed ? 'この投資により' + fmtPct(growthRate) + 'の成長を実現し、' + (breakEven || 'FY4-5') + 'での黒字化を目指します。' : ''),
      9, ['資金調達', '使途'])

    addQA('funding', '想定バリュエーションとリターンは？',
      'FY5の売上' + fmtYen(revFy5) + 'をベースに、' +
      (industry === 'SaaS' ? 'ARRマルチプル8-12xで評価すると' : '売上マルチプル3-5xで評価すると') +
      '相応のリターンが見込めます。' +
      (isDetailed ? '投資家にとってのIRR 30%以上を目標としています。' : ''),
      8, ['バリュエーション', 'リターン'])

    addQA('funding', '資金のランウェイは？',
      '現在の' + fmtYen(opexBase) + '/年のコスト構造において、' +
      (cumFcf > 0 ? '事業キャッシュフローでの自走が可能です。' :
      '十分なランウェイを確保した上で成長投資を行います。追加資金が必要な場合は、マイルストーン達成後の次ラウンド調達を計画しています。'),
      7, ['ランウェイ', '資金繰り'])
  }

  // Filter and sort based on settings
  // Adjust priority based on target audience
  allQA.forEach(function(qa) {
    if (settings.target === 'investor' && (qa.category === 'funding' || qa.category === 'growth')) {
      qa.priority += 2
    }
    if (settings.target === 'banker' && (qa.category === 'risk' || qa.category === 'funding')) {
      qa.priority += 2
    }
    if (settings.target === 'board' && (qa.category === 'profitability' || qa.category === 'operations')) {
      qa.priority += 2
    }
    if (settings.target === 'team' && (qa.category === 'operations' || qa.category === 'growth')) {
      qa.priority += 2
    }
  })

  // Sort by priority descending
  allQA.sort(function(a, b) { return b.priority - a.priority })

  // Trim answers based on length setting
  if (settings.answerLength === 'short') {
    allQA.forEach(function(qa) {
      // Take first sentence
      var firstSentence = qa.answer.split('。')[0]
      qa.answer = firstSentence + '。'
    })
  } else if (settings.answerLength === 'medium') {
    allQA.forEach(function(qa) {
      // Take first 2-3 sentences
      var sentences = qa.answer.split('。').filter(function(s) { return s.trim() })
      qa.answer = sentences.slice(0, 3).join('。') + '。'
    })
  }

  return allQA.slice(0, settings.count)
}
