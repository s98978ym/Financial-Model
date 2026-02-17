'use client'

import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { api } from '@/lib/api'

var PHASE_LABELS: Record<number, string> = {
  1: 'アップロード',
  2: 'BM分析',
  3: 'テンプレ',
  4: 'モデル設計',
  5: 'パラメータ',
  6: 'シナリオ',
  7: 'エクスポート',
  8: 'Q&A',
}

var MAX_PIPELINE_PHASE = 8

var STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  created: { label: '作成済み', color: 'text-sand-500', dot: 'bg-sand-400' },
  active: { label: '進行中', color: 'text-gold-600', dot: 'bg-gold-500' },
  completed: { label: '完了', color: 'text-emerald-600', dot: 'bg-emerald-500' },
  archived: { label: 'アーカイブ', color: 'text-sand-400', dot: 'bg-sand-300' },
}

function formatDate(dateStr: string): string {
  var d = new Date(dateStr)
  return d.getFullYear() + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + String(d.getDate()).padStart(2, '0')
}

function formatDateTime(dateStr: string): string {
  var d = new Date(dateStr)
  return formatDate(dateStr) + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
}

function getPhaseRoute(projectId: string, phase: number): string {
  if (phase <= 1) return '/projects/' + projectId + '/phase2'
  if (phase === 2) return '/projects/' + projectId + '/phase2'
  if (phase === 3) return '/projects/' + projectId + '/phase3'
  if (phase === 4) return '/projects/' + projectId + '/phase4'
  if (phase === 5) return '/projects/' + projectId + '/phase5'
  if (phase === 6) return '/projects/' + projectId + '/scenarios'
  if (phase === 7) return '/projects/' + projectId + '/export'
  if (phase === 8) return '/projects/' + projectId + '/qa'
  return '/projects/' + projectId + '/phase2'
}

