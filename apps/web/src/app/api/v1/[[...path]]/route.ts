/**
 * Catch-all API proxy route.
 *
 * Proxies /api/v1/* requests to the FastAPI backend.
 * This avoids CORS issues and handles large file uploads
 * (Vercel rewrites have a 4.5MB body limit, but API routes support up to 50MB).
 */

import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname.replace('/api/v1', '/v1')
  const url = `${BACKEND_URL}${path}${req.nextUrl.search}`

  const headers = new Headers()
  // Forward relevant headers (skip host and other hop-by-hop headers)
  req.headers.forEach((value, key) => {
    if (!['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) {
      headers.set(key, value)
    }
  })

  try {
    const res = await fetch(url, {
      method: req.method,
      headers,
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
      // @ts-ignore - duplex is required for streaming request body
      duplex: 'half',
    })

    // Stream the response back
    const responseHeaders = new Headers()
    res.headers.forEach((value, key) => {
      if (!['transfer-encoding', 'content-encoding'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value)
      }
    })

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    })
  } catch (error) {
    console.error('API proxy error:', error)
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

// Route Segment Config for App Router
export const runtime = 'edge'
export const maxDuration = 60
