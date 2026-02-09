'use client'

import { useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
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
  const projectId = params.id as string
  const [scenario, setScenario] = useState<'base' | 'best' | 'worst'>('base')
  const [parameters, setParameters] = useState(DEFAULT_PARAMS)
  const [plResult, setPLResult] = useState<any>(null)

  const recalc = useMutation({
    mutationFn: (params: { parameters: any; scenario: string }) =>
      api.recalc({
        project_id: projectId,
        parameters: params.parameters,
        scenario: params.scenario,
      }),
    onSuccess: (data) => {
      setPLResult(data)
    },
  })

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
    </PhaseLayout>
  )
}
