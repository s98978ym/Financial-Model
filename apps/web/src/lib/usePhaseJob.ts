/**
 * Reusable hook for phase job management.
 *
 * Handles: trigger phase → poll job → return result.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
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
  // staleTime prevents unnecessary refetches — projectState only changes on phase completion
  const { data: projectState } = useQuery({
    queryKey: ['projectState', projectId],
    queryFn: () => api.getProjectState(projectId),
    enabled: autoLoad && !!projectId,
    staleTime: 30000,
  })

  useEffect(() => {
    if (projectState?.phase_results?.[phase]) {
      const phaseResult = projectState.phase_results[phase]
      setState((prev) => {
        // Don't overwrite with stale results if a new job is actively running
        if (prev.jobId && (prev.status === 'queued' || prev.status === 'running') && prev.progress < 95) {
          return prev
        }
        return {
          ...prev,
          status: 'completed',
          progress: 100,
          result: phaseResult.raw_json,
        }
      })
    }
  }, [projectState, phase])

  // Poll job status
  const { data: jobData } = useQuery({
    queryKey: ['job', state.jobId],
    queryFn: () => api.getJob(state.jobId!),
    enabled: !!state.jobId && (state.status === 'queued' || state.status === 'running'),
    refetchInterval: (query) => shouldPollJob(query.state.data),
  })

  // Track which jobId we've already invalidated for (prevents double-invalidation per job)
  const completionInvalidatedForJob = useRef<string | null>(null)

  // Update state when job status changes
  useEffect(() => {
    if (!jobData) return

    if (jobData.status === 'completed') {
      // Invalidate projectState cache so other components pick up the new result
      if (completionInvalidatedForJob.current !== state.jobId) {
        completionInvalidatedForJob.current = state.jobId
        queryClient.invalidateQueries({ queryKey: ['projectState', projectId] })
      }
      // Use inlined result_data from job response for instant completion,
      // falling back to waiting for projectState refetch if not available
      var resultData = jobData.result_data || null
      setState((prev) => {
        var result = resultData || prev.result
        return {
          ...prev,
          status: result != null ? 'completed' : 'running',
          progress: result != null ? 100 : 95,
          result: result != null ? result : prev.result,
          error: null,
        }
      })
    } else {
      setState((prev) => ({
        ...prev,
        status: jobData.status,
        progress: jobData.progress || 0,
        error: jobData.error_msg || null,
      }))
    }
  }, [jobData, projectId, queryClient])

  // Common error handler for mutations
  const onMutationError = (err: Error) => {
    console.error(`[usePhaseJob] Phase ${phase} mutation error:`, err.message)
    setState((prev) => ({
      ...prev,
      status: 'failed',
      error: err.message || 'API call failed',
    }))
  }

  // Trigger functions for each phase
  const triggerPhase2 = useMutation({
    mutationFn: (body: { document_id: string; feedback?: string }) =>
      api.phase2Analyze({ project_id: projectId, ...body }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0, error: null }))
    },
    onError: onMutationError,
  })

  const triggerPhase3 = useMutation({
    mutationFn: (body: { selected_proposal: any; catalog_summary?: any }) =>
      api.phase3Map({ project_id: projectId, ...body }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0, error: null }))
    },
    onError: onMutationError,
  })

  const triggerPhase4 = useMutation({
    mutationFn: (body?: { edits?: any[] }) =>
      api.phase4Design({ project_id: projectId, ...(body || {}) }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0, error: null }))
    },
    onError: onMutationError,
  })

  const triggerPhase5 = useMutation({
    mutationFn: (body?: { edits?: any[]; document_excerpt_chars?: number }) =>
      api.phase5Extract({ project_id: projectId, ...(body || {}) }),
    onSuccess: (data) => {
      setState((prev) => ({ ...prev, jobId: data.job_id, status: 'queued', progress: 0, error: null }))
    },
    onError: onMutationError,
  })

  const trigger = useCallback(
    (body?: any) => {
      // Immediately show loading state
      setState((prev) => ({ ...prev, status: 'running', progress: 0, error: null }))
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
