'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api, shouldPollJob } from '@/lib/api'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function Phase2Page() {
  const params = useParams()
  const projectId = params.id as string
  const [selectedProposal, setSelectedProposal] = useState<string | null>(null)

  // Stub: in production, trigger phase2 job on mount and poll
  const proposals = [
    {
      label: 'SaaS_3seg',
      description: '3セグメント SaaS モデル（エンタープライズ/SMB/セルフサーブ）',
      confidence: 0.85,
      segments: ['エンタープライズ', 'SMB', 'セルフサーブ'],
    },
    {
      label: 'SaaS_2seg',
      description: '2セグメント SaaS モデル（B2B/B2C）',
      confidence: 0.72,
      segments: ['B2B', 'B2C'],
    },
    {
      label: 'Hybrid_3seg',
      description: 'ハイブリッド モデル（SaaS + コンサルティング + ライセンス）',
      confidence: 0.60,
      segments: ['SaaS', 'コンサルティング', 'ライセンス'],
    },
  ]

  return (
    <PhaseLayout
      phase={2}
      title="ビジネスモデル分析"
      subtitle="AIが提案する収益構造を選択してください"
      projectId={projectId}
    >
      <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
        {proposals.map((proposal) => (
          <button
            key={proposal.label}
            onClick={() => setSelectedProposal(proposal.label)}
            className={`text-left p-5 rounded-lg border-2 transition-all ${
              selectedProposal === proposal.label
                ? 'border-blue-500 bg-blue-50 shadow-md'
                : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-900">{proposal.label}</h3>
              <span className={`conf-badge ${
                proposal.confidence >= 0.8 ? 'conf-badge-high' :
                proposal.confidence >= 0.5 ? 'conf-badge-mid' : 'conf-badge-low'
              }`}>
                {Math.round(proposal.confidence * 100)}%
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-3">{proposal.description}</p>
            <div className="flex flex-wrap gap-1">
              {proposal.segments.map((seg) => (
                <span
                  key={seg}
                  className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
                >
                  {seg}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {selectedProposal && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700">
            <strong>{selectedProposal}</strong> を選択しました。
            次のフェーズに進むと、このモデルに基づいてテンプレートがマッピングされます。
          </p>
        </div>
      )}
    </PhaseLayout>
  )
}
