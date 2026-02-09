/**
 * Reusable hook for phase job management.
 *
 * Handles: trigger phase → poll job → return result.
 */

import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, shouldPollJob } from './api'

interface UsePhaseJobOptions {
  projectId: string
  phase: number
  /** If provided, auto-load this phase result from project state on mount */
  autoLoad?: boolean
}

interface PhaseJobState {
  jobId: string | null
  status: 'idle' | 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  result: any
  error: string | null
}

export function usePhaseJob({ projectId, phase, autoLoad = true }: UsePhaseJobOptions) {
  const queryClient = useQueryClient()
  const [state, setState] = useState<PhaseJobState>({
    jobId: null,
    status: 'idle',
    progress: 0,
    result: null,
    error: null,
  })

  // Auto-load existing result from project state
  const { data: projectState } = useQuery({
    queryKey: ['projectState', projectId],
    queryFn: () => api.getProjectState(projectId),
    enabled: autoLoad && !!projectId,
  })

  useEffect(() => {
    if (projectState?.phase_results?.[phase]) {
      const phaseResult = projectState.phase_results[phase]
      setState((prev) => ({
        ...prev,
        status: 'completed',
        progress: 100,
        result: phaseResult.raw_json,
      }))
    }
  }, [projectState, phase])

  // Poll job status
  const { data: jobData } = useQuery({
    queryKey: ['job', state.jobId],
    queryFn: () => api.getJob(state.jobId!),
    enabled: !!state.jobId && (state.status === 'queued' || state.status === 'running'),
    refetchInterval: (query) => shouldPollJob(query.state.data),
  })

  // Update state when job status changes
  useEffect(() => {
    if (!jobData) return

    if (jobData.status === 'completed') {
      // Job is done — refetch project state to populate result
      queryClient.invalidateQueries({ queryKey: ['projectState', projectId] })
      // Keep status as 'running' until project state provides the result
      // (avoids flash of "completed but no data")
      setState((prev) => ({
        ...prev,
        status: prev.result ? 'completed' : 'running',
        progress: prev.result ? 100 : 95,
        error: null,
      }))
    } else {
      setState((prev) => ({
        ...prev,
        status: jobData.status,
        progress: jobData.progress || 0,
        error: jobData.error_msg || null,
      }))
    }
  }, [jobData, projectId, queryClient])

  // Trigger functions for each phase
  const triggerPhase2 = useMutation({
    mutationFn: (body: { document_id: string; feedback?: string }) =>
      api.phase2Analyze({ project_id: projectId, ...body }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0 }))
    },
  })

  const triggerPhase3 = useMutation({
    mutationFn: (body: { selected_proposal: any; catalog_summary?: any }) =>
      api.phase3Map({ project_id: projectId, ...body }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0 }))
    },
  })

  const triggerPhase4 = useMutation({
    mutationFn: (body?: { edits?: any[] }) =>
      api.phase4Design({ project_id: projectId, ...(body || {}) }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0 }))
    },
  })

  const triggerPhase5 = useMutation({
    mutationFn: (body?: { edits?: any[]; document_excerpt_chars?: number }) =>
      api.phase5Extract({ project_id: projectId, ...(body || {}) }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0 }))
    },
  })

  const trigger = useCallback(
    (body?: any) => {
      switch (phase) {
        case 2:
          return triggerPhase2.mutate(body)
        case 3:
          return triggerPhase3.mutate(body)
        case 4:
          return triggerPhase4.mutate(body)
        case 5:
          return triggerPhase5.mutate(body)
      }
    },
    [phase, triggerPhase2, triggerPhase3, triggerPhase4, triggerPhase5]
  )

  const isProcessing = state.status === 'queued' || state.status === 'running'
  const isComplete = state.status === 'completed'
  const isFailed = state.status === 'failed'

  return {
    ...state,
    trigger,
    isProcessing,
    isComplete,
    isFailed,
    projectState,
  }
}
