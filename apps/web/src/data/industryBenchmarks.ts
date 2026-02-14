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

export interface Competitor {
  name: string
  features: string
  strengths: string
  revenue: string
  operatingProfit: string
}

export type PerspectiveKey = 'market' | 'tech' | 'regulation' | 'consumer' | 'competition' | 'risk'

export interface TrendItem {
  title: string
  summary: string
  plImpact: string
  perspective: PerspectiveKey
}

export interface CompetitionDetail {
  marketStructure: string
  entryBarriers: string
  ksf: string
  risks: string
}

export const PERSPECTIVE_META: Record<PerspectiveKey, { label: string; color: string; icon: string }> = {
  market:      { label: '市場',   color: 'blue',    icon: 'chart' },
  tech:        { label: '技術',   color: 'purple',  icon: 'cpu' },
  regulation:  { label: '規制',   color: 'rose',    icon: 'shield' },
  consumer:    { label: '消費者', color: 'green',   icon: 'users' },
  competition: { label: '競争',   color: 'orange',  icon: 'swords' },
  risk:        { label: 'リスク', color: 'red',     icon: 'alert' },
}

export const PERSPECTIVE_KEYS: PerspectiveKey[] = ['market', 'tech', 'regulation', 'consumer', 'competition', 'risk']

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
  /** Competitive landscape overview */
  competitiveEnvironment: string
  /** Structured competition analysis */
  competitionDetail: CompetitionDetail
  /** Industry trends with perspective and P&L impact */
  trends: TrendItem[]
  /** Major competitors (3-5 companies) */
  competitors: Competitor[]
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
    competitiveEnvironment: '大手クラウドベンダーと多数のスタートアップが混在する競争激化市場。Vertical SaaSへの特化と、AI機能統合による差別化が主戦場。ARR $1B超のメガSaaSが市場を寡占する一方、ニッチ領域では新興勢力が台頭。PLG（Product-Led Growth）の浸透により、販売サイクルの短縮が業界全体のトレンド。',
    competitionDetail: {
      marketStructure: '大手クラウドベンダー（Salesforce, Microsoft, Google）が上位を寡占。ARR $1B超のメガSaaSと多数のスタートアップによる二極構造。業界別ではVertical SaaSの台頭でニッチ市場にも機会あり。',
      entryBarriers: 'クラウドインフラ普及で技術的障壁は低下。ただしエンタープライズ向けはセキュリティ・コンプライアンス認証（SOC2, ISO27001）が必須。NRR 120%+の既存プレイヤーはスイッチングコストで優位。',
      ksf: 'プロダクト主導成長（PLG）による低CACの獲得モデル。AI/LLM統合によるユーザー体験差別化。APIエコシステム構築と高NRRの維持。',
      risks: '大手ベンダーによる機能バンドル化（Best-of-Suite vs Best-of-Breed）。AI進化による既存SaaS機能の代替リスク。景気後退時のIT予算削減によるチャーン増加。',
    },
    trends: [
      { title: 'AI/LLM統合', summary: 'Copilot機能の搭載が標準化。生成AIによる自動化・アシスト機能がプロダクトの差別化要素に。', plImpact: 'R&D費10-20%増加。ただしAI機能によるARPU +15-30%向上とチャーン抑制効果が期待。', perspective: 'tech' },
      { title: 'Vertical SaaS', summary: '業界特化型SaaSの台頭。汎用ツールから業種別ソリューションへの移行が加速。', plImpact: '汎用SaaS比で粗利率5-10%改善。業界知見がCAC回収期間を短縮（18→12ヶ月）。', perspective: 'market' },
      { title: 'PLG（Product-Led Growth）', summary: 'セルフサーブ型の導入モデルが主流化。営業主導からプロダクト主導の成長戦略へ。', plImpact: 'S&M費率を40%→25%に削減可能。フリーミアム→有料転換率3-5%が業界標準。', perspective: 'competition' },
      { title: 'コンポーザブルアーキテクチャ', summary: 'API連携・マーケットプレイス型エコシステムの構築。ベストオブブリードの統合。', plImpact: 'パートナー経由売上が全体の15-25%に成長。API連携による開発コスト削減。', perspective: 'tech' },
      { title: 'Usage-Based Pricing', summary: '従量課金モデルの採用増加。サブスクリプションとのハイブリッド課金が主流に。', plImpact: '売上変動性が増すが、大口顧客のARPU上限を撤廃。NRR 130%+を実現する企業も。', perspective: 'market' },
    ],
    competitors: [
      { name: 'Salesforce', features: 'CRM/SFA/MAの統合プラットフォーム', strengths: '圧倒的な市場シェアとエコシステム', revenue: '約5兆円（$34.9B）', operatingProfit: '約8,500億円（営業利益率17.2%）' },
      { name: 'ServiceNow', features: 'IT運用・ワークフロー自動化プラットフォーム', strengths: 'エンタープライズ向け強固な基盤とNRR 125%超', revenue: '約1.3兆円（$8.9B）', operatingProfit: '約3,500億円（営業利益率27%）' },
      { name: 'Datadog', features: 'クラウド監視・オブザーバビリティ', strengths: '統合プラットフォーム戦略とDevOps市場の成長', revenue: '約3,500億円（$2.1B）', operatingProfit: '約700億円（営業利益率22%）' },
      { name: 'HubSpot', features: 'SMB向けCRM・マーケティング統合', strengths: 'PLGモデルの成功事例、フリーミアム戦略', revenue: '約3,200億円（$2.2B）', operatingProfit: '約370億円（営業利益率12%）' },
    ],
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
    competitiveEnvironment: '少子化による市場縮小圧力の中、オンライン教育・EdTechが急成長。大手学習塾チェーンとEdTechスタートアップの二極化が進行。リスキリング需要の高まりにより社会人教育市場が拡大中。コンテンツの質と学習成果の可視化が競争優位の鍵。',
    competitionDetail: {
      marketStructure: '大手学習塾チェーン（ベネッセ、ナガセ、河合塾）が学齢市場を支配。EdTechスタートアップがオンライン領域で急成長中。社会人教育市場は分散的で新規参入余地あり。',
      entryBarriers: '教育コンテンツの品質とブランド信頼の構築に時間が必要。学校向けはICT導入の意思決定プロセスが長い。一方、オンライン個人向けは比較的参入しやすい。',
      ksf: '学習成果の可視化（成績向上の実績データ）。AI個別最適化による学習体験の差別化。リスキリング需要の取り込みとB2B展開。',
      risks: '少子化による学齢市場の構造的縮小（年1-2%減）。無料コンテンツ（YouTube等）との競合。政府補助金政策の変動リスク。',
    },
    trends: [
      { title: 'オンライン/ハイブリッド学習', summary: 'コロナ後も定着した対面×オンラインの併用モデル。場所を問わない学習環境が標準に。', plImpact: '施設賃料30-50%削減可能。一方でプラットフォーム開発費が年間2,000-5,000万円必要。', perspective: 'market' },
      { title: 'AI個別最適化', summary: 'アダプティブラーニングにより一人一人に合わせた学習体験を提供。学習効率の大幅向上。', plImpact: 'AI開発投資が初期1-3億円。講師1人あたり担当生徒数を2-3倍に拡大し人件費効率化。', perspective: 'tech' },
      { title: 'リスキリング/社会人教育', summary: '政府補助金も追い風に、企業向け研修・生涯学習市場が急拡大。人材不足時代の成長市場。', plImpact: '法人単価は個人の3-5倍。助成金活用で実質顧客負担減→受注率向上。市場規模は年+15%成長。', perspective: 'regulation' },
      { title: 'マイクロラーニング', summary: '短時間コンテンツ・モバイルファーストの学習形態。隙間時間の活用で学習継続率向上。', plImpact: 'コンテンツ制作コスト1/3に低減（5分動画 vs 90分講義）。月額サブスク化で安定収益。', perspective: 'consumer' },
    ],
    competitors: [
      { name: 'ベネッセHD', features: '通信教育「進研ゼミ」、学校ICT支援', strengths: '圧倒的な顧客基盤と教材開発力', revenue: '約4,200億円', operatingProfit: '約200億円（営業利益率4.8%）' },
      { name: 'リクルート（スタディサプリ）', features: 'オンライン学習プラットフォーム', strengths: '低価格×高品質な映像授業、B2B2C展開', revenue: '教育事業 約1,200億円', operatingProfit: '約180億円（営業利益率15%）' },
      { name: 'ナガセ（東進）', features: '映像授業予備校、全国FC展開', strengths: 'トップ講師陣と合格実績ブランド', revenue: '約500億円', operatingProfit: '約70億円（営業利益率14%）' },
      { name: 'atama plus', features: 'AI学習プラットフォーム（塾向け）', strengths: 'AI個別最適化技術、大手塾との提携網', revenue: '約50億円（推定）', operatingProfit: '成長投資フェーズ' },
    ],
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
    competitiveEnvironment: '大手人材サービス会社が市場の過半を占める寡占市場。ダイレクトリクルーティングの台頭で従来型紹介モデルが変化。IT/DXエンジニア特化型や副業マッチングなどニッチ領域での新規参入が活発。人手不足を背景に市場全体は堅調に成長。',
    competitionDetail: {
      marketStructure: 'リクルートHDが圧倒的首位（グローバル含め3.4兆円）。パーソル・パソナ等の大手5社が市場の60%を占有。IT/DX特化型・副業マッチング等ニッチ領域で新興勢力が台頭。',
      entryBarriers: '求人データベースと候補者ネットワークの構築に時間とコストが必要。大手はブランド力とリピート顧客で優位。一方、特定職種・業界特化であれば小規模でも参入可能。',
      ksf: 'マッチング精度の向上（成約率×単価の最大化）。企業・候補者双方のデータベース品質。特定領域での専門性とブランド構築。',
      risks: 'ダイレクトリクルーティングの普及による紹介手数料モデルの侵食。景気後退時の採用凍結による急激な売上減。AI自動マッチングによる中間業者の不要化。',
    },
    trends: [
      { title: 'ダイレクトリクルーティング', summary: '企業が候補者に直接アプローチするスカウト型採用が主流化。従来型紹介の市場を侵食。', plImpact: '紹介手数料率25-35%→プラットフォーム利用料月額制へ移行圧力。1件あたり売上は減少傾向。', perspective: 'competition' },
      { title: 'フリーランス/副業マッチング', summary: '雇用形態の多様化に伴いギグワーク・副業プラットフォームが急成長。新たな収益源。', plImpact: '正社員紹介比で単価は低いが、ボリュームで補完。プラットフォーム手数料15-25%の継続収益モデル。', perspective: 'market' },
      { title: 'AI選考・マッチング', summary: 'AIによる書類スクリーニングと最適人材マッチングの自動化。選考プロセスの効率化。', plImpact: 'コンサルタント1人あたり担当案件数を1.5-2倍に。AI投資は年間3,000-8,000万円、人件費削減効果は1-2年で回収。', perspective: 'tech' },
      { title: 'リファラル採用', summary: '社員紹介経由の採用が増加。専用ツール・プラットフォームの普及。', plImpact: '企業の外部紹介依存度低下→紹介会社の売上減リスク。ただしリファラルツール提供で新市場創出の機会。', perspective: 'consumer' },
    ],
    competitors: [
      { name: 'リクルートHD', features: '総合人材サービス（Indeed, リクナビ, リクルートエージェント）', strengths: '国内最大の求人データベースとグローバル展開', revenue: '約3.4兆円（HR Technology含む）', operatingProfit: '約4,500億円（営業利益率13%）' },
      { name: 'パーソルHD', features: '人材派遣・紹介・BPO（doda, テンプスタッフ）', strengths: '派遣×紹介の複合サービスと規模の経済', revenue: '約1.3兆円', operatingProfit: '約580億円（営業利益率4.5%）' },
      { name: 'ビズリーチ（Visional）', features: 'ハイクラス向けダイレクトリクルーティング', strengths: '管理職・専門職特化のDB、企業スカウトモデル', revenue: '約600億円', operatingProfit: '約120億円（営業利益率20%）' },
      { name: 'エン・ジャパン', features: '求人サイト・転職エージェント', strengths: '口コミ情報の充実とアジア展開', revenue: '約700億円', operatingProfit: '約80億円（営業利益率11%）' },
    ],
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
    competitiveEnvironment: 'Amazon・楽天の二大プラットフォームが市場を支配する中、D2Cブランドの台頭が顕著。Shopify等のEC基盤ツールの普及により参入障壁は低下。一方で物流・CS品質が差別化要素に。ソーシャルコマースやライブコマースの新チャネルも急成長中。',
    competitionDetail: {
      marketStructure: 'Amazon Japan（推定3.5兆円）と楽天市場（1.2兆円）の二大プラットフォームが市場の過半を占有。ZOZO（ファッション特化）、メルカリ（C2C）等がカテゴリ特化で成長。D2Cブランドの直販モデルが急拡大中。',
      entryBarriers: 'Shopify等のSaaS型EC基盤で技術障壁は大幅低下。ただし物流インフラ（倉庫・配送網）の構築には大規模投資が必要。Amazon FBAへの依存はプラットフォームリスクあり。',
      ksf: '物流品質（配送スピード・正確性）の差別化。SNSを活用したブランド構築とリピート顧客獲得。データ活用によるパーソナライズ推薦と在庫最適化。',
      risks: 'プラットフォーム手数料の引き上げリスク（テイクレート上昇）。物流コスト・人件費の構造的上昇。返品率増加によるマージン圧迫。',
    },
    trends: [
      { title: 'D2C/ブランドEC', summary: 'メーカー直販モデルの拡大。SNSを活用した独自ブランド構築により中間マージンを排除。', plImpact: '粗利率60-70%（卸経由の30-40%比で大幅改善）。ただし自社マーケ費用が売上の20-35%必要。', perspective: 'market' },
      { title: 'ソーシャルコマース', summary: 'Instagram/TikTok経由の購買導線が急拡大。コンテンツ→購入のシームレスな体験。', plImpact: '広告CPC低下（検索広告比で30-50%安）。UGCによるマーケ費削減効果。CVR 2-5倍の事例も。', perspective: 'consumer' },
      { title: 'ライブコマース', summary: 'ライブ配信での販売が中国に続き日本でも成長中。インフルエンサー活用の新販売チャネル。', plImpact: '配信1回あたり売上50-500万円。出演料＋プラットフォーム手数料15-30%が追加コスト。', perspective: 'tech' },
      { title: 'サステナブルEC', summary: '環境配慮型商品・包装への需要増。リコマース（二次流通）市場の急成長。', plImpact: 'エコ包材はコスト+5-10%。ただしサステナブル商品は平均単価15-25%プレミアム可能。', perspective: 'regulation' },
      { title: 'クイックコマース', summary: '30分以内即配達サービスの台頭。ダークストア型の新業態が都市部で急成長。', plImpact: '配送コスト300-500円/件で粗利を圧迫。ただし客単価+20%・リピート率1.5倍の効果。', perspective: 'competition' },
    ],
    competitors: [
      { name: 'Amazon Japan', features: '総合ECプラットフォーム + Prime会員サービス', strengths: '物流インフラ（FBA）と圧倒的な品揃え', revenue: '約3.5兆円（日本事業推定）', operatingProfit: '非開示（全社営業利益率6%）' },
      { name: '楽天グループ（楽天市場）', features: 'モール型EC + ポイントエコシステム', strengths: '楽天経済圏1億ID、ポイント還元の集客力', revenue: 'EC事業 約1.2兆円', operatingProfit: 'EC事業 約700億円（推定）' },
      { name: 'ZOZO（ZOZOTOWN）', features: 'ファッション特化型ECモール', strengths: '圧倒的なファッションEC認知度、計測技術', revenue: '約1,800億円', operatingProfit: '約500億円（営業利益率28%）' },
      { name: 'メルカリ', features: 'C2Cフリマ + メルカリShops', strengths: '月間2,300万人利用の二次流通プラットフォーム', revenue: '約1,900億円', operatingProfit: '約140億円（営業利益率7%）' },
    ],
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
    competitiveEnvironment: 'コンビニ3社（セブン、ローソン、ファミマ）がインフラ化し、専門小売・ドラッグストアが成長。人口減少による市場縮小を、インバウンド需要とPB商品強化で補う構造。DX推進（セルフレジ・無人店舗）とオムニチャネル化が競争の焦点。',
    competitionDetail: {
      marketStructure: 'コンビニ3社（セブン21,000店・ローソン14,600店・ファミマ16,500店）がインフラ化。イオン・セブン&アイの2大流通が総合小売を支配。ドラッグストアが食品進出で急成長。',
      entryBarriers: '店舗網とサプライチェーンの構築に大規模資本が必要。コンビニはFC加盟金＋ロイヤリティが重い。ドラッグストアは薬剤師確保が制約。EC参入は比較的容易だが物流網がボトルネック。',
      ksf: 'PB商品開発力（粗利率NB比+10-15%）。データ活用による需要予測と在庫最適化。オムニチャネル（店舗×EC×アプリ）の統合顧客体験。',
      risks: '人口減少による国内市場の構造的縮小。人手不足・最低賃金上昇による人件費圧力。食品ロス規制強化（廃棄コスト増）。',
    },
    trends: [
      { title: 'オムニチャネル', summary: '店舗×EC×アプリの統合購買体験の構築。店舗受取・即日配送の需要増。', plImpact: 'EC売上比率5→15%へ。EC専用倉庫投資5-20億円。客単価はEC経由で+30%高い傾向。', perspective: 'market' },
      { title: 'DX・無人店舗', summary: 'セルフレジ、AI需要予測、無人決済店舗の実験・導入拡大。', plImpact: 'セルフレジ導入で人件費10-15%削減。AI需要予測で食品ロス20-30%削減。初期投資1店舗500-1,000万円。', perspective: 'tech' },
      { title: 'PB商品強化', summary: '高利益率PB商品の拡充による粗利改善。品質向上で消費者の信頼も向上。', plImpact: 'PB比率10→30%で粗利率+3-5%改善。開発コストは売上の1-2%増。', perspective: 'competition' },
      { title: 'ドラッグストア躍進', summary: '食品・日用品の取扱い拡大で総合小売化。調剤併設で集客力強化。', plImpact: '食品売上構成比40%超で来店頻度向上。薬価改定リスクは調剤部門の利益率を圧迫。', perspective: 'consumer' },
    ],
    competitors: [
      { name: 'セブン&アイHD', features: 'コンビニ（セブン-イレブン）、スーパー（イトーヨーカドー）', strengths: '国内21,000店超の圧倒的店舗網とPB「セブンプレミアム」', revenue: '約11兆円', operatingProfit: '約4,700億円（営業利益率4.2%）' },
      { name: 'イオン', features: '総合スーパー・モール・金融・ヘルスケア', strengths: '国内最大の小売グループ、モール集客力', revenue: '約9.5兆円', operatingProfit: '約2,500億円（営業利益率2.6%）' },
      { name: 'ファーストリテイリング（ユニクロ）', features: 'SPA型アパレル小売', strengths: 'グローバル展開と製販一体のコスト競争力', revenue: '約3兆円', operatingProfit: '約4,500億円（営業利益率15%）' },
      { name: 'ウエルシアHD', features: 'ドラッグストアチェーン', strengths: '調剤併設型店舗と食品取扱い拡大', revenue: '約1.2兆円', operatingProfit: '約430億円（営業利益率3.6%）' },
    ],
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
    competitiveEnvironment: '大手チェーンのFC展開による寡占化と、個人店・新興ブランドの二極化。原材料費・人件費の高騰が業界全体の課題。デリバリー/テイクアウト需要の定着で「店舗外売上」の比率が増加。高付加価値路線とコスト効率化の両立が求められる。',
    competitionDetail: {
      marketStructure: 'ゼンショーHD（すき家等、8,500億円）が国内最大。マクドナルド・すかいらーく・スタバ等の大手チェーンがFC展開で店舗数拡大。個人経営店は全体の70%だが売上シェアは40%以下。',
      entryBarriers: '個店の開業障壁は比較的低い（初期投資1,000-3,000万円）。ただし3年生存率は30-50%と厳しい。チェーン展開にはセントラルキッチン・物流網の構築（数十億円規模）が必要。',
      ksf: 'FL比率60%以下の維持（食材30%+人件費30%）。立地選定とターゲット客層の明確化。デリバリー/テイクアウト対応による売上チャネル多角化。',
      risks: '食材価格の高騰（輸入食材は為替リスクあり）。最低賃金上昇による人件費圧力。食品衛生法改正への対応コスト。',
    },
    trends: [
      { title: 'デリバリー/テイクアウト常態化', summary: 'UberEats・出前館による店舗外売上が全体の15-30%に定着。イートイン依存からの脱却。', plImpact: 'デリバリー手数料35%が粗利を圧迫。ただし追加売上として限界利益は確保可能。自社配達で手数料削減。', perspective: 'market' },
      { title: 'ゴーストキッチン', summary: '客席なしのデリバリー専用キッチンで固定費を大幅削減。複数ブランドの同時運営。', plImpact: '賃料60-70%削減（客席不要）。1拠点で3-5ブランド運営可能。ただし集客は完全にプラットフォーム依存。', perspective: 'competition' },
      { title: 'DX推進・省人化', summary: 'モバイルオーダー、セルフレジ、AI需要予測による省人化・オペレーション効率化。', plImpact: 'ホールスタッフ20-30%削減。AI需要予測で食品ロス15-25%削減。システム導入費1店舗200-500万円。', perspective: 'tech' },
      { title: '原価高騰対応', summary: '食材価格上昇に対するメニュー改定・ポーションコントロール。値上げ戦略の巧拙が業績を左右。', plImpact: '食材原価率+3-5%上昇を価格改定+5-8%で吸収。値上げ許容度は業態により異なる。', perspective: 'risk' },
      { title: '体験価値重視', summary: 'SNS映え、コト消費としての飲食体験の差別化。付加価値路線で客単価向上。', plImpact: '体験型メニューは客単価+30-50%。SNS投稿による無料広告効果（広告費削減-10%）。', perspective: 'consumer' },
    ],
    competitors: [
      { name: 'すかいらーくHD', features: 'ファミレスチェーン（ガスト、バーミヤン等）', strengths: '約3,000店の店舗網とセントラルキッチン', revenue: '約3,700億円', operatingProfit: '約150億円（営業利益率4%）' },
      { name: 'ゼンショーHD', features: '牛丼（すき家）、回転寿司（はま寿司）等', strengths: '国内最大の外食チェーン、多業態展開', revenue: '約8,500億円', operatingProfit: '約450億円（営業利益率5.3%）' },
      { name: '日本マクドナルドHD', features: 'ハンバーガーチェーン', strengths: '圧倒的ブランド力とFC model、デジタル戦略', revenue: '約3,800億円', operatingProfit: '約380億円（営業利益率10%）' },
      { name: 'スターバックス コーヒー ジャパン', features: 'スペシャルティコーヒーチェーン', strengths: 'ブランド・空間価値と高単価戦略', revenue: '約2,500億円', operatingProfit: '約250億円（営業利益率10%）' },
    ],
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
    competitiveEnvironment: '素材・部品メーカーは技術力で寡占、完成品メーカーは価格競争が激化。グローバルサプライチェーンの再編（国内回帰、チャイナ+1）が進行中。カーボンニュートラル対応のための設備投資が必須となり、ESG経営が競争力の新基準に。',
    competitionDetail: {
      marketStructure: '素材・部品メーカーは技術力で寡占（キーエンス営業利益率55%、村田製作所MLCC世界シェア40%）。完成品メーカーは新興国との価格競争が激化。B2B部品は高利益率、B2C完成品は低利益率の二極構造。',
      entryBarriers: '製造設備の初期投資が大きい（数億〜数百億円）。品質管理のノウハウ蓄積に長期間を要する。素材・部品は技術特許が参入障壁。認証取得（ISO, 各国規制）もハードル。',
      ksf: '独自技術・特許による高付加価値製品の開発。グローバル生産拠点の最適配置。カーボンニュートラル対応とESG経営による取引先要件の充足。',
      risks: '地政学リスクによるサプライチェーン分断。原材料（レアメタル等）の価格高騰と供給不安。円安/円高の為替変動リスク。',
    },
    trends: [
      { title: 'スマートファクトリー', summary: 'IoT/AI活用の工場自動化。予知保全、品質管理の高度化、デジタルツイン活用。', plImpact: '製造コスト10-20%削減。予知保全でダウンタイム50-70%削減。IoT投資は年間1-5億円規模。', perspective: 'tech' },
      { title: 'サプライチェーン再編', summary: '地政学リスクを踏まえた生産拠点の分散・国内回帰。チャイナ+1戦略の加速。', plImpact: '国内回帰は製造コスト+10-20%。ただしサプライチェーンリスクの軽減による事業継続性向上。', perspective: 'risk' },
      { title: 'カーボンニュートラル', summary: 'CO2排出削減、再エネ導入、Scope3対応。取引先からのESG要件が強化。', plImpact: 'RE100対応で電力コスト+5-15%。ただしESG対応が取引条件化しており非対応は受注減リスク。', perspective: 'regulation' },
      { title: 'アフターサービス収益', summary: '製品販売からサービス（保守・サブスク・データ活用）への収益モデル転換。', plImpact: 'サービス売上比率10→30%で粗利率改善（サービス粗利60-70% vs 製品30-40%）。ストック収益化。', perspective: 'market' },
    ],
    competitors: [
      { name: 'キーエンス', features: 'FA用センサー・計測機器・画像処理', strengths: '直販モデルと55%超の営業利益率', revenue: '約9,200億円', operatingProfit: '約5,100億円（営業利益率55%）' },
      { name: 'ダイキン工業', features: '空調機器のグローバルメーカー', strengths: '世界シェア1位の空調技術とグローバル展開', revenue: '約4.2兆円', operatingProfit: '約4,400億円（営業利益率10%）' },
      { name: '村田製作所', features: '電子部品（セラミックコンデンサ等）', strengths: 'MLCC世界シェア40%、EV/5G需要取込み', revenue: '約1.7兆円', operatingProfit: '約3,200億円（営業利益率19%）' },
      { name: 'SMC', features: '空圧機器の世界トップメーカー', strengths: '工場自動化のFA需要を独占、世界シェア38%', revenue: '約8,200億円', operatingProfit: '約2,900億円（営業利益率35%）' },
    ],
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
    competitiveEnvironment: '医療DXが国策として推進される中、電子カルテ・オンライン診療・PHR（個人健康記録）が急成長。規制産業のため参入障壁は高いが、デジタルヘルスへの投資が活発。薬事承認プロセスのDX化（SaMD=プログラム医療機器）が新市場を創出。大手製薬・医療機器メーカーとデジタルヘルススタートアップの提携が加速。',
    competitionDetail: {
      marketStructure: 'エムスリー（医師の90%が登録）がプラットフォームを独占。電子カルテはPHC・富士通・NEC等が競合。オンライン診療はメドレー（CLINICS）が先行。ウェルネス領域は多数のスタートアップが乱立。',
      entryBarriers: '薬事承認・医療機器認証の取得に1-3年＋数千万〜数億円の投資が必要。医療データの取扱いは個人情報保護法・医療法の厳格規制。医療機関の意思決定プロセスは長い（6-18ヶ月）。',
      ksf: '薬事承認のスピードと規制対応力。医療機関・医師ネットワークの構築。エビデンスに基づく臨床効果の実証。大手製薬・医療機器メーカーとの提携。',
      risks: '薬価改定による収益性の変動。医療データ漏洩時のレピュテーションリスクと法的責任。保険適用の可否による市場規模の大幅変動。',
    },
    trends: [
      { title: 'オンライン診療', summary: '規制緩和により恒久化。初診からのオンライン対応が可能になり、遠隔医療が日常化。', plImpact: '通院不要で患者アクセス2-3倍。診療単価は対面比-20%だがボリュームで補完。プラットフォーム利用料月額5-20万円。', perspective: 'regulation' },
      { title: 'SaMD（プログラム医療機器）', summary: 'AIによる診断支援ソフトの薬事承認が増加。画像診断・病理・眼科領域で実用化。', plImpact: '承認後はSaaS型で月額5-50万円/施設。開発投資2-5億円、承認取得に1-3年。承認後の粗利率80%超。', perspective: 'tech' },
      { title: 'PHR/ウェアラブル', summary: 'Apple Watch等によるバイタル記録。予防医療データの活用と健康管理サービスの拡大。', plImpact: '予防医療市場は年+20%成長。ウェアラブルデータ連携で月額サブスク500-3,000円/ユーザーの新収益源。', perspective: 'consumer' },
      { title: 'バイオテック', summary: 'mRNA技術、遺伝子治療、個別化医療の発展。コロナワクチンを契機に投資が加速。', plImpact: '開発成功時のリターンは莫大（ブロックバスター薬は年売上1,000億円+）だが成功確率は10%以下。R&D投資は売上の20-30%。', perspective: 'market' },
      { title: '医療DX政策', summary: 'マイナ保険証、電子処方箋、医療データ連携基盤の政府主導整備。', plImpact: '政策対応システムの需要増。電子処方箋対応は薬局1店舗100-300万円の投資。補助金活用で顧客負担軽減。', perspective: 'regulation' },
    ],
    competitors: [
      { name: 'エムスリー', features: '医療従事者向けプラットフォーム（m3.com）', strengths: '国内医師の90%が登録、製薬MR代替のデジタルマーケ', revenue: '約2,300億円', operatingProfit: '約600億円（営業利益率26%）' },
      { name: 'メドレー', features: 'オンライン診療（CLINICS）、人材（ジョブメドレー）', strengths: 'SaaS×人材の複合モデルで医療機関を包括支援', revenue: '約200億円', operatingProfit: '約30億円（営業利益率15%）' },
      { name: 'PHCホールディングス', features: '診療所向け電子カルテ・検査機器', strengths: '国内電子カルテシェアトップクラス', revenue: '約3,500億円', operatingProfit: '約250億円（営業利益率7%）' },
      { name: 'テルモ', features: '医療機器（カテーテル、輸液等）', strengths: 'グローバル展開と高シェアのカテーテル事業', revenue: '約8,600億円', operatingProfit: '約1,400億円（営業利益率16%）' },
    ],
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
    competitiveEnvironment: '業種により競争環境は大きく異なる。一般的に、デジタル化の進展により業界の垣根が低下し、異業種参入が増加傾向。スタートアップによるディスラプションと、大企業によるデジタル変革の両面で競争が激化。',
    competitionDetail: {
      marketStructure: '業界により寡占〜分散まで多様。デジタル化の進展で業界の垣根が低下し、異業種からの参入が増加。プラットフォーム型ビジネスの台頭で「勝者総取り」傾向。',
      entryBarriers: 'デジタル系は比較的低障壁で参入可能。規制業界（金融・医療・建設等）は許認可がハードル。既存大手のブランド力・顧客基盤がスイッチングコストとして機能。',
      ksf: 'DXによる業務効率化とコスト競争力。顧客データの活用によるパーソナライゼーション。持続可能な成長モデルの構築（ESG対応含む）。',
      risks: 'スタートアップによる業界ディスラプション。景気変動に対する事業の脆弱性。デジタル人材の確保難と人件費高騰。',
    },
    trends: [
      { title: 'DX推進', summary: 'あらゆる業界でデジタルトランスフォーメーションが加速。レガシーシステムの刷新が急務。', plImpact: 'DX投資は売上の3-8%。業務効率化で人件費10-25%削減。顧客接点のデジタル化でCAC改善。', perspective: 'tech' },
      { title: 'サステナビリティ経営', summary: 'ESG/SDGsへの対応が投資家・消費者双方から要求。非財務情報の開示義務化が進行。', plImpact: 'ESG対応コストは売上の1-3%増。ただしESG投資は資金調達コスト-0.2-0.5%低下と中長期的な企業価値向上に寄与。', perspective: 'regulation' },
      { title: 'AI/自動化', summary: '業務プロセスの自動化・効率化による生産性向上。生成AIの業務活用が急速に普及。', plImpact: '定型業務の30-50%を自動化可能。AI導入で従業員1人あたり生産性+15-30%向上。初期導入コスト500-3,000万円。', perspective: 'tech' },
      { title: '人材不足対応', summary: '少子高齢化に伴う人手不足への技術的・組織的対応。外国人材活用やリモートワーク定着。', plImpact: '人件費年+3-5%上昇圧力。省人化投資とリモートワーク環境整備で生産性維持。採用コスト増加傾向。', perspective: 'risk' },
    ],
    competitors: [
      { name: '（業界により異なる）', features: '業界リーダー企業', strengths: '市場シェアとブランド力', revenue: '業界により異なる', operatingProfit: '業界平均 営業利益率5-15%' },
      { name: '（業界により異なる）', features: 'チャレンジャー企業', strengths: '差別化戦略とイノベーション', revenue: '業界により異なる', operatingProfit: '業界平均 営業利益率3-10%' },
      { name: '（業界により異なる）', features: 'ニッチプレイヤー', strengths: '特定セグメントでの専門性', revenue: '業界により異なる', operatingProfit: '業界平均 営業利益率5-20%' },
    ],
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
