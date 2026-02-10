import { ImageResponse } from 'next/og'

export const size = { width: 32, height: 32 }
export const contentType = 'image/png'

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          gap: '2px',
          padding: '4px',
          borderRadius: '6px',
          background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
        }}
      >
        {/* Bar chart representing P&L growth */}
        <div style={{ width: '5px', height: '8px', background: '#93c5fd', borderRadius: '1px' }} />
        <div style={{ width: '5px', height: '12px', background: '#60a5fa', borderRadius: '1px' }} />
        <div style={{ width: '5px', height: '16px', background: '#3b82f6', borderRadius: '1px' }} />
        <div style={{ width: '5px', height: '10px', background: '#f87171', borderRadius: '1px' }} />
        <div style={{ width: '5px', height: '22px', background: '#34d399', borderRadius: '1px' }} />
      </div>
    ),
    { ...size }
  )
}
