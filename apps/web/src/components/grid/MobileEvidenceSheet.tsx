'use client'

import { useState, useEffect, useRef } from 'react'
import { EvidencePanel } from './EvidencePanel'

interface MobileEvidenceSheetProps {
  cell: any | null
  onClose: () => void
}

/**
 * ボトムシート形式のエビデンスパネル（モバイル専用）
 * セル選択時に下からスライドアップ表示
 */
export function MobileEvidenceSheet({ cell, onClose }: MobileEvidenceSheetProps) {
  var [isExpanded, setIsExpanded] = useState(false)
  var [startY, setStartY] = useState(0)
  var [currentY, setCurrentY] = useState(0)
  var [isDragging, setIsDragging] = useState(false)
  var sheetRef = useRef<HTMLDivElement>(null)

  // Reset state when cell changes
  useEffect(function() {
    if (cell) {
      setIsExpanded(false)
      setCurrentY(0)
    }
  }, [cell])

  if (!cell) return null

  function handleTouchStart(e: React.TouchEvent) {
    setStartY(e.touches[0].clientY)
    setIsDragging(true)
  }

  function handleTouchMove(e: React.TouchEvent) {
    if (!isDragging) return
    var diff = e.touches[0].clientY - startY
    setCurrentY(diff)
  }

  function handleTouchEnd() {
    setIsDragging(false)
    if (currentY > 80) {
      // Drag down: close or collapse
      if (isExpanded) {
        setIsExpanded(false)
      } else {
        onClose()
      }
    } else if (currentY < -80) {
      // Drag up: expand
      setIsExpanded(true)
    }
    setCurrentY(0)
  }

  var sheetHeight = isExpanded ? '85vh' : '50vh'
  var translateY = isDragging && currentY > 0 ? currentY : 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Bottom Sheet */}
      <div
        ref={sheetRef}
        className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-white rounded-t-2xl shadow-2xl transition-all duration-300 ease-out"
        style={{
          height: sheetHeight,
          transform: 'translateY(' + translateY + 'px)',
        }}
      >
        {/* Drag Handle */}
        <div
          className="flex items-center justify-center pt-3 pb-2 cursor-grab active:cursor-grabbing"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 pb-2 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">エビデンス</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={function() { setIsExpanded(!isExpanded) }}
              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 active:bg-gray-200"
              title={isExpanded ? '縮小' : '拡大'}
            >
              <svg className={'w-4 h-4 transition-transform ' + (isExpanded ? 'rotate-180' : '')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 active:bg-gray-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto px-4 py-3" style={{ height: 'calc(100% - 60px)' }}>
          <EvidencePanel cell={cell} />
        </div>
      </div>
    </>
  )
}
