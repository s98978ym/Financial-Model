/**
 * API client for PL Generator FastAPI backend.
 *
 * All requests go directly to the backend (CORS configured).
 * No server-side proxy — simplest and most reliable approach.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_BASE = `${BASE_URL}/v1`

async function fetchAPI(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE}${path}`
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

  // Documents (FormData — no Content-Type header, browser sets multipart boundary)
  uploadDocument: (projectId: string, body: { kind: string; text?: string }) => {
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('kind', body.kind)
    if (body.text) formData.append('text', body.text)
    return fetch(`${API_BASE}/documents/upload`, {
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
    return fetch(`${API_BASE}/documents/upload`, {
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
    `${API_BASE}/export/download/${jobId}`,

  // Jobs (return failed status on 404 so polling stops gracefully)
  getJob: (jobId: string) =>
    fetchAPI(`/jobs/${jobId}`).catch((err) => {
      if (err.message?.includes('404')) {
        return { status: 'failed', error_msg: 'Job not found (server restarted?)' }
      }
      throw err
    }),
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
