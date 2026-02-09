'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ParameterGrid } from '@/components/grid/ParameterGrid'
import { EvidencePanel } from '@/components/grid/EvidencePanel'
import { CompletionChecklist } from '@/components/progress/CompletionChecklist'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function Phase4Page() {
  const params = useParams()
  const projectId = params.id as string
  const [selectedCell, setSelectedCell] = useState<any>(null)

  // In production: fetch from API
  const { data: designResult, isLoading } = useQuery({
    queryKey: ['phase4', projectId],
    queryFn: async () => {
      // Stub data for development
      return {
        cell_assignments: [
          {
            sheet: 'PL設計', cell: 'B5', concept: 'total_revenue',
            category: 'revenue', segment: null, period: 'FY1', unit: '円',
            confidence: 0.92, label_match: '売上高', warnings: [],
            evidence: { quote: '初年度売上目標は3億円', page: 5 },
          },
          {
            sheet: 'PL設計', cell: 'B6', concept: 'cogs_ratio',
            category: 'cost', segment: null, period: 'FY1', unit: '%',
            confidence: 0.65, label_match: '原価率', warnings: [],
            evidence: { quote: '売上原価率は30%程度を想定', page: 8 },
          },
          {
            sheet: 'PL設計', cell: 'B12', concept: 'opex_personnel',
            category: 'opex', segment: null, period: 'FY1', unit: '円',
            confidence: 0.30, label_match: '人件費', warnings: ['evidence_not_found_in_document'],
            evidence: { quote: '', page: null },
          },
          {
            sheet: '収益モデル1', cell: 'C8', concept: 'unit_price',
            category: 'revenue', segment: 'エンタープライズ', period: 'FY1', unit: '円',
            confidence: 0.88, label_match: '月額単価', warnings: [],
            evidence: { quote: '月額50万円のエンタープライズプラン', page: 3 },
          },
          {
            sheet: '収益モデル1', cell: 'C10', concept: 'churn_rate',
            category: 'revenue', segment: 'エンタープライズ', period: 'FY1', unit: '%',
            confidence: 0.55, label_match: '月次解約率', warnings: [],
            evidence: { quote: '業界平均の解約率を想定', page: null },
          },
        ],
        unmapped_cells: [
          { sheet: 'PL設計', cell: 'B20', reason: 'ラベルが曖昧' },
        ],
      }
    },
  })

  const assignments = designResult?.cell_assignments || []
  const unmapped = designResult?.unmapped_cells || []

  const stats = {
    total: assignments.length + unmapped.length,
    mapped: assignments.length,
    highConf: assignments.filter((a: any) => a.confidence >= 0.8).length,
    midConf: assignments.filter((a: any) => a.confidence >= 0.5 && a.confidence < 0.8).length,
    lowConf: assignments.filter((a: any) => a.confidence < 0.5).length,
    docSource: assignments.filter((a: any) => !a.warnings?.length).length,
  }

  return (
    <PhaseLayout
      phase={4}
      title="モデル設計"
      subtitle="セルとビジネスコンセプトのマッピング"
      projectId={projectId}
    >
      <div className="flex gap-6">
        {/* Main Grid */}
        <div className="flex-1 min-w-0">
          <ParameterGrid
            data={assignments}
            columns={[
              { field: 'sheet', headerName: 'シート', width: 120 },
              { field: 'cell', headerName: 'セル', width: 70 },
              { field: 'label_match', headerName: 'ラベル', width: 120 },
              { field: 'concept', headerName: 'コンセプト', width: 150, editable: true },
              { field: 'category', headerName: 'カテゴリ', width: 100 },
              { field: 'segment', headerName: 'セグメント', width: 130 },
              { field: 'period', headerName: '期間', width: 70 },
              { field: 'confidence', headerName: '確信度', width: 90, type: 'confidence' },
            ]}
            onCellClick={(cell: any) => setSelectedCell(cell)}
          />
        </div>

        {/* Evidence Side Panel */}
        <div className="w-80 flex-shrink-0">
          <EvidencePanel cell={selectedCell} />
        </div>
      </div>

      {/* Completion Checklist */}
      <div className="mt-6">
        <CompletionChecklist
          stats={stats}
          nextActions={[
            unmapped.length > 0 ? `未マッピング ${unmapped.length} セルを確認` : null,
            stats.lowConf > 0 ? `低確信度 ${stats.lowConf} セルのエビデンスを補完` : null,
            'Phase 5 (パラメータ抽出) へ進む',
          ].filter(Boolean) as string[]}
        />
      </div>
    </PhaseLayout>
  )
}
