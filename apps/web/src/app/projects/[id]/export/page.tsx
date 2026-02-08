'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function ExportPage() {
  const params = useParams()
  const projectId = params.id as string
  const [scenarios, setScenarios] = useState(['base', 'best', 'worst'])

  const exportMutation = useMutation({
    mutationFn: () =>
      api.exportExcel({
        project_id: projectId,
        scenarios,
        options: {
          include_needs_review: true,
          include_case_diff: true,
          best_multipliers: { revenue: 1.2, cost: 0.9 },
          worst_multipliers: { revenue: 0.8, cost: 1.15 },
        },
      }),
  })

  return (
    <PhaseLayout
      phase={6}
      title="Excel エクスポート"
      subtitle="最終的な収益計画を Excel ファイルとしてダウンロード"
      projectId={projectId}
    >
      <div className="max-w-xl mx-auto">
        {/* Scenario Selection */}
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <h3 className="font-medium text-gray-900 mb-3">シナリオ選択</h3>
          <div className="space-y-2">
            {['base', 'best', 'worst'].map((s) => (
              <label key={s} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={scenarios.includes(s)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setScenarios([...scenarios, s])
                    } else {
                      setScenarios(scenarios.filter((x) => x !== s))
                    }
                  }}
                  className="rounded border-gray-300 text-blue-600"
                />
                <span className="text-sm text-gray-700 capitalize">{s}</span>
                <span className="text-xs text-gray-400">
                  {s === 'base' ? '基本シナリオ' :
                   s === 'best' ? '売上+20%/コスト-10%' : '売上-20%/コスト+15%'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Export Options */}
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <h3 className="font-medium text-gray-900 mb-3">出力オプション</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded border-gray-300 text-blue-600" />
              needs_review.csv を含める
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded border-gray-300 text-blue-600" />
              ケース差分レポートを含める
            </label>
          </div>
        </div>

        {/* Export Button */}
        <button
          onClick={() => exportMutation.mutate()}
          disabled={exportMutation.isPending || scenarios.length === 0}
          className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {exportMutation.isPending ? 'Excel 生成中...' : 'Excel をエクスポート'}
        </button>

        {/* Result */}
        {exportMutation.isSuccess && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <h3 className="font-medium text-green-800 mb-2">生成完了</h3>
            <p className="text-sm text-green-700">
              ジョブが作成されました。ダウンロードリンクが準備でき次第、こちらに表示されます。
            </p>
          </div>
        )}

        {exportMutation.isError && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-700">
              エラー: {(exportMutation.error as Error).message}
            </p>
          </div>
        )}
      </div>
    </PhaseLayout>
  )
}