export default function DashboardPage() {
  var queryClient = useQueryClient()
  var { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: api.listProjects,
  })

  var [editingMemo, setEditingMemo] = useState<string | null>(null)
  var [memoText, setMemoText] = useState('')
  var [deletingId, setDeletingId] = useState<string | null>(null)
  var [filter, setFilter] = useState<string>('all')
  var [sortBy, setSortBy] = useState<'date' | 'name' | 'phase'>('date')

  var updateMutation = useMutation({
    mutationFn: function(args: { id: string; body: any }) {
      return api.updateProject(args.id, args.body)
    },
    onSuccess: function() {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  var deleteMutation = useMutation({
    mutationFn: function(id: string) {
      return api.deleteProject(id)
    },
    onSuccess: function() {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setDeletingId(null)
    },
  })

  var handleMemoSave = useCallback(function(projectId: string) {
    updateMutation.mutate({ id: projectId, body: { memo: memoText } })
    setEditingMemo(null)
  }, [memoText, updateMutation])

  var handleStartEditMemo = useCallback(function(projectId: string, currentMemo: string) {
    setEditingMemo(projectId)
    setMemoText(currentMemo || '')
  }, [])

  var filteredProjects = projects ? projects.filter(function(p: any) {
    if (filter === 'all') return true
    return p.status === filter
  }) : []

  var sortedProjects = filteredProjects.slice().sort(function(a: any, b: any) {
    if (sortBy === 'name') return a.name.localeCompare(b.name)
    if (sortBy === 'phase') return b.current_phase - a.current_phase
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  var statusCounts: Record<string, number> = {}
  if (projects) {
    projects.forEach(function(p: any) {
      statusCounts[p.status] = (statusCounts[p.status] || 0) + 1
    })
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-10 gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-dark-900 tracking-tight">プロジェクト</h1>
          <p className="text-sand-500 mt-1 text-sm hidden sm:block">収益計画の管理と進捗確認</p>
        </div>
        <Link
          href="/projects/new"
          className="group flex items-center gap-2 bg-dark-900 text-white px-5 py-3 rounded-2xl hover:bg-dark-800 transition-all shadow-warm-md hover:shadow-warm-lg font-medium min-h-[44px] flex-shrink-0"
        >
          <svg className="w-5 h-5 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          <span className="hidden sm:inline">新規プロジェクト</span>
          <span className="sm:hidden">新規</span>
        </Link>
      </div>

      {/* Summary Cards */}
      {projects && projects.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-8">
          <button
            onClick={function() { setFilter('all') }}
            className={'rounded-3xl p-5 transition-all text-left ' + (
              filter === 'all'
                ? 'bg-dark-900 shadow-warm-md'
                : 'bg-white shadow-warm hover:shadow-warm-md'
            )}
          >
            <div className={'text-3xl font-bold ' + (filter === 'all' ? 'text-white' : 'text-dark-900')}>{projects.length}</div>
            <div className={'text-xs mt-1 font-medium ' + (filter === 'all' ? 'text-white/50' : 'text-sand-400')}>全プロジェクト</div>
          </button>
          {Object.keys(STATUS_CONFIG).map(function(status) {
            var config = STATUS_CONFIG[status]
            var count = statusCounts[status] || 0
            if (count === 0 && status !== 'active') return null
            return (
              <button
                key={status}
                onClick={function() { setFilter(filter === status ? 'all' : status) }}
                className={'rounded-3xl p-5 transition-all text-left ' + (
                  filter === status
                    ? 'bg-dark-900 shadow-warm-md'
                    : 'bg-white shadow-warm hover:shadow-warm-md'
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={'w-2 h-2 rounded-full ' + (filter === status ? 'bg-gold-400' : config.dot)} />
                </div>
                <div className={'text-3xl font-bold ' + (filter === status ? 'text-white' : 'text-dark-900')}>{count}</div>
                <div className={'text-xs mt-1 font-medium ' + (filter === status ? 'text-white/50' : config.color)}>{config.label}</div>
              </button>
            )
          })}
        </div>
      )}

      {/* Sort Controls */}
      {projects && projects.length > 0 && (
        <div className="flex items-center gap-2 mb-6">
          <span className="text-xs text-sand-400 mr-1">並び替え</span>
          {[
            { key: 'date' as const, label: '作成日' },
            { key: 'name' as const, label: '名前' },
            { key: 'phase' as const, label: 'フェーズ' },
          ].map(function(opt) {
            return (
              <button
                key={opt.key}
                onClick={function() { setSortBy(opt.key) }}
                className={'text-xs px-3.5 py-2 rounded-full transition-all font-medium ' + (
                  sortBy === opt.key
                    ? 'bg-dark-900 text-white shadow-warm-sm'
                    : 'bg-white text-sand-500 shadow-warm-sm hover:shadow-warm'
                )}
              >
                {opt.label}
              </button>
            )
          })}
        </div>
      )}

      {/* Project List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <div className="text-center">
            <div className="relative w-12 h-12 mx-auto mb-4">
              <div className="absolute inset-0 rounded-full border-2 border-cream-300"></div>
              <div className="absolute inset-0 rounded-full border-2 border-gold-500 border-t-transparent animate-spin"></div>
            </div>
            <p className="text-sand-400 text-sm">読み込み中...</p>
          </div>
        </div>
      ) : sortedProjects.length > 0 ? (
        <div className="space-y-4">
          {sortedProjects.map(function(project: any) {
            var statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.created
            var displayPhase = Math.min(project.current_phase, MAX_PIPELINE_PHASE)
            var phaseLabel = PHASE_LABELS[displayPhase] || ('Phase ' + displayPhase)
            var phaseProgress = Math.round((displayPhase / MAX_PIPELINE_PHASE) * 100)
            var isEditingThisMemo = editingMemo === project.id
            var isDeleting = deletingId === project.id

            return (
              <div
                key={project.id}
                className="bg-white rounded-3xl shadow-warm hover:shadow-warm-md transition-all duration-300 overflow-hidden"
              >
                <div className="p-6 sm:p-7">
                  {/* Top Row */}
                  <div className="flex items-start gap-4">
                    {/* Circular Progress */}
                    <div className="hidden sm:block relative w-14 h-14 flex-shrink-0">
                      <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
                        <circle cx="28" cy="28" r="24" fill="none" stroke="#F5F0EA" strokeWidth="4" />
                        <circle
                          cx="28" cy="28" r="24" fill="none"
                          stroke={displayPhase >= MAX_PIPELINE_PHASE ? '#22c55e' : '#D4A853'}
                          strokeWidth="4"
                          strokeLinecap="round"
                          strokeDasharray={String(2 * Math.PI * 24)}
                          strokeDashoffset={String(2 * Math.PI * 24 * (1 - displayPhase / MAX_PIPELINE_PHASE))}
                          className="transition-all duration-700"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xs font-bold text-dark-900">{displayPhase}/{MAX_PIPELINE_PHASE}</span>
                      </div>
                    </div>

                    {/* Project Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1 flex-wrap">
                        <Link
                          href={getPhaseRoute(project.id, project.current_phase)}
                          className="text-lg font-bold text-dark-900 hover:text-gold-600 transition-colors truncate"
                        >
                          {project.name}
                        </Link>
                        <span className={'inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full font-medium bg-cream-200 ' + statusConfig.color}>
                          <span className={'w-1.5 h-1.5 rounded-full ' + statusConfig.dot}></span>
                          {statusConfig.label}
                        </span>
                      </div>

                      {/* Meta */}
                      <div className="flex items-center gap-4 text-xs text-sand-400">
                        <span>{formatDate(project.created_at)}</span>
                        <span className="hidden sm:inline">{formatDateTime(project.updated_at)}</span>
                      </div>

                      {/* Phase Label */}
                      <div className="mt-3 flex items-center gap-2">
                        <span className="text-xs font-semibold text-gold-600 bg-gold-500/10 px-3 py-1 rounded-full">
                          {phaseLabel}
                        </span>
                        <span className="text-xs text-sand-400">{phaseProgress}%</span>
                      </div>

                      {/* Dot Progress */}
                      <div className="flex items-center gap-1.5 mt-3">
                        {[1, 2, 3, 4, 5, 6, 7, 8].map(function(phase) {
                          var isDone = phase < displayPhase
                          var isCurrent = phase === displayPhase
                          return (
                            <div
                              key={phase}
                              className={'rounded-full transition-all duration-500 ' + (
                                isDone
                                  ? 'w-2.5 h-2.5 bg-gold-500'
                                  : isCurrent
                                    ? 'w-3 h-3 bg-gold-400 ring-4 ring-gold-100'
                                    : 'w-2 h-2 bg-cream-300'
                              )}
                              title={'Phase ' + phase + ': ' + (PHASE_LABELS[phase] || '')}
                            />
                          )
                        })}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Link
                        href={getPhaseRoute(project.id, project.current_phase)}
                        className="flex items-center gap-1.5 px-5 py-2.5 rounded-2xl text-sm font-medium text-white bg-dark-900 hover:bg-dark-800 transition-all shadow-warm-sm hover:shadow-warm min-h-[44px]"
                      >
                        <span className="hidden sm:inline">続ける</span>
                        <svg className="w-4 h-4 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </Link>
                      <button
                        onClick={function() { handleStartEditMemo(project.id, project.memo || '') }}
                        className="w-10 h-10 rounded-xl bg-cream-100 text-sand-400 hover:bg-cream-200 hover:text-sand-600 transition-all flex items-center justify-center"
                        title="メモを編集"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {!isDeleting ? (
                        <button
                          onClick={function() { setDeletingId(project.id) }}
                          className="w-10 h-10 rounded-xl bg-cream-100 text-sand-300 hover:bg-red-50 hover:text-red-400 transition-all flex items-center justify-center"
                          title="削除"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={function() { deleteMutation.mutate(project.id) }}
                            disabled={deleteMutation.isPending}
                            className="px-3 py-2 rounded-xl text-xs font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 transition-all min-h-[44px]"
                          >
                            {deleteMutation.isPending ? '削除中...' : '削除する'}
                          </button>
                          <button
                            onClick={function() { setDeletingId(null) }}
                            className="px-3 py-2 rounded-xl text-xs font-medium text-sand-500 bg-cream-200 hover:bg-cream-300 transition-all min-h-[44px]"
                          >
                            取消
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Memo Section */}
                  {isEditingThisMemo ? (
                    <div className="mt-5 sm:ml-[72px] flex gap-2">
                      <input
                        type="text"
                        value={memoText}
                        onChange={function(e) { setMemoText(e.target.value) }}
                        onKeyDown={function(e) {
                          if (e.key === 'Enter') handleMemoSave(project.id)
                          if (e.key === 'Escape') setEditingMemo(null)
                        }}
                        placeholder="メモを入力..."
                        className="flex-1 text-sm bg-cream-100 border-0 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-gold-400/30 transition-all placeholder:text-sand-300"
                        autoFocus
                      />
                      <button
                        onClick={function() { handleMemoSave(project.id) }}
                        disabled={updateMutation.isPending}
                        className="px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-dark-900 hover:bg-dark-800 disabled:opacity-50 transition-all"
                      >
                        保存
                      </button>
                      <button
                        onClick={function() { setEditingMemo(null) }}
                        className="px-3 py-2.5 rounded-xl text-sm text-sand-500 bg-cream-200 hover:bg-cream-300 transition-all"
                      >
                        取消
                      </button>
                    </div>
                  ) : project.memo ? (
                    <button
                      onClick={function() { handleStartEditMemo(project.id, project.memo || '') }}
                      className="mt-4 sm:ml-[72px] text-left group/memo"
                    >
                      <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-cream-100 hover:bg-cream-200 transition-all">
                        <svg className="w-3.5 h-3.5 text-sand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                        </svg>
                        <span className="text-sm text-sand-600">{project.memo}</span>
                      </div>
                    </button>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      ) : projects && projects.length > 0 ? (
        <div className="text-center py-16 bg-white rounded-3xl shadow-warm">
          <p className="text-sand-500 text-sm mb-2">フィルター条件に一致するプロジェクトがありません</p>
          <button
            onClick={function() { setFilter('all') }}
            className="text-gold-600 hover:text-gold-500 text-sm font-medium transition-colors"
          >
            フィルターをリセット
          </button>
        </div>
      ) : (
        <div className="text-center py-24 bg-white rounded-3xl shadow-warm relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-gold-300/20 to-transparent rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-cream-300/60 to-transparent rounded-full translate-y-1/2 -translate-x-1/2" />
          <div className="relative">
            <div className="w-16 h-16 rounded-3xl bg-cream-200 flex items-center justify-center mx-auto mb-5">
              <svg className="w-7 h-7 text-gold-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-dark-900 mb-1 font-semibold">プロジェクトがありません</p>
            <p className="text-sand-400 text-sm mb-6">最初のプロジェクトを作成して収益計画を始めましょう</p>
            <Link
              href="/projects/new"
              className="inline-flex items-center gap-2 bg-dark-900 text-white px-6 py-3 rounded-2xl hover:bg-dark-800 transition-all shadow-warm-md font-medium"
            >
              <svg className="w-5 h-5 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              プロジェクトを作成
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
