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
  ArchetypeConfig,
} from './types'

// ---------------------------------------------------------------------------
// Archetype metadata registry
// ---------------------------------------------------------------------------

export var ARCHETYPES: ArchetypeMeta[] = [
  {
    id: 'unit_economics',
    label: 'ユニットエコノミクス',
    description: '商品/SaaS型。SKU別の単価・購入頻度・CAC・LTVを設計',
    icon: 'U',
    color: 'bg-blue-500',
    textColor: 'text-blue-700',
  },
  {
    id: 'consulting',
    label: 'コンサルティング',
    description: 'プロジェクト/受託型。SKU別の単価・原価(時給x時間)・件数を設計',
    icon: 'C',
    color: 'bg-emerald-500',
    textColor: 'text-emerald-700',
  },
  {
    id: 'academy',
    label: 'アカデミー',
    description: 'スクール/教育型。ティア別の受講料・修了率・進級フローを設計',
    icon: 'A',
    color: 'bg-purple-500',
    textColor: 'text-purple-700',
  },
  {
    id: 'subscription',
    label: 'サブスクリプション',
    description: '月額課金型。プラン別の月額・契約者数・解約率を設計',
    icon: 'S',
    color: 'bg-orange-500',
    textColor: 'text-orange-700',
  },
  {
    id: 'marketplace',
    label: 'マーケットプレイス',
    description: '取引仲介型。供給/需要の双方ユーザー数・取引額・手数料率を設計',
    icon: 'M',
    color: 'bg-cyan-500',
    textColor: 'text-cyan-700',
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

export function getDefaultConfig(archetype: ArchetypeId): ArchetypeConfig {
  switch (archetype) {
    case 'unit_economics': return defaultUnitEconomicsConfig()
    case 'consulting': return defaultConsultingConfig()
    case 'academy': return defaultAcademyConfig()
    case 'subscription': return defaultSubscriptionConfig()
    case 'marketplace': return defaultMarketplaceConfig()
  }
}
