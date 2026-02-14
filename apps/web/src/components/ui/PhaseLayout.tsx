'use client'

import Link from 'next/link'

interface PhaseLayoutProps {
  phase: number
  title: string
  subtitle?: string
  projectId: string
  children: React.ReactNode
}

var PHASES = [
  { num: 1, label: 'アップロード', icon: '📤', desc: 'テンプレート・事業計画書を取り込み', path: 'new' },
  { num: 2, label: 'BM分析', icon: '🔍', desc: '事業モデルを解析', path: 'phase2' },
  { num: 3, label: 'テンプレマップ', icon: '🗺️', desc: 'シートとセグメントを紐づけ', path: 'phase3' },
  { num: 4, label: 'モデル設計', icon: '🏗️', desc: 'セルにコンセプトを割当', path: 'phase4' },
  { num: 5, label: 'パラメータ抽出', icon: '📊', desc: '数値を自動抽出・確認', path: 'phase5' },
  { num: 6, label: 'シナリオ', icon: '🎮', desc: 'PLをシミュレーション', path: 'scenarios' },
  { num: 7, label: 'エクスポート', icon: '📥', desc: 'Excelファイル出力', path: 'export' },
  { num: 8, label: 'Q&A', icon: '💬', desc: 'Q&A作成・保存', path: 'qa' },
]

export function PhaseLayout({ phase, title, subtitle, projectId, children }: PhaseLayoutProps) {
  return (
    <div className="max-w-[1200px] mx-auto">
      {/* Phase Stepper */}
      <div className="mb-8 relative">
        {/* Admin: LLM Config link */}
        <Link
          href={'/projects/' + projectId + '/llm-config'}
          className="absolute right-0 top-0 text-gray-300 hover:text-purple-500 transition-colors z-10"
          title="LLM設定管理 (管理者専用)"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Link>
        <div className="flex items-center gap-0 overflow-x-auto pb-2">
          {PHASES.map(function(p, i) {
            var isActive = p.num === phase
            var isComplete = p.num < phase
            var href = p.num === 1
              ? '/projects/new'
              : '/projects/' + projectId + '/' + p.path

            return (
              <div key={p.num} className="flex items-center flex-shrink-0">
                <Link
                  href={href}
                  className={'group relative flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-all ' + (
                    isActive
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-200'
                      : isComplete
                        ? 'bg-green-50 text-green-700 hover:bg-green-100'
                        : 'bg-gray-50 text-gray-400 hover:bg-gray-100'
                  )}
                  title={p.desc}
                >
                  <span className={'w-6 h-6 rounded-lg flex items-center justify-center text-xs ' + (
                    isActive ? 'bg-white/20' :
                    isComplete ? 'bg-green-100' :
                    'bg-gray-100'
                  )}>
                    {isComplete ? (
                      <svg className="w-3.5 h-3.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <span className="text-xs">{p.icon}</span>
                    )}
                  </span>
                  <div className="hidden sm:block">
                    <div className={'text-xs font-semibold ' + (isActive ? 'text-white' : '')}>
                      {p.label}
                    </div>
                    {isActive && (
                      <div className="text-[10px] text-blue-100 whitespace-nowrap">{p.desc}</div>
                    )}
                  </div>

                  {/* Tooltip for non-active phases */}
                  {!isActive && (
                    <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 hidden group-hover:block z-10">
                      <div className="bg-gray-800 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap shadow-lg">
                        {p.desc}
                      </div>
                    </div>
                  )}
                </Link>

                {/* Connector */}
                {i < PHASES.length - 1 && (
                  <div className={'w-5 h-0.5 mx-0.5 flex-shrink-0 ' + (
                    isComplete ? 'bg-green-300' :
                    isActive ? 'bg-blue-200' :
                    'bg-gray-200'
                  )} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{PHASES[phase - 1] ? PHASES[phase - 1].icon : ''}</span>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        </div>
        {subtitle && (
          <p className="text-gray-500 ml-11">{subtitle}</p>
        )}
      </div>

      {/* Content */}
      {children}

      {/* Navigation Footer */}
      <div className="mt-10 flex justify-between items-center pt-6 border-t border-gray-100">
        {phase > 1 ? (
          <Link
            href={'/projects/' + projectId + '/' + (PHASES[phase - 2] ? PHASES[phase - 2].path : '')}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {PHASES[phase - 2] ? PHASES[phase - 2].label : ''}
          </Link>
        ) : <div />}

        <div className="flex gap-3">
          {phase < PHASES.length && (
            <Link
              href={'/projects/' + projectId + '/' + (PHASES[phase] ? PHASES[phase].path : '')}
              className={'flex items-center gap-2 px-5 py-2.5 text-sm text-white rounded-xl font-medium transition-colors shadow-sm ' + (
                phase === PHASES.length - 1 ? 'bg-purple-600 hover:bg-purple-700' :
                phase >= 6 ? 'bg-green-600 hover:bg-green-700' :
                'bg-blue-600 hover:bg-blue-700'
              )}
            >
              {PHASES[phase] ? PHASES[phase].label : ''}
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
