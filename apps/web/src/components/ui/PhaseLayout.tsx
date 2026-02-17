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
  { num: 1, label: 'アップロード', desc: 'テンプレート・事業計画書を取り込み', path: 'new' },
  { num: 2, label: 'BM分析', desc: '事業モデルを解析', path: 'phase2' },
  { num: 3, label: 'テンプレマップ', desc: 'シートとセグメントを紐づけ', path: 'phase3' },
  { num: 4, label: 'モデル設計', desc: 'セルにコンセプトを割当', path: 'phase4' },
  { num: 5, label: 'パラメータ抽出', desc: '数値を自動抽出・確認', path: 'phase5' },
  { num: 6, label: 'シナリオ', desc: 'PLをシミュレーション', path: 'scenarios' },
  { num: 7, label: 'エクスポート', desc: 'Excelファイル出力', path: 'export' },
  { num: 8, label: 'Q&A', desc: 'Q&A作成・保存', path: 'qa' },
]

export function PhaseLayout({ phase, title, subtitle, projectId, children }: PhaseLayoutProps) {
  return (
    <div className="max-w-[1200px] mx-auto">
      {/* Phase Stepper */}
      <div className="mb-8 relative">
        {/* Admin: LLM Config link */}
        <Link
          href={'/projects/' + projectId + '/llm-config'}
          className="absolute right-0 top-0 text-sand-300 hover:text-gold-500 transition-colors z-10"
          title="LLM設定管理 (管理者専用)"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Link>

        {/* Mobile: Dot stepper */}
        <div className="sm:hidden">
          <div className="flex items-center justify-center gap-2 mb-3">
            {PHASES.map(function(p) {
              var isActive = p.num === phase
              var isComplete = p.num < phase
              return (
                <Link
                  key={p.num}
                  href={p.num === 1 ? '/projects/new' : '/projects/' + projectId + '/' + p.path}
                  className={
                    'rounded-full transition-all flex-shrink-0 ' +
                    (isActive
                      ? 'w-3 h-3 bg-gold-500 ring-4 ring-gold-200'
                      : isComplete
                        ? 'w-2.5 h-2.5 bg-gold-400'
                        : 'w-2 h-2 bg-cream-400')
                  }
                  title={p.label + ': ' + p.desc}
                />
              )
            })}
          </div>
          <div className="text-center">
            <span className="text-xs text-sand-400">Phase {phase}/{PHASES.length}</span>
            <span className="mx-2 text-cream-400">|</span>
            <span className="text-xs font-semibold text-gold-600">
              {PHASES[phase - 1] ? PHASES[phase - 1].label : ''}
            </span>
          </div>
        </div>

        {/* Desktop: Horizontal stepper */}
        <div className="hidden sm:block">
          <div className="bg-white rounded-3xl shadow-warm p-2 flex items-center gap-0 overflow-x-auto">
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
                    className={'group relative flex items-center gap-2 px-3.5 py-2.5 rounded-2xl text-sm transition-all ' + (
                      isActive
                        ? 'bg-dark-900 text-white shadow-warm-md'
                        : isComplete
                          ? 'text-gold-600 hover:bg-cream-100'
                          : 'text-sand-400 hover:bg-cream-100'
                    )}
                    title={p.desc}
                  >
                    <span className={'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ' + (
                      isActive ? 'bg-gold-500 text-white' :
                      isComplete ? 'bg-gold-100 text-gold-600' :
                      'bg-cream-200 text-sand-400'
                    )}>
                      {isComplete ? (
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <span>{p.num}</span>
                      )}
                    </span>
                    <div>
                      <div className={'text-xs font-semibold ' + (isActive ? 'text-white' : '')}>
                        {p.label}
                      </div>
                      {isActive && (
                        <div className="text-[10px] text-white/50 whitespace-nowrap">{p.desc}</div>
                      )}
                    </div>

                    {/* Tooltip */}
                    {!isActive && (
                      <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 hidden group-hover:block z-10">
                        <div className="bg-dark-900 text-white text-[10px] px-2.5 py-1.5 rounded-xl whitespace-nowrap shadow-warm-md">
                          {p.desc}
                        </div>
                      </div>
                    )}
                  </Link>

                  {/* Connector */}
                  {i < PHASES.length - 1 && (
                    <div className={'w-4 h-0.5 mx-0.5 flex-shrink-0 rounded-full ' + (
                      isComplete ? 'bg-gold-300' :
                      isActive ? 'bg-cream-300' :
                      'bg-cream-300'
                    )} />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-dark-900">{title}</h1>
        {subtitle && (
          <p className="text-sand-500 mt-1">{subtitle}</p>
        )}
      </div>

      {/* Content */}
      {children}

      {/* Navigation Footer */}
      <div className="mt-10 flex justify-between items-center pt-6 border-t border-cream-300">
        {phase > 1 ? (
          <Link
            href={'/projects/' + projectId + '/' + (PHASES[phase - 2] ? PHASES[phase - 2].path : '')}
            className="flex items-center gap-2 text-sand-500 hover:text-dark-900 text-sm transition-colors min-h-[44px] px-3 rounded-xl hover:bg-white"
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
              className="flex items-center gap-2 px-5 py-3 text-sm text-white rounded-2xl font-medium transition-all shadow-warm-sm hover:shadow-warm min-h-[44px] bg-dark-900 hover:bg-dark-800"
            >
              {PHASES[phase] ? PHASES[phase].label : ''}
              <svg className="w-4 h-4 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
