'use client'

import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(function() {
    console.error('[GlobalError]', error)
  }, [error])

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream-50">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-warm-lg p-8 text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4 text-2xl">!</div>
        <h2 className="text-xl font-bold text-dark-900 mb-2">
          エラーが発生しました
        </h2>
        <p className="text-sand-500 mb-6">
          予期しないエラーが発生しました。再試行するか、ホームに戻ってください。
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-dark-900 text-white rounded-2xl hover:bg-dark-800 font-medium shadow-warm-md transition-all"
          >
            再試行
          </button>
          <a
            href="/"
            className="px-5 py-2.5 bg-cream-200 text-dark-900 rounded-2xl hover:bg-cream-300 font-medium transition-all"
          >
            ホームに戻る
          </a>
        </div>
      </div>
    </div>
  )
}
