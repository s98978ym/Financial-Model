/**
 * Archetype metadata and default configurations.
 */

import type {
  ArchetypeId,
  ArchetypeMeta,
  UnitEconomicsConfig,
  ConsultingConfig,
  AcademyConfig,
  SubscriptionConfig,
  MarketplaceConfig,
  UsageConfig,
  AdvertisingConfig,
  LicensingConfig,
  StaffingConfig,
  RentalConfig,
  FranchiseConfig,
  ArchetypeConfig,
} from './types'

// ---------------------------------------------------------------------------
// Archetype metadata registry
// ---------------------------------------------------------------------------

export var ARCHETYPES: ArchetypeMeta[] = [
  // ═══ 取引型 (Transaction-based) ═══
  {
    id: 'unit_economics',
    label: 'ユニットエコノミクス',
    description: '商品/SaaS型。SKU別の単価・購入頻度・CAC・LTVを設計',
    icon: 'U',
    color: 'bg-blue-500',
    textColor: 'text-blue-700',
    category: '取引型',
  },
  {
    id: 'consulting',
    label: 'コンサルティング',
    description: 'プロジェクト/受託型。SKU別の単価・原価(時給x時間)・件数を設計',
    icon: 'C',
    color: 'bg-emerald-500',
    textColor: 'text-emerald-700',
    category: '取引型',
  },
  {
    id: 'rental',
    label: 'レンタル/リース',
    description: '資産貸出型。保有資産の月額料金・台数・稼働率から収益を設計',
    icon: 'R',
    color: 'bg-stone-500',
    textColor: 'text-stone-700',
    category: '取引型',
  },
  // ═══ 継続型 (Recurring) ═══
  {
    id: 'subscription',
    label: 'サブスクリプション',
    description: '月額課金型。プラン別の月額・契約者数・解約率を設計',
    icon: 'S',
    color: 'bg-orange-500',
    textColor: 'text-orange-700',
    category: '継続型',
  },
  {
    id: 'usage',
    label: '従量課金',
    description: '利用量ベース型。ティア別の単価・無料枠・利用量から収益を設計',
    icon: '従',
    color: 'bg-teal-500',
    textColor: 'text-teal-700',
    category: '継続型',
  },
  {
    id: 'staffing',
    label: '人材派遣/SES',
    description: '人材提供型。職種別の月額単価・原価・稼働人数から収益を設計',
    icon: '人',
    color: 'bg-amber-500',
    textColor: 'text-amber-700',
    category: '継続型',
  },
  // ═══ 仲介型 (Intermediary) ═══
  {
    id: 'marketplace',
    label: 'マーケットプレイス',
    description: '取引仲介型。供給/需要の双方ユーザー数・取引額・手数料率を設計',
    icon: 'M',
    color: 'bg-cyan-500',
    textColor: 'text-cyan-700',
    category: '仲介型',
  },
  {
    id: 'advertising',
    label: '広告モデル',
    description: '広告収益型。MAU・PV・広告フォーマット別の単価・充填率を設計',
    icon: '広',
    color: 'bg-rose-500',
    textColor: 'text-rose-700',
    category: '仲介型',
  },
  // ═══ 権利・教育型 (Rights & Education) ═══
  {
    id: 'licensing',
    label: 'ライセンス',
    description: '知的財産型。ライセンス料・保守料率・更新率から収益を設計',
    icon: 'L',
    color: 'bg-indigo-500',
    textColor: 'text-indigo-700',
    category: '権利・教育型',
  },
  {
    id: 'franchise',
    label: 'フランチャイズ',
    description: 'FC展開型。加盟金・ロイヤリティ率・店舗数から収益を設計',
    icon: 'F',
    color: 'bg-lime-600',
    textColor: 'text-lime-700',
    category: '権利・教育型',
  },
  {
    id: 'academy',
    label: 'アカデミー',
    description: 'スクール/教育型。ティア別の受講料・修了率・進級フローを設計',
    icon: 'A',
    color: 'bg-purple-500',
    textColor: 'text-purple-700',
    category: '権利・教育型',
  },
]

export function getArchetypeMeta(id: ArchetypeId): ArchetypeMeta {
  return ARCHETYPES.find(function(a) { return a.id === id })!
}

// ---------------------------------------------------------------------------
// Default configs
// ---------------------------------------------------------------------------

var _id = 0
function uid(): string { return 'sku_' + (++_id) + '_' + Date.now().toString(36) }

export function defaultUnitEconomicsConfig(): UnitEconomicsConfig {
  return {
    skus: [
      { id: uid(), name: 'プランA', price: 50000, items_per_txn: 1, txns_per_person: 1, annual_purchases: 12 },
      { id: uid(), name: 'プランB', price: 100000, items_per_txn: 1, txns_per_person: 1, annual_purchases: 12 },
    ],
    cac: 30000,
    monthly_churn: 0.03,
    avg_contract_months: 24,
  }
}

export function defaultConsultingConfig(): ConsultingConfig {
  return {
    skus: [
      { id: uid(), name: '戦略コンサル', unit_price: 5000000, hourly_rate: 15000, standard_hours: 200, cac: 200000, quantities: [10, 15, 22, 30, 40] },
      { id: uid(), name: 'DX推進', unit_price: 3000000, hourly_rate: 12000, standard_hours: 160, cac: 150000, quantities: [8, 12, 18, 25, 35] },
    ],
  }
}

