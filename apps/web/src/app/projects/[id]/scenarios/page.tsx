'use client'

import { useState, useCallback, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PLChart } from '@/components/charts/PLChart'
import { ScenarioTabs } from '@/components/scenario/ScenarioTabs'
import { DriverSliders } from '@/components/scenario/DriverSliders'
import { ScenarioComparison } from '@/components/scenario/ScenarioComparison'
import { PhaseLayout } from '@/components/ui/PhaseLayout'

const DEFAULT_PARAMS = {
  revenue_fy1: 100_000_000,
  growth_rate: 0.30,
  cogs_rate: 0.30,
  opex_base: 80_000_000,
  opex_growth: 0.10,
}

export default function ScenarioPlaygroundPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [scenario, setScenario] = useState<'base' | 'best' | 'worst'>('base')
  const [parameters, setParameters] = useState(DEFAULT_PARAMS)
  const [plResult, setPLResult] = useState<any>(null)
  const [initialized, setInitialized] = useState(false)

  // Load project state to get Phase 5 parameters
  const { data: projectState } = useQuery({
    queryKey: ['projectState', projectId],
    queryFn: () => api.getProjectState(projectId),
    enabled: !!projectId,
  })

  const recalc = useMutation({
    mutationFn: (p: { parameters: any; scenario: string }) =>
      api.recalc({
        project_id: projectId,
        parameters: p.parameters,
        scenario: p.scenario,
      }),
    onSuccess: (data) => {
      setPLResult(data)
      // If source_params came back, use them (includes Phase 5 data)
      if (!initialized && data.source_params) {
        const merged = { ...DEFAULT_PARAMS }
        for (const key of Object.keys(DEFAULT_PARAMS)) {
          if (data.source_params[key] != null) {
            merged[key as keyof typeof DEFAULT_PARAMS] = data.source_params[key]
          }
        }
        setParameters(merged)
        setInitialized(true)
      }
    },
  })

  // Auto-trigger initial recalc when project state loads
  useEffect(() => {
    if (projectId && !initialized) {
      recalc.mutate({ parameters: DEFAULT_PARAMS, scenario: 'base' })
    }
  }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleParameterChange = useCallback(
    (key: string, value: number) => {
      const newParams = { ...parameters, [key]: value }
      setParameters(newParams)
      recalc.mutate({ parameters: newParams, scenario })
    },
    [parameters, scenario, recalc]
  )

  const handleScenarioChange = useCallback(
    (newScenario: 'base' | 'best' | 'worst') => {
      setScenario(newScenario)
      recalc.mutate({ parameters, scenario: newScenario })
    },
    [parameters, recalc]
  )

  return (
    <PhaseLayout
      phase={6}
      title="シナリオ プレイグラウンド"
      subtitle="パラメータを調整してPLの変化を体感"
      projectId={projectId}
    >
      {/* Scenario Tabs */}
      <ScenarioTabs active={scenario} onChange={handleScenarioChange} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Driver Sliders */}
        <div className="lg:col-span-1">
          <DriverSliders
            parameters={parameters}
            onChange={handleParameterChange}
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

      {/* Navigation */}
      <div className="mt-8 flex justify-end">
        <button
          onClick={() => router.push(`/projects/${projectId}/export`)}
          className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 text-sm"
        >
          Excel エクスポートへ進む
        </button>
      </div>
    </PhaseLayout>
  )
}
