/**
 * Auto-suggest revenue model archetype from Phase 2 segment data.
 *
 * Uses keyword matching on segment name, model_type, revenue_formula,
 * and revenue_drivers to recommend the most appropriate archetype.
 */

import type { ArchetypeId } from './types'

interface SegmentHint {
  name: string
  model_type?: string
  revenue_formula?: string
  revenue_drivers?: Array<{ name: string; unit?: string; description?: string }>
  key_assumptions?: string[]
}

interface SuggestionRule {
  archetype: ArchetypeId
  score: number
}

// Keyword groups per archetype (JP + EN)
var KEYWORD_MAP: Record<ArchetypeId, string[]> = {
  subscription: ['subscription', 'サブスクリプション', 'サブスク', '月額', '月額課金', 'MRR', 'ARR', '定額', '年額', '月次課金', 'recurring', 'SaaS'],
  usage: ['従量', '従量課金', 'usage', 'pay-per-use', 'API', 'リクエスト', '利用量', 'consumption', 'メータリング', 'GB', 'データ量'],
  unit_economics: ['ユニットエコノミクス', 'unit economics', 'EC', 'eコマース', '物販', '商品販売', 'D2C', 'B2C', '商品数', 'SKU', '単価×数量', 'LTV', 'CAC'],
  consulting: ['コンサルティング', 'コンサル', '受託', 'プロジェクト', '案件', 'SI', 'システム開発', 'professional service', 'advisory', '業務委託', 'BPO'],
  academy: ['アカデミー', '教育', '研修', 'スクール', '講座', '受講', '資格', '認定', 'コース', '学習', 'education', 'training', 'academy', 'certification'],
  marketplace: ['マーケットプレイス', 'marketplace', 'プラットフォーム', '仲介', 'マッチング', '手数料', 'テイクレート', 'take rate', 'GMV', 'C2C', '出品'],
  advertising: ['広告', 'advertising', 'ad', 'CPM', 'CPC', 'CPA', 'インプレッション', 'クリック', 'メディア', 'アドネットワーク', 'DSP', 'SSP'],
  licensing: ['ライセンス', 'license', 'IP', '知的財産', '特許', 'ロイヤリティ', '使用許諾', 'OEM', '保守'],
  staffing: ['人材派遣', 'SES', '派遣', '常駐', '技術者派遣', 'staffing', 'outsourcing', '稼働人数', '時間単価', 'エンジニア派遣', '人月'],
  rental: ['レンタル', 'リース', 'rental', 'lease', '貸出', '機器貸出', '資産運用', 'シェアリング', '利用期間'],
  franchise: ['フランチャイズ', 'franchise', 'FC', '加盟', '加盟店', 'チェーン', '多店舗', 'ロイヤリティ'],
}

// model_type direct mapping (strongest signal)
var MODEL_TYPE_MAP: Record<string, ArchetypeId> = {
  subscription: 'subscription',
  saas: 'subscription',
  'サブスクリプション': 'subscription',
  'サブスク': 'subscription',
  usage: 'usage',
  'usage-based': 'usage',
  '従量課金': 'usage',
  transaction: 'unit_economics',
  ec: 'unit_economics',
  ecommerce: 'unit_economics',
  '物販': 'unit_economics',
  project: 'consulting',
  consulting: 'consulting',
  '受託': 'consulting',
  'コンサルティング': 'consulting',
  marketplace: 'marketplace',
  'マーケットプレイス': 'marketplace',
  platform: 'marketplace',
  advertising: 'advertising',
  ad: 'advertising',
  '広告': 'advertising',
  license: 'licensing',
  licensing: 'licensing',
  'ライセンス': 'licensing',
  education: 'academy',
  training: 'academy',
  academy: 'academy',
  '教育': 'academy',
  staffing: 'staffing',
  ses: 'staffing',
  '人材派遣': 'staffing',
  rental: 'rental',
  lease: 'rental',
  'レンタル': 'rental',
  franchise: 'franchise',
  fc: 'franchise',
  'フランチャイズ': 'franchise',
}

function normalizeText(text: string): string {
  return text.toLowerCase().replace(/[\s\-_]/g, '')
}

export function suggestArchetype(segment: SegmentHint): { archetype: ArchetypeId; confidence: number } | null {
  var scores: Record<string, number> = {}

  // Initialize scores
  var archetypes: ArchetypeId[] = ['unit_economics', 'consulting', 'academy', 'subscription', 'marketplace',
    'usage', 'advertising', 'licensing', 'staffing', 'rental', 'franchise']
  archetypes.forEach(function(a) { scores[a] = 0 })

  // 1. Direct model_type match (strongest signal: +10)
  if (segment.model_type) {
    var normalized = normalizeText(segment.model_type)
    // Try exact match first
    Object.keys(MODEL_TYPE_MAP).forEach(function(key) {
      if (normalized === normalizeText(key) || normalized.indexOf(normalizeText(key)) >= 0) {
        scores[MODEL_TYPE_MAP[key]] += 10
      }
    })
  }

  // 2. Keyword matching on segment name (+5 per match)
  if (segment.name) {
    var nameLower = segment.name.toLowerCase()
    archetypes.forEach(function(arch) {
      KEYWORD_MAP[arch].forEach(function(kw) {
        if (nameLower.indexOf(kw.toLowerCase()) >= 0) {
          scores[arch] += 5
        }
      })
    })
  }

  // 3. Keyword matching on revenue_formula (+3 per match)
  if (segment.revenue_formula) {
    var formulaLower = segment.revenue_formula.toLowerCase()
    archetypes.forEach(function(arch) {
      KEYWORD_MAP[arch].forEach(function(kw) {
        if (formulaLower.indexOf(kw.toLowerCase()) >= 0) {
          scores[arch] += 3
        }
      })
    })
  }

  // 4. Revenue driver names (+4 per match)
  if (segment.revenue_drivers && segment.revenue_drivers.length > 0) {
    segment.revenue_drivers.forEach(function(driver) {
      var driverText = (driver.name + ' ' + (driver.description || '') + ' ' + (driver.unit || '')).toLowerCase()
      archetypes.forEach(function(arch) {
        KEYWORD_MAP[arch].forEach(function(kw) {
          if (driverText.indexOf(kw.toLowerCase()) >= 0) {
            scores[arch] += 4
          }
        })
      })
    })
  }

  // 5. Key assumptions (+2 per match)
  if (segment.key_assumptions && segment.key_assumptions.length > 0) {
    var assumptionsText = segment.key_assumptions.join(' ').toLowerCase()
    archetypes.forEach(function(arch) {
      KEYWORD_MAP[arch].forEach(function(kw) {
        if (assumptionsText.indexOf(kw.toLowerCase()) >= 0) {
          scores[arch] += 2
        }
      })
    })
  }

  // Find best match
  var bestArch: ArchetypeId = 'unit_economics'
  var bestScore = 0
  archetypes.forEach(function(arch) {
    if (scores[arch] > bestScore) {
      bestScore = scores[arch]
      bestArch = arch
    }
  })

  // Need minimum score of 3 to suggest
  if (bestScore < 3) return null

  // Confidence: normalize score to 0-1 range (cap at 20 for max confidence)
  var confidence = Math.min(bestScore / 20, 1.0)

  return { archetype: bestArch, confidence: confidence }
}
