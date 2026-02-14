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
  /** Industry trends (3-5 items) */
  trends: string[]
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
    trends: [
      'AI/LLM統合 — Copilot機能の搭載が標準化、生成AIによる自動化・アシスト機能が差別化要素に',
      'Vertical SaaS — 業界特化型SaaSの台頭。汎用ツールから業種別ソリューションへの移行',
      'PLG（Product-Led Growth） — セルフサーブ型の導入モデルが主流化、営業主導からプロダクト主導へ',
      'コンポーザブルアーキテクチャ — API連携・マーケットプレイス型エコシステムの構築',
      'Usage-Based Pricing — 従量課金モデルの採用増加、サブスクとのハイブリッド',
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
    trends: [
      'オンライン/ハイブリッド学習 — コロナ後も定着、対面×オンラインの併用モデルが主流に',
      'AI個別最適化 — アダプティブラーニングによる一人一人に合わせた学習体験の提供',
      'リスキリング/社会人教育 — 政府補助金も追い風に、企業向け研修・生涯学習市場が急拡大',
      'マイクロラーニング — 短時間コンテンツ・モバイルファーストの学習形態',
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
    trends: [
      'ダイレクトリクルーティング — 企業が候補者に直接アプローチするスカウト型採用の主流化',
      'フリーランス/副業マッチング — 雇用形態の多様化に伴いギグワーク・副業プラットフォームが成長',
      'AI選考・マッチング — AIによるスクリーニング、最適人材マッチングの自動化',
      'リファラル採用 — 社員紹介経由の採用が増加、専用ツールの普及',
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
    trends: [
      'D2C/ブランドEC — メーカー直販モデルの拡大、SNS活用したブランド構築',
      'ソーシャルコマース — Instagram/TikTok経由の購買導線が急拡大',
      'ライブコマース — ライブ配信での販売が中国に続き日本でも成長',
      'サステナブルEC — 環境配慮型商品・包装への需要増、リコマース（二次流通）',
      'クイックコマース — 即配達（30分以内）サービスの台頭',
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
    trends: [
      'オムニチャネル — 店舗×EC×アプリの統合購買体験の構築',
      'DX・無人店舗 — セルフレジ、AI需要予測、無人決済店舗の実験',
      'PB（プライベートブランド）強化 — 高利益率PB商品の拡充による粗利改善',
      'ドラッグストア躍進 — 食品・日用品の取扱い拡大で総合小売化',
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
    trends: [
      'デリバリー/テイクアウト常態化 — UberEats・出前館による店舗外売上が全体の15-30%に',
      'ゴーストキッチン — 客席なしのデリバリー専用キッチンで固定費削減',
      'DX推進 — モバイルオーダー、セルフレジ、AI需要予測による省人化',
      '原価高騰対応 — 食材価格上昇に対するメニュー改定・ポーションコントロール',
      '体験価値重視 — SNS映え、コト消費としての飲食体験の差別化',
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
    trends: [
      'スマートファクトリー — IoT/AI活用の工場自動化、予知保全、品質管理の高度化',
      'サプライチェーン再編 — 地政学リスクを踏まえた生産拠点の分散・国内回帰',
      'カーボンニュートラル — CO2排出削減、再エネ導入、Scope3対応',
      'アフターサービス収益 — 製品販売からサービス（保守・サブスク）への収益モデル転換',
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
    trends: [
      'オンライン診療 — 規制緩和により恒久化、初診からのオンライン対応が可能に',
      'SaMD（プログラム医療機器） — AIによる診断支援ソフトの薬事承認が増加',
      'PHR/ウェアラブル — Apple Watch等によるバイタル記録、予防医療データの活用',
      'バイオテック — mRNA技術、遺伝子治療、個別化医療の発展',
      '医療DX政策 — マイナ保険証、電子処方箋、医療データ連携基盤の整備',
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
    trends: [
      'DX推進 — あらゆる業界でデジタルトランスフォーメーションが加速',
      'サステナビリティ経営 — ESG/SDGsへの対応が投資家・消費者双方から要求',
      'AI/自動化 — 業務プロセスの自動化・効率化による生産性向上',
      '人材不足対応 — 少子高齢化に伴う人手不足への技術的・組織的対応',
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
