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

interface RDThemeItem {
  name: string
  items: string[]
  amounts?: number[]
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
  var [rdThemes, setRdThemes] = useState<RDThemeItem[] | null>(null)

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

  // Load rd_themes from Phase 6 edits
  var editsQuery = useQuery({
    queryKey: ['edits-export', projectId],
    queryFn: function() { return api.getEdits(projectId, 6) },
    enabled: !!projectId,
  })

  useEffect(function() {
    if (editsQuery.data && Array.isArray(editsQuery.data)) {
      for (var i = editsQuery.data.length - 1; i >= 0; i--) {
        var pj = editsQuery.data[i].patch_json || {}
        if (pj.rd_themes) {
          setRdThemes(pj.rd_themes)
          break
        }
      }
    }
  }, [editsQuery.data])

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
        options: Object.assign({
          include_needs_review: includeNeedsReview,
          include_case_diff: includeCaseDiff,
          sga_rd_mode: sgaRdMode,
          best_multipliers: { revenue: 1.2, cost: 0.9 },
          worst_multipliers: { revenue: 0.8, cost: 1.15 },
        }, rdThemes ? { rd_themes: rdThemes } : {}),
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
        <div className="bg-white rounded-3xl shadow-warm p-6 mb-4">
          <h3 className="font-semibold text-dark-900 mb-4">現在のモデル設定（PL反映値）</h3>
          {recalcQuery.isLoading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-gold-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-sand-500">モデルパラメータを読み込み中...</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="bg-cream-100 rounded-2xl p-3">
                <div className="text-xs text-sand-400">初年度売上</div>
                <div className="text-sm font-bold text-dark-900 mt-0.5">{formatYen(currentParams.revenue_fy1)}</div>
              </div>
              <div className="bg-cream-100 rounded-2xl p-3">
                <div className="text-xs text-sand-400">売上成長率</div>
                <div className="text-sm font-bold text-dark-900 mt-0.5">{formatPct(currentParams.growth_rate)}</div>
              </div>
              <div className="bg-cream-100 rounded-2xl p-3">
                <div className="text-xs text-sand-400">売上原価率</div>
                <div className="text-sm font-bold text-dark-900 mt-0.5">{formatPct(currentParams.cogs_rate)}</div>
              </div>
              <div className="bg-cream-100 rounded-2xl p-3">
                <div className="text-xs text-sand-400">初年度 OPEX</div>
                <div className="text-sm font-bold text-dark-900 mt-0.5">{formatYen(currentParams.opex_base)}</div>
              </div>
              <div className="bg-cream-100 rounded-2xl p-3">
                <div className="text-xs text-sand-400">OPEX 増加率</div>
                <div className="text-sm font-bold text-dark-900 mt-0.5">{formatPct(currentParams.opex_growth)}</div>
              </div>
              {plPreview && (
                <div className="bg-cream-100 rounded-2xl p-3">
                  <div className="text-xs text-sand-400">FY5 営業利益</div>
                  <div className="text-sm font-bold text-dark-900 mt-0.5">
                    {formatYen(plPreview.operating_profit[4])}
                  </div>
                </div>
              )}
            </div>
          )}
          <p className="text-xs text-sand-400 mt-3">
            シナリオ プレイグラウンドで設定した値がExcelに反映されます
          </p>
        </div>

        {/* Scenario Selection */}
        <div className="bg-white rounded-3xl shadow-warm p-6 mb-4">
          <h3 className="font-semibold text-dark-900 mb-4">シナリオ選択</h3>
          <div className="space-y-3">
            {['base', 'best', 'worst'].map(function(s) {
              var checked = scenarios.indexOf(s) >= 0
              return (
                <label key={s} className={'flex items-center gap-3 p-3 rounded-2xl cursor-pointer transition-all ' + (checked ? 'bg-gold-500/5' : 'hover:bg-cream-100')}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={function(e) {
                      if (e.target.checked) {
                        setScenarios(scenarios.concat([s]))
                      } else {
                        setScenarios(scenarios.filter(function(x) { return x !== s }))
                      }
                    }}
                    className="rounded-lg border-cream-400 text-gold-500 focus:ring-gold-400/30 w-4 h-4"
                  />
                  <span className="text-sm font-medium text-dark-900 capitalize">{s}</span>
                  <span className="text-xs text-sand-400">
                    {s === 'base' ? '基本シナリオ' :
                     s === 'best' ? '売上+20%/コスト-10%' : '売上-20%/コスト+15%'}
                  </span>
                </label>
              )
            })}
          </div>
        </div>

        {/* SGA/R&D Sheet Mode */}
        <div className="bg-white rounded-3xl shadow-warm p-6 mb-4">
          <h3 className="font-semibold text-dark-900 mb-4">販管費・開発費の出力形式</h3>
          <div className="space-y-3">
            <label className={'flex items-start gap-3 p-3 rounded-2xl cursor-pointer transition-all ' + (sgaRdMode === 'inline' ? 'bg-gold-500/5' : 'hover:bg-cream-100')}>
              <input
                type="radio"
                name="sgaRdMode"
                checked={sgaRdMode === 'inline'}
                onChange={function() { setSgaRdMode('inline') }}
                className="mt-0.5 text-gold-500 focus:ring-gold-400/30"
              />
              <div>
                <div className="text-sm font-medium text-dark-900">PL設計シートに直接記載</div>
                <div className="text-xs text-sand-400 mt-0.5">
                  人件費・マーケティング費・オフィス費・システム開発費・その他OPEXをPL設計シート内に記載
                </div>
              </div>
            </label>
            <label className={'flex items-start gap-3 p-3 rounded-2xl cursor-pointer transition-all ' + (sgaRdMode === 'separate' ? 'bg-gold-500/5' : 'hover:bg-cream-100')}>
              <input
                type="radio"
                name="sgaRdMode"
                checked={sgaRdMode === 'separate'}
                onChange={function() { setSgaRdMode('separate') }}
                className="mt-0.5 text-gold-500 focus:ring-gold-400/30"
              />
              <div>
                <div className="text-sm font-medium text-dark-900">別シートに分離（販管費明細 + 開発費明細）</div>
                <div className="text-xs text-sand-400 mt-0.5">
                  販管費と開発費を各明細シートに分離し、PL設計シートには合計を自動反映
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Export Options */}
        <div className="bg-white rounded-3xl shadow-warm p-6 mb-6">
          <h3 className="font-semibold text-dark-900 mb-4">出力オプション</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-3 text-sm text-dark-900 cursor-pointer">
              <input
                type="checkbox"
                checked={includeNeedsReview}
                onChange={function(e) { setIncludeNeedsReview(e.target.checked) }}
                className="rounded-lg border-cream-400 text-gold-500 focus:ring-gold-400/30 w-4 h-4"
              />
              needs_review.csv を含める
            </label>
            <label className="flex items-center gap-3 text-sm text-dark-900 cursor-pointer">
              <input
                type="checkbox"
                checked={includeCaseDiff}
                onChange={function(e) { setIncludeCaseDiff(e.target.checked) }}
                className="rounded-lg border-cream-400 text-gold-500 focus:ring-gold-400/30 w-4 h-4"
              />
              ケース差分レポートを含める
            </label>
          </div>
        </div>

        {/* Export Button */}
        <button
          onClick={function() { exportMutation.mutate() }}
          disabled={exportMutation.isPending || !!isGenerating || scenarios.length === 0}
          className="w-full bg-dark-900 text-white py-3.5 rounded-2xl hover:bg-dark-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-warm-md hover:shadow-warm-lg font-medium"
        >
          {isGenerating ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              {'Excel 生成中... (' + (jobData?.progress || 0) + '%)'}
            </span>
          ) : exportMutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ジョブ作成中...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <svg className="w-5 h-5 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Excel をエクスポート
            </span>
          )}
        </button>

        {/* Generating spinner */}
        {isGenerating && (
          <div className="mt-6 text-center">
            <div className="relative w-10 h-10 mx-auto mb-3">
              <div className="absolute inset-0 rounded-full border-2 border-cream-300"></div>
              <div className="absolute inset-0 rounded-full border-2 border-gold-500 border-t-transparent animate-spin"></div>
            </div>
            <p className="text-sm text-sand-500">Excel ファイルを生成しています...</p>
          </div>
        )}

        {/* Download ready */}
        {isComplete && downloadUrl && (
          <div className="mt-6 bg-white rounded-3xl shadow-warm p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-dark-900">生成完了</h3>
            </div>
            <a
              href={downloadUrl}
              download
              className="inline-flex items-center gap-2 bg-dark-900 text-white px-6 py-3 rounded-2xl hover:bg-dark-800 transition-all shadow-warm-md font-medium"
            >
              <svg className="w-5 h-5 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Excel ファイルをダウンロード
            </a>
            {sgaRdMode === 'separate' && (
              <p className="mt-3 text-xs text-sand-400">
                販管費明細・開発費明細シートが含まれています
              </p>
            )}
            <p className="mt-1 text-xs text-sand-400">
              ファイルはブラウザのダウンロードフォルダに保存されます
            </p>
          </div>
        )}

        {/* Error */}
        {(isFailed || exportMutation.isError) && (
          <div className="mt-6 bg-red-50 rounded-2xl p-5">
            <p className="text-sm text-red-600">
              エラー: {jobData?.error_msg || (exportMutation.error as Error)?.message || '不明なエラー'}
            </p>
            <button
              onClick={function() {
                setJobId(null)
                exportMutation.reset()
              }}
              className="mt-3 text-sm text-red-500 hover:text-red-600 font-medium transition-colors"
            >
              再試行
            </button>
          </div>
        )}
      </div>
    </PhaseLayout>
  )
}
