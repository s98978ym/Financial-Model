/**
 * Keep-alive endpoint — Vercel Cron hits this every 10 minutes
 * to prevent Render free-tier API from sleeping.
 */

import { NextResponse } from 'next/server'

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  try {
    const res = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(10_000), // 10s timeout
    })
    const data = await res.json()
    return NextResponse.json({
      status: 'ok',
      api: data,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    return NextResponse.json(
      {
        status: 'api_unreachable',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      },
      { status: 502 }
    )
  }
}
