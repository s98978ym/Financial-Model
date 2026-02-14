'use client'

import { useState, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PLChart } from '@/components/charts/PLChart'
import { ScenarioTabs } from '@/components/scenario/ScenarioTabs'
import { DriverSliders } from '@/components/scenario/DriverSliders'
import { ScenarioComparison } from '@/components/scenario/ScenarioComparison'
import { IndustryBenchmarkCards } from '@/components/scenario/IndustryBenchmarkCards'
import { ModelOverview } from '@/components/scenario/ModelOverview'
import { NaturalLanguageInput } from '@/components/scenario/NaturalLanguageInput'
import { PhaseLayout } from '@/components/ui/PhaseLayout'
import type { IndustryKey } from '@/data/industryBenchmarks'
import { detectIndustry } from '@/data/industryBenchmarks'

var DEFAULT_PARAMS = {
  revenue_fy1: 100_000_000,
  growth_rate: 0.30,
  cogs_rate: 0.30,
  opex_base: 80_000_000,
  opex_growth: 0.10,
}

export default function ScenarioPlaygroundPage() {
  var params = useParams()
  var projectId = params.id as string
  var [scenario, setScenario] = useState<'base' | 'best' | 'worst'>('base')
  var [parameters, setParameters] = useState(DEFAULT_PARAMS)
  var [plResult, setPLResult] = useState<any>(null)
  var [initialized, setInitialized] = useState(false)
  var [industry, setIndustry] = useState<IndustryKey>('その他')

  // Load project state to get Phase 5 parameters
  var projectState = useQuery({
    queryKey: ['projectState', projectId],
    queryFn: function() { return api.getProjectState(projectId) },
    enabled: !!projectId,
  })

  // Detect industry from project data
  useEffect(function() {
    if (projectState.data) {
      var detected = detectIndustry(
        projectState.data.project?.name,
        projectState.data.phase5_result
      )
      setIndustry(detected)
    }
  }, [projectState.data])

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
      // If source_params came back, use them (includes Phase 5 data)
      if (!initialized && data.source_params) {
        var merged = Object.assign({}, DEFAULT_PARAMS)
        Object.keys(DEFAULT_PARAMS).forEach(function(key) {
          if (data.source_params[key] != null) {
            merged[key as keyof typeof DEFAULT_PARAMS] = data.source_params[key]
          }
        })
        setParameters(merged)
        setInitialized(true)
      }
    },
  })

  // Auto-trigger initial recalc when project state loads
  useEffect(function() {
    if (projectId && !initialized) {
      recalc.mutate({ parameters: DEFAULT_PARAMS, scenario: 'base' })
    }
  }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  var handleParameterChange = useCallback(
    function(key: string, value: number) {
      var newParams = Object.assign({}, parameters, { [key]: value })
      setParameters(newParams)
      recalc.mutate({ parameters: newParams, scenario: scenario })
    },
    [parameters, scenario, recalc]
  )

  var handleBatchChange = useCallback(
    function(changes: Record<string, number>) {
      var newParams = Object.assign({}, parameters, changes)
      setParameters(newParams)
      recalc.mutate({ parameters: newParams, scenario: scenario })
    },
    [parameters, scenario, recalc]
  )

  var handleScenarioChange = useCallback(
    function(newScenario: 'base' | 'best' | 'worst') {
      setScenario(newScenario)
      recalc.mutate({ parameters: parameters, scenario: newScenario })
    },
    [parameters, recalc]
  )

  var handleIndustryChange = useCallback(
    function(newIndustry: IndustryKey) {
      setIndustry(newIndustry)
    },
    []
  )

  return (
    <PhaseLayout
      phase={6}
      title="シナリオ プレイグラウンド"
      subtitle="パラメータを調整してPLの変化を体感"
      projectId={projectId}
    >
      {/* Model Overview & Natural Language Input */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ModelOverview
          parameters={parameters}
          kpis={plResult?.kpis}
          plSummary={plResult?.pl_summary}
          industry={industry}
          onParameterChange={handleParameterChange}
        />
        <div className="space-y-4">
          <NaturalLanguageInput
            parameters={parameters}
            onParameterChange={handleParameterChange}
            onBatchChange={handleBatchChange}
          />
          <IndustryBenchmarkCards
            industry={industry}
            onIndustryChange={handleIndustryChange}
          />
        </div>
      </div>

      {/* Scenario Tabs */}
      <ScenarioTabs active={scenario} onChange={handleScenarioChange} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Driver Sliders */}
        <div className="lg:col-span-1">
          <DriverSliders
            parameters={parameters}
            onChange={handleParameterChange}
            industry={industry}
          />
        </div>

        {/* PL Chart */}
        <div className="lg:col-span-2">
          <PLChart data={plResult?.pl_summary} kpis={plResult?.kpis} />
        </div>
      </div>

      {/* Scenario Comparison Table */}
      <div className="mt-8">
        <ScenarioComparison projectId={projectId} parameters={parameters} />
      </div>

    </PhaseLayout>
  )
}
