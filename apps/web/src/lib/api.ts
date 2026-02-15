/**
 * API client for PL Generator FastAPI backend.
 *
 * All requests go directly to the backend (CORS configured).
 * Includes retry logic for Render free-tier cold starts (30-60s wake-up).
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_BASE = `${BASE_URL}/v1`

/**
 * Retry fetch up to `retries` times with exponential backoff.
 * Tuned for Render free-tier cold starts (30-60s wake-up).
 * Schedule: 0s → 8s → 16s → 32s → 64s  (total ~120s window)
 */
async function fetchWithRetry(
  url: string,
  init: RequestInit,
  retries = 4,
  baseDelayMs = 8000,
): Promise<Response> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fetch(url, init)
    } catch (err) {
      if (attempt >= retries) {
        throw new Error(
          `サーバーに接続できません。しばらく待ってからリロードしてください → ${url}`
        )
      }
      var delay = baseDelayMs * Math.pow(2, attempt)
      console.log('[API] Retry ' + (attempt + 1) + '/' + retries + ' after ' + delay + 'ms: ' + url)
      // Wait before retry (handles Render cold start: 30-60s)
      await new Promise(function(r) { setTimeout(r, delay) })
    }
  }
}

// Admin token management
var _adminToken: string | null = null

export function setAdminToken(token: string | null) {
  _adminToken = token
}

export function getAdminToken(): string | null {
  return _adminToken
}

/** Warm up the Render backend on page load (fire-and-forget with retry). */
let _warmedUp = false
export function warmUpBackend() {
  if (_warmedUp) return
  _warmedUp = true
  // First ping — may fail if cold-starting
  fetch(BASE_URL + '/health').catch(function() {
    // Retry after 5s to ensure backend is awake before user interacts
    setTimeout(function() { fetch(BASE_URL + '/health').catch(function() {}) }, 5000)
  })
}

async function fetchAPI(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE}${path}`
  var baseHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (_adminToken && path.indexOf('/admin/') === 0) {
    baseHeaders['Authorization'] = 'Bearer ' + _adminToken
  }
  const res = await fetchWithRetry(url, {
    ...options,
    headers: {
      ...baseHeaders,
      ...(options.headers as Record<string, string> || {}),
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }))
    var msg = error.error?.message || error.detail?.message || `API Error: ${res.status}`
    var apiError = new Error(msg) as any
    apiError.code = error.detail?.code || error.error?.code || null
    apiError.detail = error.detail || null
    apiError.status = res.status
    throw apiError
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

  updateProject: (id: string, body: { name?: string; memo?: string; status?: string }) =>
    fetchAPI(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),

  deleteProject: (id: string) =>
    fetchAPI(`/projects/${id}`, { method: 'DELETE' }),

  // Documents (FormData — no Content-Type header, browser sets multipart boundary)
  uploadDocument: (projectId: string, body: { kind: string; text?: string }) => {
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('kind', body.kind)
    if (body.text) formData.append('text', body.text)
    return fetchWithRetry(`${API_BASE}/documents/upload`, {
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
    return fetchWithRetry(`${API_BASE}/documents/upload`, {
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

  // Edits — save/load user decisions
  saveEdit: (body: { project_id: string; phase: number; patch_json: any }) =>
    fetchAPI('/edits', { method: 'POST', body: JSON.stringify(body) }),

  getEdits: (projectId: string, phase?: number) => {
    var url = '/edits/' + projectId
    if (phase != null) url += '?phase=' + phase
    return fetchAPI(url)
  },

  // Recalc (synchronous)
  recalc: (body: any) =>
    fetchAPI('/recalc', { method: 'POST', body: JSON.stringify(body) }),

  // Export
  exportExcel: (body: any) =>
    fetchAPI('/export/excel', { method: 'POST', body: JSON.stringify(body) }),

  downloadExcel: (jobId: string) =>
    `${API_BASE}/export/download/${jobId}`,

  // Jobs (keep polling on transient errors — only stop on terminal status)
  getJob: (jobId: string) =>
    fetchAPI(`/jobs/${jobId}`).catch((err) => {
      // Return a transient 'running' status so polling continues on network errors.
      // Only the backend should decide when a job is truly 'failed'.
      console.warn('[API] getJob transient error, continuing poll:', err.message)
      return { status: 'running', progress: 0, error_msg: err.message || 'Job fetch failed', _transient: true }
    }),

  // Admin: Authentication
  adminAuth: function(adminId: string, password: string) {
    return fetchAPI('/admin/auth', {
      method: 'POST',
      body: JSON.stringify({ admin_id: adminId, password: password }),
    })
  },

  verifyAdminToken: function() {
    return fetchAPI('/admin/auth/verify')
  },

  // Admin: Prompt Management
  getPromptPhases: () => fetchAPI('/admin/prompts/phases'),

  listPrompts: (projectId?: string) => {
    var url = '/admin/prompts'
    if (projectId) url += '?project_id=' + projectId
    return fetchAPI(url)
  },

  getPrompt: (key: string, projectId?: string) => {
    var url = '/admin/prompts/' + key
    if (projectId) url += '?project_id=' + projectId
    return fetchAPI(url)
  },

  updatePrompt: (key: string, body: { content: string; project_id?: string; label?: string }) =>
    fetchAPI('/admin/prompts/' + key, { method: 'PUT', body: JSON.stringify(body) }),

  resetPrompt: (key: string, projectId?: string) =>
    fetchAPI('/admin/prompts/' + key + '/reset', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId || null }),
    }),

  activatePromptVersion: (key: string, versionId: string, projectId?: string) =>
    fetchAPI('/admin/prompts/' + key + '/versions/' + versionId, {
      method: 'PUT',
      body: JSON.stringify({ project_id: projectId || null }),
    }),
}

/**
 * Hook helper: Poll a job until completion.
 * Use with TanStack Query's refetchInterval.
 */
export function shouldPollJob(data: any): number | false {
  if (!data) return false // No data yet (initial load) — don't poll
  if (data.status === 'queued' || data.status === 'running') return 2000
  return false // Stop polling when completed/failed
}
