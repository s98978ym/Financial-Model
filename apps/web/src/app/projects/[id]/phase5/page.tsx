'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { ParameterGrid } from '@/components/grid/ParameterGrid'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { CompletionChecklist } from '@/components/progress/CompletionChecklist'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function Phase5Page() {
  const params = useParams()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)

  // Stub data for development
  const extractions = [
    {
      sheet: '収益モデル1', cell: 'C8', value: 50000,
      original_text: '月額5万円', source: 'document', confidence: 0.91,
      evidence: { quote: 'エンタープライズプランは月額5万円から', page: 3, rationale: '直接記載' },
      warnings: [],
    },
    {
      sheet: '収益モデル1', cell: 'C10', value: 0.05,
      original_text: '月次解約率5%', source: 'inferred', confidence: 0.55,
      evidence: { quote: '業界平均の解約率を想定', page: null, rationale: 'SaaS業界平均から推定' },
      warnings: [],
    },
    {
      sheet: 'PL設計', cell: 'B12', value: 30000000,
      original_text: '人件費3000万円', source: 'document', confidence: 0.82,
      evidence: { quote: '初年度の人件費は約3000万円', page: 7, rationale: '直接記載' },
      warnings: [],
    },
    {
      sheet: 'PL設計', cell: 'B14', value: 5000000,
      original_text: '', source: 'default', confidence: 0.15,
      evidence: { quote: '文書に記載なし', page: null, rationale: 'デフォルト値を使用' },
      warnings: ['evidence_missing'],
    },
  ]

  const stats = {
    total: extractions.length + 2, // +2 for unmapped
    mapped: extractions.length,
    highConf: extractions.filter((e) => e.confidence >= 0.8).length,
    midConf: extractions.filter((e) => e.confidence >= 0.5 && e.confidence < 0.8).length,
    lowConf: extractions.filter((e) => e.confidence < 0.5).length,
    docSource: extractions.filter((e) => e.source === 'document').length,
  }

  return (
    <PhaseLayout
      phase={5}
      title="パラメータ抽出"
      subtitle="文書から抽出した値の確認・編集"
      projectId={projectId}
    >
      <div className="flex gap-6">
        <div className="flex-1 min-w-0">
          <ParameterGrid
            data={extractions}
            columns={[
              { field: 'sheet', headerName: 'シート', width: 120 },
              { field: 'cell', headerName: 'セル', width: 70 },
              { field: 'value', headerName: '値', width: 120, editable: true },
              { field: 'original_text', headerName: '原文', width: 150 },
              { field: 'source', headerName: 'ソース', width: 90, type: 'source' },
              { field: 'confidence', headerName: '確信度', width: 90, type: 'confidence' },
            ]}
            onCellClick={(cell: any) => setSelectedCell(cell)}
          />
        </div>

        <div className="w-80 flex-shrink-0">
          <EvidencePanel cell={selectedCell} />
        </div>
      </div>

      <div className="mt-6">
        <CompletionChecklist
          stats={stats}
          nextActions={[
            stats.lowConf > 0 ? `低確信度 ${stats.lowConf} セルの値を確認` : null,
            'シナリオ プレイグラウンドでPLを確認',
            'Excel エクスポート',
          ].filter(Boolean) as string[]}
        />
      </div>
    </PhaseLayout>
  )
}