export function defaultAcademyConfig(): AcademyConfig {
  return {
    tiers: [
      { id: uid(), level: 'C', name: '入門コース', price: 50000, description: '基礎知識の習得', completion_rate: 0.85, certification_rate: 0.70, advancement_rate: 0.50, students: [200, 350, 500, 700, 1000] },
      { id: uid(), level: 'B', name: '実践コース', price: 150000, description: '実務スキルの習得', completion_rate: 0.80, certification_rate: 0.65, advancement_rate: 0.40, students: [80, 150, 230, 330, 470] },
      { id: uid(), level: 'A', name: '上級コース', price: 300000, description: '専門性の深化', completion_rate: 0.75, certification_rate: 0.60, advancement_rate: 0.30, students: [25, 50, 85, 130, 190] },
      { id: uid(), level: 'S', name: 'エキスパート', price: 500000, description: '指導者・講師養成', completion_rate: 0.70, certification_rate: 0.55, advancement_rate: 0, students: [5, 12, 22, 38, 58] },
    ],
  }
}

export function defaultSubscriptionConfig(): SubscriptionConfig {
  return {
    plans: [
      { id: uid(), name: 'ベーシック', monthly_price: 980, subscribers: [500, 1200, 2500, 4500, 7000], churn_rate: 0.05 },
      { id: uid(), name: 'プロ', monthly_price: 2980, subscribers: [100, 300, 700, 1400, 2500], churn_rate: 0.03 },
      { id: uid(), name: 'エンタープライズ', monthly_price: 9800, subscribers: [10, 30, 70, 130, 220], churn_rate: 0.02 },
    ],
    trial_conversion_rate: 0.15,
  }
}

export function defaultMarketplaceConfig(): MarketplaceConfig {
  return {
    supply: { id: uid(), name: '出品者', users: [50, 120, 250, 450, 700], avg_txn_value: 15000, txns_per_user: 8 },
    demand: { id: uid(), name: '購入者', users: [200, 600, 1500, 3500, 7000], avg_txn_value: 15000, txns_per_user: 3 },
    take_rate: 0.10,
  }
}

export function defaultUsageConfig(): UsageConfig {
  return {
    tiers: [
      { id: uid(), name: 'スタンダード', unit_price: 0.5, unit_label: 'APIコール', included_units: 10000, users: [200, 500, 1200, 2500, 5000], avg_usage_per_user: 25000 },
      { id: uid(), name: 'プレミアム', unit_price: 0.3, unit_label: 'APIコール', included_units: 100000, users: [20, 60, 150, 300, 600], avg_usage_per_user: 200000 },
    ],
  }
}

export function defaultAdvertisingConfig(): AdvertisingConfig {
  return {
    formats: [
      { id: uid(), name: 'ディスプレイ広告', pricing_model: 'cpm', rate: 300, fill_rate: 0.65 },
      { id: uid(), name: '動画広告', pricing_model: 'cpm', rate: 800, fill_rate: 0.45 },
      { id: uid(), name: 'ネイティブ広告', pricing_model: 'cpc', rate: 50, fill_rate: 0.55 },
    ],
    monthly_active_users: [5000, 15000, 40000, 80000, 150000],
    avg_pageviews_per_user: 12,
  }
}

export function defaultLicensingConfig(): LicensingConfig {
  return {
    products: [
      { id: uid(), name: 'スタンダード版', license_fee: 500000, maintenance_rate: 0.18, licenses: [20, 45, 80, 130, 200] },
      { id: uid(), name: 'エンタープライズ版', license_fee: 2000000, maintenance_rate: 0.15, licenses: [3, 8, 15, 25, 40] },
    ],
    renewal_rate: 0.85,
  }
}

export function defaultStaffingConfig(): StaffingConfig {
  return {
    categories: [
      { id: uid(), name: 'シニアエンジニア', monthly_rate: 900000, cost_rate: 650000, headcount: [5, 12, 25, 40, 60] },
      { id: uid(), name: 'ミドルエンジニア', monthly_rate: 700000, cost_rate: 500000, headcount: [10, 25, 50, 80, 120] },
      { id: uid(), name: 'ジュニアエンジニア', monthly_rate: 500000, cost_rate: 350000, headcount: [8, 20, 40, 65, 100] },
    ],
    utilization_rate: 0.85,
  }
}

export function defaultRentalConfig(): RentalConfig {
  return {
    assets: [
      { id: uid(), name: '機器A', monthly_fee: 50000, acquisition_cost: 800000, units: [20, 50, 100, 180, 300] },
      { id: uid(), name: '機器B', monthly_fee: 30000, acquisition_cost: 400000, units: [30, 80, 160, 280, 450] },
    ],
    utilization_rate: 0.80,
    avg_contract_months: 12,
  }
}

export function defaultFranchiseConfig(): FranchiseConfig {
  return {
    initial_fee: 5000000,
    royalty_rate: 0.05,
    stores: [3, 8, 18, 35, 60],
    avg_store_monthly_revenue: 8000000,
    support_cost_per_store: 200000,
  }
}

export function getDefaultConfig(archetype: ArchetypeId): ArchetypeConfig {
  switch (archetype) {
    case 'unit_economics': return defaultUnitEconomicsConfig()
    case 'consulting': return defaultConsultingConfig()
    case 'academy': return defaultAcademyConfig()
    case 'subscription': return defaultSubscriptionConfig()
    case 'marketplace': return defaultMarketplaceConfig()
    case 'usage': return defaultUsageConfig()
    case 'advertising': return defaultAdvertisingConfig()
    case 'licensing': return defaultLicensingConfig()
    case 'staffing': return defaultStaffingConfig()
    case 'rental': return defaultRentalConfig()
    case 'franchise': return defaultFranchiseConfig()
  }
}
