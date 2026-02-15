/**
 * Revenue model archetype types.
 *
 * Each business segment can be configured with a specific revenue logic
 * archetype (unit economics, consulting, academy, subscription, marketplace).
 */

// ---------------------------------------------------------------------------
// Archetype IDs
// ---------------------------------------------------------------------------

export type ArchetypeId =
  | 'unit_economics'
  | 'consulting'
  | 'academy'
  | 'subscription'
  | 'marketplace'

export interface ArchetypeMeta {
  id: ArchetypeId
  label: string
  description: string
  icon: string
  color: string       // Tailwind bg class
  textColor: string   // Tailwind text class
}

// ---------------------------------------------------------------------------
// Unit Economics model
// ---------------------------------------------------------------------------

export interface UnitEconSKU {
  id: string
  name: string
  price: number             // 単価(税抜)
  items_per_txn: number     // 商品数/取引
  txns_per_person: number   // 取引回数/人
  annual_purchases: number  // 年間購入回数/人
}

export interface UnitEconomicsConfig {
  skus: UnitEconSKU[]
  cac: number               // 顧客獲得コスト
  monthly_churn: number     // 月次解約率 (0-1)
  avg_contract_months: number // 平均契約期間(月)
}

// ---------------------------------------------------------------------------
// Consulting model
// ---------------------------------------------------------------------------

export interface ConsultingSKU {
  id: string
  name: string
  unit_price: number        // 単価
  hourly_rate: number       // 時給
  standard_hours: number    // 標準時間
  cac: number               // 顧客獲得コスト
  quantities: number[]      // FY1-FY5 件数
}

export interface ConsultingConfig {
  skus: ConsultingSKU[]
}

// ---------------------------------------------------------------------------
// Academy model
// ---------------------------------------------------------------------------

export interface AcademyTier {
  id: string
  level: string             // C, B, A, S
  name: string
  price: number             // 受講料
  description: string
  completion_rate: number   // 修了率 (0-1)
  certification_rate: number // 認定率 (0-1)
  advancement_rate: number  // 進級率 (0-1)
  students: number[]        // FY1-FY5 受講者数
}

export interface AcademyConfig {
  tiers: AcademyTier[]
}

// ---------------------------------------------------------------------------
// Subscription model
// ---------------------------------------------------------------------------

export interface SubscriptionPlan {
  id: string
  name: string
  monthly_price: number
  subscribers: number[]     // FY1-FY5
  churn_rate: number        // 月次解約率 (0-1)
}

export interface SubscriptionConfig {
  plans: SubscriptionPlan[]
  trial_conversion_rate: number
}

// ---------------------------------------------------------------------------
// Marketplace model
// ---------------------------------------------------------------------------

export interface MarketplaceSide {
  id: string
  name: string
  users: number[]           // FY1-FY5
  avg_txn_value: number
  txns_per_user: number
}

export interface MarketplaceConfig {
  supply: MarketplaceSide
  demand: MarketplaceSide
  take_rate: number         // 手数料率 (0-1)
}

// ---------------------------------------------------------------------------
// Union type
// ---------------------------------------------------------------------------

export type ArchetypeConfig =
  | UnitEconomicsConfig
  | ConsultingConfig
  | AcademyConfig
  | SubscriptionConfig
  | MarketplaceConfig

export interface SegmentRevenueModel {
  segment_name: string
  archetype: ArchetypeId | null
  config: ArchetypeConfig | null
}

// ---------------------------------------------------------------------------
// Computed helpers
// ---------------------------------------------------------------------------

export function computeUnitEconRevPerPerson(sku: UnitEconSKU): number {
  return sku.price * sku.items_per_txn * sku.txns_per_person * sku.annual_purchases
}

export function computeUnitEconLTV(config: UnitEconomicsConfig): number {
  if (config.skus.length === 0) return 0
  var avgRevPerPerson = config.skus.reduce(function(sum, s) { return sum + computeUnitEconRevPerPerson(s) }, 0) / config.skus.length
  var months = config.monthly_churn > 0 ? 1 / config.monthly_churn : config.avg_contract_months
  return avgRevPerPerson * (months / 12)
}

export function computeUnitEconLTVCACRatio(config: UnitEconomicsConfig): number {
  if (config.cac === 0) return 0
  return computeUnitEconLTV(config) / config.cac
}

export function computeUnitEconPaybackMonths(config: UnitEconomicsConfig): number {
  var ltv = computeUnitEconLTV(config)
  var months = config.monthly_churn > 0 ? 1 / config.monthly_churn : config.avg_contract_months
  if (ltv === 0) return 0
  return (config.cac / ltv) * months
}

export function computeConsultingDeliveryCost(sku: ConsultingSKU): number {
  return sku.hourly_rate * sku.standard_hours
}

export function computeConsultingGrossMargin(sku: ConsultingSKU): number {
  if (sku.unit_price === 0) return 0
  return 1 - (computeConsultingDeliveryCost(sku) / sku.unit_price)
}
