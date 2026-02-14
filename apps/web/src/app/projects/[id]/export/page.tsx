'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, shouldPollJob } from '@/lib/api'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

var DEFAULT_PARAMS: Record<string, number> = {
  revenue_fy1: 100_000_000,
  growth_rate: 0.30,
  cogs_rate: 0.30,
  opex_base: 80_000_000,
  opex_growth: 0.10,
}

function formatYen(v: number): string {
  if (v >= 100_000_000) return (v / 100_000_000).toFixed(1) + ' 億円'
  if (v >= 10_000) return (v / 10_000).toFixed(0) + ' 万円'
  return v.toLocaleString() + ' 円'
}

function formatPct(v: number): string {
  return (v * 100).toFixed(0) + '%'
}

export default function ExportPage() {
  var params = useParams()
  var projectId = params.id as string
  var [scenarios, setScenarios] = useState(['base', 'best', 'worst'])
  var [jobId, setJobId] = useState<string | null>(null)
  var [includeNeedsReview, setIncludeNeedsReview] = useState(true)
  var [includeCaseDiff, setIncludeCaseDiff] = useState(true)
  var [sgaRdMode, setSgaRdMode] = useState<'inline' | 'separate'>('inline')
  var [currentParams, setCurrentParams] = useState<Record<string, number>>(DEFAULT_PARAMS)
  var [paramsLoaded, setParamsLoaded] = useState(false)

  // Load current model parameters from recalc (Phase 5 + Phase 6 edits merged)
  var recalcQuery = useQuery({
    queryKey: ['recalc-export', projectId],
    queryFn: function() {
      return api.recalc({
        project_id: projectId,
        parameters: {},
        scenario: 'base',
      })
    },
    enabled: !!projectId,
  })

  // When recalc returns, extract the actual parameters
  useEffect(function() {
    if (recalcQuery.data && !paramsLoaded) {
      var src = recalcQuery.data.source_params || {}
      var merged: Record<string, number> = {}
      Object.keys(DEFAULT_PARAMS).forEach(function(key) {
        merged[key] = (src[key] != null) ? Number(src[key]) : DEFAULT_PARAMS[key]
      })
      setCurrentParams(merged)
      setParamsLoaded(true)
    }
  }, [recalcQuery.data, paramsLoaded])

  var exportMutation = useMutation({
    mutationFn: function() {
      return api.exportExcel({
        project_id: projectId,
        parameters: currentParams,
        scenarios: scenarios,
        options: {
          include_needs_review: includeNeedsReview,
          include_case_diff: includeCaseDiff,
          sga_rd_mode: sgaRdMode,
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
  var jobQuery = useQuery({
    queryKey: ['job', jobId],
    queryFn: function() { return api.getJob(jobId!) },
    enabled: !!jobId,
    refetchInterval: function(query: any) { return shouldPollJob(query.state.data) },
  })
  var jobData = jobQuery.data

  var isGenerating = jobId && (jobData?.status === 'queued' || jobData?.status === 'running')
  var isComplete = jobData?.status === 'completed'
  var isFailed = jobData?.status === 'failed'
  var downloadUrl = isComplete ? api.downloadExcel(jobId!) : null

  // PL preview from the loaded parameters
  var plPreview = recalcQuery.data?.pl_summary

  return (
    <PhaseLayout
      phase={7}
      title="Excel エクスポート"
      subtitle="最終的な収益計画を Excel ファイルとしてダウンロード"
      projectId={projectId}
    >
      <div className="max-w-2xl mx-auto">
        {/* Current Model Settings Summary */}
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-5 mb-6">
          <h3 className="font-medium text-blue-900 mb-3">現在のモデル設定（PL反映値）</h3>
          {recalcQuery.isLoading ? (
            <p className="text-sm text-blue-600">モデルパラメータを読み込み中...</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="bg-white rounded p-2.5 border border-blue-100">
                <div className="text-xs text-gray-500">初年度売上</div>
                <div className="text-sm font-medium text-gray-900">{formatYen(currentParams.revenue_fy1)}</div>
              </div>
              <div className="bg-white rounded p-2.5 border border-blue-100">
                <div className="text-xs text-gray-500">売上成長率</div>
                <div className="text-sm font-medium text-gray-900">{formatPct(currentParams.growth_rate)}</div>
              </div>
              <div className="bg-white rounded p-2.5 border border-blue-100">
                <div className="text-xs text-gray-500">売上原価率</div>
                <div className="text-sm font-medium text-gray-900">{formatPct(currentParams.cogs_rate)}</div>
              </div>
              <div className="bg-white rounded p-2.5 border border-blue-100">
                <div className="text-xs text-gray-500">初年度 OPEX</div>
                <div className="text-sm font-medium text-gray-900">{formatYen(currentParams.opex_base)}</div>
              </div>
              <div className="bg-white rounded p-2.5 border border-blue-100">
                <div className="text-xs text-gray-500">OPEX 増加率</div>
                <div className="text-sm font-medium text-gray-900">{formatPct(currentParams.opex_growth)}</div>
              </div>
              {plPreview && (
                <div className="bg-white rounded p-2.5 border border-blue-100">
                  <div className="text-xs text-gray-500">FY5 営業利益</div>
                  <div className="text-sm font-medium text-gray-900">
                    {formatYen(plPreview.operating_profit[4])}
                  </div>
                </div>
              )}
            </div>
          )}
          <p className="text-xs text-blue-500 mt-2">
            シナリオ プレイグラウンドで設定した値がExcelに反映されます
          </p>
        </div>

        {/* Scenario Selection */}
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <h3 className="font-medium text-gray-900 mb-3">シナリオ選択</h3>
          <div className="space-y-2">
            {['base', 'best', 'worst'].map(function(s) {
              return (
                <label key={s} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={scenarios.indexOf(s) >= 0}
                    onChange={function(e) {
                      if (e.target.checked) {
                        setScenarios(scenarios.concat([s]))
                      } else {
                        setScenarios(scenarios.filter(function(x) { return x !== s }))
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
              )
            })}
          </div>
        </div>

        {/* SGA/R&D Sheet Mode */}
        <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
          <h3 className="font-medium text-gray-900 mb-3">販管費・開発費の出力形式</h3>
          <div className="space-y-3">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="radio"
                name="sgaRdMode"
                checked={sgaRdMode === 'inline'}
                onChange={function() { setSgaRdMode('inline') }}
                className="mt-0.5 text-blue-600"
              />
              <div>
                <div className="text-sm font-medium text-gray-800">PL設計シートに直接記載</div>
                <div className="text-xs text-gray-500">
                  人件費・マーケティング費・オフィス費・システム開発費・その他OPEXをPL設計シート内に記載
                </div>
              </div>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="radio"
                name="sgaRdMode"
                checked={sgaRdMode === 'separate'}
                onChange={function() { setSgaRdMode('separate') }}
                className="mt-0.5 text-blue-600"
              />
              <div>
                <div className="text-sm font-medium text-gray-800">別シートに分離（販管費明細 + 開発費明細）</div>
                <div className="text-xs text-gray-500">
                  販管費と開発費を各明細シートに分離し、PL設計シートには合計を自動反映
                </div>
              </div>
            </label>
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
          onClick={function() { exportMutation.mutate() }}
          disabled={exportMutation.isPending || !!isGenerating || scenarios.length === 0}
          className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {isGenerating ? 'Excel 生成中... (' + (jobData?.progress || 0) + '%)' :
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
            {sgaRdMode === 'separate' && (
              <p className="mt-2 text-xs text-green-600">
                販管費明細・開発費明細シートが含まれています
              </p>
            )}
            <p className="mt-1 text-xs text-green-600">
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
              onClick={function() {
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
