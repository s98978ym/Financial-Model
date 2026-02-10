import { ImageResponse } from 'next/og'

export const alt = 'PL Generator — AI-powered financial model generator'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e40af 100%)',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        {/* Chart bars decoration */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center',
            gap: '16px',
            marginBottom: '40px',
          }}
        >
          <div style={{ width: '40px', height: '60px', background: '#93c5fd', borderRadius: '8px', opacity: 0.8 }} />
          <div style={{ width: '40px', height: '100px', background: '#60a5fa', borderRadius: '8px', opacity: 0.85 }} />
          <div style={{ width: '40px', height: '140px', background: '#3b82f6', borderRadius: '8px', opacity: 0.9 }} />
          <div style={{ width: '40px', height: '80px', background: '#f87171', borderRadius: '8px', opacity: 0.8 }} />
          <div style={{ width: '40px', height: '180px', background: '#34d399', borderRadius: '8px' }} />
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: '72px',
            fontWeight: 800,
            color: '#ffffff',
            marginBottom: '16px',
            letterSpacing: '-1px',
          }}
        >
          PL Generator
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: '28px',
            color: '#94a3b8',
            letterSpacing: '2px',
          }}
        >
          AI-powered Financial Model Generator
        </div>
      </div>
    ),
    { ...size }
  )
}
