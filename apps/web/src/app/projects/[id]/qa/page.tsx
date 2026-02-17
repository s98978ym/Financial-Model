'use client'

import { useState, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import { QASettingsPanel } from '@/components/qa/QASettings'
import { QADisplay } from '@/components/qa/QADisplay'
import { SaveResumePanel } from '@/components/qa/SaveResumePanel'
import type { QASettings, QAItem } from '@/data/qaTemplates'
import { generateQA } from '@/data/qaTemplates'
import type { IndustryKey } from '@/data/industryBenchmarks'
import { detectIndustry } from '@/data/industryBenchmarks'

var DEFAULT_PARAMS = {
  revenue_fy1: 100_000_000,
  growth_rate: 0.30,
  cogs_rate: 0.30,
  opex_base: 80_000_000,
  opex_growth: 0.10,
}

var DEFAULT_SETTINGS: QASettings = {
  target: 'investor',
  detailLevel: 'standard',
  answerLength: 'medium',
  count: 10,
}

export default function QAPage() {
  var params = useParams()
  var projectId = params.id as string
  var [settings, setSettings] = useState<QASettings>(DEFAULT_SETTINGS)
  var [qaItems, setQAItems] = useState<QAItem[]>([])
  var [isGenerating, setIsGenerating] = useState(false)
  var [parameters, setParameters] = useState(DEFAULT_PARAMS)
  var [plResult, setPLResult] = useState<any>(null)
  var [industry, setIndustry] = useState<IndustryKey>('その他')

  // Load project state
  var projectState = useQuery({
    queryKey: ['projectState', projectId],
    queryFn: function() { return api.getProjectState(projectId) },
    enabled: !!projectId,
  })

  // Detect industry
  useEffect(function() {
    if (projectState.data) {
      var detected = detectIndustry(
        projectState.data.project?.name,
        projectState.data.phase5_result
      )
      setIndustry(detected)
    }
  }, [projectState.data])

  // Load PL data
  var recalc = useMutation({
    mutationFn: function(p: { parameters: any; scenario: string }) {
      return api.recalc({
        project_id: projectId,
        parameters: p.parameters,
        scenario: p.scenario,
      })
    },
    onSuccess: function(data: any) {
      setPLResult(data)
      if (data.source_params) {
        var merged = Object.assign({}, DEFAULT_PARAMS)
        Object.keys(DEFAULT_PARAMS).forEach(function(key) {
          if (data.source_params[key] != null) {
            merged[key as keyof typeof DEFAULT_PARAMS] = data.source_params[key]
          }
        })
        setParameters(merged)
      }
    },
  })

  // Auto-load PL data
  useEffect(function() {
    if (projectId) {
      recalc.mutate({ parameters: DEFAULT_PARAMS, scenario: 'base' })
    }
  }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  var handleGenerate = useCallback(function() {
    setIsGenerating(true)

    // Simulate generation delay for UX
    setTimeout(function() {
      var items = generateQA(
        {
          parameters: parameters,
          kpis: plResult?.kpis,
          plSummary: plResult?.pl_summary,
          industry: industry,
        },
        settings
      )
      setQAItems(items)
      setIsGenerating(false)
    }, 600)
  }, [parameters, plResult, industry, settings])

  return (
    <PhaseLayout
      phase={8}
      title="Q&A 作成"
      subtitle="プレゼン・資金調達用の想定問答を自動生成"
      projectId={projectId}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Settings + Save */}
        <div className="lg:col-span-1 space-y-6">
          <QASettingsPanel
            settings={settings}
            onChange={setSettings}
            onGenerate={handleGenerate}
            isGenerating={isGenerating}
          />
          <SaveResumePanel
            projectId={projectId}
            projectState={projectState.data}
          />
        </div>

        {/* Right: QA Display */}
        <div className="lg:col-span-2">
          {qaItems.length > 0 ? (
            <QADisplay items={qaItems} />
          ) : (
            <div className="bg-white rounded-3xl shadow-warm p-12 text-center">
              <div className="text-5xl mb-4">💬</div>
              <h3 className="text-lg font-semibold text-dark-900 mb-2">Q&Aを生成しましょう</h3>
              <p className="text-sm text-sand-500 max-w-md mx-auto mb-6">
                左のパネルでターゲット、詳しさ、長さ、Q&A数を設定し、
                「Q&Aを生成」ボタンを押してください。
                PLモデルのデータから自動的にQ&Aが作成されます。
              </p>
              <div className="grid grid-cols-2 gap-4 max-w-sm mx-auto text-left">
                <div className="bg-cream-100 rounded-2xl p-3">
                  <div className="text-xs font-medium text-dark-900 mb-1">収益・成長</div>
                  <div className="text-xs text-sand-600">売上予測、成長率の根拠</div>
                </div>
                <div className="bg-red-50/50 rounded-2xl p-3">
                  <div className="text-xs font-medium text-red-700 mb-1">コスト・収益性</div>
                  <div className="text-xs text-red-600">原価率、黒字化時期</div>
                </div>
                <div className="bg-orange-50/50 rounded-2xl p-3">
                  <div className="text-xs font-medium text-orange-700 mb-1">リスク・市場</div>
                  <div className="text-xs text-orange-600">ダウンサイド、競合分析</div>
                </div>
                <div className="bg-purple-50/50 rounded-2xl p-3">
                  <div className="text-xs font-medium text-purple-700 mb-1">資金・運営</div>
                  <div className="text-xs text-purple-600">資金調達、体制計画</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </PhaseLayout>
  )
}
