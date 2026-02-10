import { ImageResponse } from 'next/og'

export const size = { width: 180, height: 180 }
export const contentType = 'image/png'

export default function AppleIcon() {
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
          borderRadius: '36px',
          background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 50%, #3b82f6 100%)',
        }}
      >
        {/* Chart bars */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center',
            gap: '8px',
            marginBottom: '12px',
          }}
        >
          <div style={{ width: '18px', height: '30px', background: '#93c5fd', borderRadius: '4px' }} />
          <div style={{ width: '18px', height: '48px', background: '#60a5fa', borderRadius: '4px' }} />
          <div style={{ width: '18px', height: '65px', background: '#bfdbfe', borderRadius: '4px' }} />
          <div style={{ width: '18px', height: '40px', background: '#f87171', borderRadius: '4px' }} />
          <div style={{ width: '18px', height: '80px', background: '#34d399', borderRadius: '4px' }} />
        </div>
        {/* PL text */}
        <div
          style={{
            fontSize: '28px',
            fontWeight: 800,
            color: '#ffffff',
            letterSpacing: '3px',
          }}
        >
          P&L
        </div>
      </div>
    ),
    { ...size }
  )
}
