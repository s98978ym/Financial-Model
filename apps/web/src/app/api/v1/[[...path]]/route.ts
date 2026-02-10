/**
 * Catch-all API proxy route.
 *
 * Proxies /api/v1/* requests to the FastAPI backend.
 * Uses Node.js runtime for full body buffering support.
 * File uploads (>4.5MB) should bypass this proxy and call the backend directly.
 */

import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL =
  process.env.API_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000'

async function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname.replace('/api/v1', '/v1')
  const url = `${BACKEND_URL}${path}${req.nextUrl.search}`

  // Forward relevant headers (skip hop-by-hop headers)
  const headers: Record<string, string> = {}
  req.headers.forEach((value, key) => {
    if (
      !['host', 'connection', 'transfer-encoding', 'content-length'].includes(
        key.toLowerCase()
      )
    ) {
      headers[key] = value
    }
  })

  // Buffer body for non-GET requests
  let body: BodyInit | undefined
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    body = await req.text()
  }

  try {
    const res = await fetch(url, {
      method: req.method,
      headers,
      body,
    })

    const responseHeaders = new Headers()
    res.headers.forEach((value, key) => {
      if (
        !['transfer-encoding', 'content-encoding'].includes(key.toLowerCase())
      ) {
        responseHeaders.set(key, value)
      }
    })

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    })
  } catch (error) {
    console.error('API proxy error:', error, '→', url)
    return NextResponse.json(
      { error: { message: 'Backend service unavailable' } },
      { status: 502 }
    )
  }
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const PATCH = proxy
export const DELETE = proxy

// Node.js runtime for full body buffering (no 4MB Edge limit)
export const runtime = 'nodejs'
export const maxDuration = 60
