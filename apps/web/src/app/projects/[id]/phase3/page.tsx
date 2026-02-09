'use client'

import { useParams } from 'next/navigation'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function Phase3Page() {
  const params = useParams()
  const projectId = params.id as string

  // Stub: sheet-to-segment mapping visualization
  const mappings = [
    { sheet: 'シミュレーション分析', purpose: 'assumptions', segment: null, confidence: 0.95 },
    { sheet: 'PL設計', purpose: 'pl_summary', segment: null, confidence: 0.95 },
    { sheet: '収益モデル1', purpose: 'revenue_model', segment: 'エンタープライズ', confidence: 0.88 },
    { sheet: '収益モデル2', purpose: 'revenue_model', segment: 'SMB', confidence: 0.82 },
    { sheet: '収益モデル3', purpose: 'revenue_model', segment: 'セルフサーブ', confidence: 0.75 },
  ]

  const purposeLabels: Record<string, string> = {
    revenue_model: '収益モデル',
    pl_summary: 'PL集計',
    assumptions: '前提条件',
    cost_detail: 'コスト詳細',
    headcount: '人員計画',
  }

  return (
    <PhaseLayout
      phase={3}
      title="テンプレート構造マッピング"
      subtitle="シートとビジネスセグメントの対応関係"
      projectId={projectId}
    >
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">シート名</th>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">目的</th>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">対応セグメント</th>
              <th className="text-right px-4 py-3 text-gray-500 font-medium">確信度</th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((m) => (
              <tr key={m.sheet} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{m.sheet}</td>
                <td className="px-4 py-3">
                  <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded">
                    {purposeLabels[m.purpose] || m.purpose}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{m.segment || '—'}</td>
                <td className="px-4 py-3 text-right">
                  <span className={`conf-badge ${
                    m.confidence >= 0.8 ? 'conf-badge-high' :
                    m.confidence >= 0.5 ? 'conf-badge-mid' : 'conf-badge-low'
                  }`}>
                    {Math.round(m.confidence * 100)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PhaseLayout>
  )
}
