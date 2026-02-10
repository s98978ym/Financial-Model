/**
 * API client for PL Generator FastAPI backend.
 *
 * Uses fetch() with TanStack Query for caching and polling.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// In production, use Next.js proxy (/api/v1/*) to avoid CORS.
// In local dev, call the backend directly.
const isServer = typeof window === 'undefined'
const isLocal = BASE_URL.includes('localhost')
const API_PREFIX = isServer
  ? `${BASE_URL}/v1`                          // SSR: direct
  : (isLocal
      ? `${BASE_URL}/v1`                       // local dev: direct
      : '/api/v1')                             // production: via Next.js proxy

// Direct backend URL for large file uploads that exceed Vercel's body size limit.
// File uploads bypass the Next.js proxy and go straight to the backend with CORS.
const DIRECT_API = `${BASE_URL}/v1`

async function fetchAPI(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_PREFIX}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }))
    throw new Error(error.error?.message || error.detail?.message || `API Error: ${res.status}`)
  }

  return res.json()
}

export const api = {
  // Projects
  createProject: (body: { name: string; template_id?: string }) =>
    fetchAPI('/projects', { method: 'POST', body: JSON.stringify(body) }),

  listProjects: () => fetchAPI('/projects'),

  getProject: (id: string) => fetchAPI(`/projects/${id}`),

  getProjectState: (id: string) => fetchAPI(`/projects/${id}/state`),

  // Documents — file uploads go DIRECTLY to backend (bypass Vercel proxy body limit)
  uploadDocument: (projectId: string, body: { kind: string; text?: string }) => {
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('kind', body.kind)
    if (body.text) formData.append('text', body.text)
    return fetch(`${DIRECT_API}/documents/upload`, {
      method: 'POST',
      body: formData,
    }).then(async (r) => {
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`)
      return r.json()
    })
  },

  uploadDocumentFile: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('kind', 'file')
    formData.append('file', file)
    return fetch(`${DIRECT_API}/documents/upload`, {
      method: 'POST',
      body: formData,
    }).then(async (r) => {
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`)
      return r.json()
    })
  },

  // Phases
  phase1Scan: (body: any) =>
    fetchAPI('/phase1/scan', { method: 'POST', body: JSON.stringify(body) }),

  phase2Analyze: (body: any) =>
    fetchAPI('/phase2/analyze', { method: 'POST', body: JSON.stringify(body) }),

  phase3Map: (body: any) =>
    fetchAPI('/phase3/map', { method: 'POST', body: JSON.stringify(body) }),

  phase4Design: (body: any) =>
    fetchAPI('/phase4/design', { method: 'POST', body: JSON.stringify(body) }),

  phase5Extract: (body: any) =>
    fetchAPI('/phase5/extract', { method: 'POST', body: JSON.stringify(body) }),

  // Recalc (synchronous)
  recalc: (body: any) =>
    fetchAPI('/recalc', { method: 'POST', body: JSON.stringify(body) }),

  // Export
  exportExcel: (body: any) =>
    fetchAPI('/export/excel', { method: 'POST', body: JSON.stringify(body) }),

  downloadExcel: (jobId: string) =>
    `${API_PREFIX}/export/download/${jobId}`,

  // Jobs
  getJob: (jobId: string) => fetchAPI(`/jobs/${jobId}`),
}

/**
 * Hook helper: Poll a job until completion.
 * Use with TanStack Query's refetchInterval.
 */
export function shouldPollJob(data: any): number | false {
  if (!data) return 2000
  if (data.status === 'queued' || data.status === 'running') return 2000
  return false // Stop polling when completed/failed
}
