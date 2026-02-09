'use client'

import Link from 'next/link'

interface PhaseLayoutProps {
  phase: number
  title: string
  subtitle?: string
  projectId: string
  children: React.ReactNode
}

const PHASES = [
  { num: 1, label: 'アップロード', path: 'new' },
  { num: 2, label: 'BM分析', path: 'phase2' },
  { num: 3, label: 'テンプレマップ', path: 'phase3' },
  { num: 4, label: 'モデル設計', path: 'phase4' },
  { num: 5, label: 'パラメータ抽出', path: 'phase5' },
  { num: 6, label: 'シナリオ', path: 'scenarios' },
]

export function PhaseLayout({ phase, title, subtitle, projectId, children }: PhaseLayoutProps) {
  return (
    <div>
      {/* Phase Stepper */}
      <div className="flex items-center gap-1 mb-6 overflow-x-auto">
        {PHASES.map((p, i) => {
          const isActive = p.num === phase
          const isComplete = p.num < phase
          const href = p.num === 1
            ? `/projects/new`
            : `/projects/${projectId}/${p.path}`

          return (
            <div key={p.num} className="flex items-center">
              <Link
                href={href}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : isComplete
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-gray-100 text-gray-400'
                }`}
              >
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                  isActive ? 'bg-white text-blue-600' :
                  isComplete ? 'bg-green-500 text-white' :
                  'bg-gray-300 text-white'
                }`}>
                  {isComplete ? '✓' : p.num}
                </span>
                <span className="hidden sm:inline whitespace-nowrap">{p.label}</span>
              </Link>
              {i < PHASES.length - 1 && (
                <div className={`w-6 h-0.5 mx-1 ${
                  isComplete ? 'bg-green-400' : 'bg-gray-200'
                }`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {subtitle && (
          <p className="text-gray-500 mt-1">{subtitle}</p>
        )}
      </div>

      {/* Content */}
      {children}

      {/* Navigation Footer */}
      <div className="mt-8 flex justify-between items-center pt-6 border-t border-gray-200">
        {phase > 1 ? (
          <Link
            href={`/projects/${projectId}/${PHASES[phase - 2]?.path || ''}`}
            className="text-gray-600 hover:text-gray-800 text-sm"
          >
            &larr; 前のフェーズ
          </Link>
        ) : <div />}

        <div className="flex gap-3">
          <button className="px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
            下書き保存
          </button>
          {phase < 6 && (
            <Link
              href={`/projects/${projectId}/${PHASES[phase]?.path || 'export'}`}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              次のフェーズ &rarr;
            </Link>
          )}
          {phase === 6 && (
            <Link
              href={`/projects/${projectId}/export`}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Excel エクスポート
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
