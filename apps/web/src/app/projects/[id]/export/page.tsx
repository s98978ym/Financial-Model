'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, shouldPollJob } from '@/lib/api'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

export default function ExportPage() {
  var params = useParams()
  var projectId = params.id as string
  var [scenarios, setScenarios] = useState(['base', 'best', 'worst'])
  var [jobId, setJobId] = useState<string | null>(null)
  var [includeNeedsReview, setIncludeNeedsReview] = useState(true)
  var [includeCaseDiff, setIncludeCaseDiff] = useState(true)

  var exportMutation = useMutation({
    mutationFn: function() {
      return api.exportExcel({
        project_id: projectId,
        scenarios: scenarios,
        options: {
          include_needs_review: includeNeedsReview,
          include_case_diff: includeCaseDiff,
          best_multipliers: { revenue: 1.2, cost: 0.9 },
          worst_multipliers: { revenue: 0.8, cost: 1.15 },
        },
      })
    },
    onSuccess: function(data: any) {
      setJobId(data.job_id)
    },
  })

  // Poll job status
  const { data: jobData } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => shouldPollJob(query.state.data),
  })

  const isGenerating = jobId && (jobData?.status === 'queued' || jobData?.status === 'running')
  const isComplete = jobData?.status === 'completed'
  const isFailed = jobData?.status === 'failed'
  const downloadUrl = isComplete ? api.downloadExcel(jobId!) : null

  return (
    <PhaseLayout
      phase={7}
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
              <input
                type="checkbox"
                checked={includeNeedsReview}
                onChange={function(e) { setIncludeNeedsReview(e.target.checked) }}
                className="rounded border-gray-300 text-blue-600"
              />
              needs_review.csv を含める
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeCaseDiff}
                onChange={function(e) { setIncludeCaseDiff(e.target.checked) }}
                className="rounded border-gray-300 text-blue-600"
              />
              ケース差分レポートを含める
            </label>
          </div>
        </div>

        {/* Export Button */}
        <button
          onClick={() => exportMutation.mutate()}
          disabled={exportMutation.isPending || !!isGenerating || scenarios.length === 0}
          className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {isGenerating ? `Excel 生成中... (${jobData?.progress || 0}%)` :
           exportMutation.isPending ? 'ジョブ作成中...' :
           'Excel をエクスポート'}
        </button>

        {/* Generating spinner */}
        {isGenerating && (
          <div className="mt-6 text-center">
            <div className="inline-block w-6 h-6 border-4 border-green-200 border-t-green-600 rounded-full animate-spin mb-2" />
            <p className="text-sm text-gray-500">Excel ファイルを生成しています...</p>
          </div>
        )}

        {/* Download ready */}
        {isComplete && downloadUrl && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-5">
            <h3 className="font-medium text-green-800 mb-3">生成完了</h3>
            <a
              href={downloadUrl}
              download
              className="inline-flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Excel ファイルをダウンロード
            </a>
            <p className="mt-2 text-xs text-green-600">
              ファイルはブラウザのダウンロードフォルダに保存されます
            </p>
          </div>
        )}

        {/* Error */}
        {(isFailed || exportMutation.isError) && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-700">
              エラー: {jobData?.error_msg || (exportMutation.error as Error)?.message || '不明なエラー'}
            </p>
            <button
              onClick={() => {
                setJobId(null)
                exportMutation.reset()
              }}
              className="mt-2 text-sm text-red-600 hover:underline"
            >
              再試行
            </button>
          </div>
        )}
      </div>
    </PhaseLayout>
  )
}
