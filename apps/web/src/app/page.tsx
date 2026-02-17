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

var PHASE_ICONS: Record<number, string> = {
  1: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12',
  2: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  3: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z',
  4: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  5: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01',
  6: 'M13 10V3L4 14h7v7l9-11h-7z',
  7: 'M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  8: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
}

var PHASE_COLORS: Record<number, { bg: string; text: string; ring: string; gradient: string }> = {
  1: { bg: 'bg-slate-100', text: 'text-slate-600', ring: 'ring-slate-200', gradient: 'from-slate-400 to-slate-500' },
  2: { bg: 'bg-blue-100', text: 'text-blue-600', ring: 'ring-blue-200', gradient: 'from-blue-400 to-blue-600' },
  3: { bg: 'bg-violet-100', text: 'text-violet-600', ring: 'ring-violet-200', gradient: 'from-violet-400 to-violet-600' },
  4: { bg: 'bg-amber-100', text: 'text-amber-600', ring: 'ring-amber-200', gradient: 'from-amber-400 to-amber-500' },
  5: { bg: 'bg-rose-100', text: 'text-rose-600', ring: 'ring-rose-200', gradient: 'from-rose-400 to-rose-500' },
  6: { bg: 'bg-cyan-100', text: 'text-cyan-600', ring: 'ring-cyan-200', gradient: 'from-cyan-400 to-cyan-600' },
  7: { bg: 'bg-emerald-100', text: 'text-emerald-600', ring: 'ring-emerald-200', gradient: 'from-emerald-400 to-emerald-600' },
  8: { bg: 'bg-indigo-100', text: 'text-indigo-600', ring: 'ring-indigo-200', gradient: 'from-indigo-400 to-indigo-600' },
}

var STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string; icon: string }> = {
  created: { label: '作成済み', bg: 'bg-gray-50', text: 'text-gray-600', dot: 'bg-gray-400', icon: 'M12 6v6m0 0v6m0-6h6m-6 0H6' },
  active: { label: '進行中', bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500', icon: 'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z' },
  completed: { label: '完了', bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
  archived: { label: 'アーカイブ', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', icon: 'M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4' },
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">

        {/* Header */}
        <div className="relative mb-8 sm:mb-10">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-3 mb-1.5">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-600/20">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight">プロジェクト管理</h1>
                  <p className="text-gray-400 text-xs sm:text-sm hidden sm:block">収益計画プロジェクトの作成・管理・進捗確認</p>
                </div>
              </div>
            </div>
            <Link
              href="/projects/new"
              className="group flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-2.5 sm:py-3 rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg shadow-blue-600/25 hover:shadow-xl hover:shadow-blue-600/30 font-medium min-h-[44px] flex-shrink-0"
            >
              <svg className="w-5 h-5 transition-transform group-hover:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden sm:inline">新規プロジェクト</span>
              <span className="sm:hidden">新規</span>
            </Link>
          </div>
        </div>

        {/* Status Summary Cards */}
        {projects && projects.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
            <button
              onClick={function() { setFilter('all') }}
              className={'group relative rounded-2xl p-4 sm:p-5 border transition-all text-left overflow-hidden ' + (
                filter === 'all'
                  ? 'border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-md shadow-blue-100/50 ring-1 ring-blue-200'
                  : 'border-gray-200/80 bg-white hover:border-gray-300 hover:shadow-sm'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className={'w-8 h-8 rounded-lg flex items-center justify-center ' + (
                  filter === 'all' ? 'bg-blue-100' : 'bg-gray-100'
                )}>
                  <svg className={'w-4 h-4 ' + (filter === 'all' ? 'text-blue-600' : 'text-gray-500')} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </div>
              </div>
              <div className={'text-2xl sm:text-3xl font-bold ' + (filter === 'all' ? 'text-blue-700' : 'text-gray-900')}>{projects.length}</div>
              <div className={'text-xs mt-0.5 font-medium ' + (filter === 'all' ? 'text-blue-500' : 'text-gray-400')}>全プロジェクト</div>
            </button>
            {Object.keys(STATUS_CONFIG).map(function(status) {
              var config = STATUS_CONFIG[status]
              var count = statusCounts[status] || 0
              if (count === 0 && status !== 'active') return null
              return (
                <button
                  key={status}
                  onClick={function() { setFilter(filter === status ? 'all' : status) }}
                  className={'group relative rounded-2xl p-4 sm:p-5 border transition-all text-left overflow-hidden ' + (
                    filter === status
                      ? 'border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-md shadow-blue-100/50 ring-1 ring-blue-200'
                      : 'border-gray-200/80 bg-white hover:border-gray-300 hover:shadow-sm'
                  )}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className={'w-8 h-8 rounded-lg flex items-center justify-center ' + config.bg}>
                      <svg className={'w-4 h-4 ' + config.text} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={config.icon} />
                      </svg>
                    </div>
                  </div>
                  <div className={'text-2xl sm:text-3xl font-bold ' + (filter === status ? 'text-blue-700' : 'text-gray-900')}>{count}</div>
                  <div className={'text-xs mt-0.5 font-medium ' + config.text}>{config.label}</div>
                </button>
              )
            })}
          </div>
        )}

        {/* Sort Controls */}
        {projects && projects.length > 0 && (
          <div className="flex items-center gap-2 mb-5">
            <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
            </svg>
            <span className="text-xs text-gray-400 mr-1">並び替え</span>
            {[
              { key: 'date' as const, label: '作成日', icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
              { key: 'name' as const, label: '名前', icon: 'M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4' },
              { key: 'phase' as const, label: 'フェーズ', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
            ].map(function(opt) {
              return (
                <button
                  key={opt.key}
                  onClick={function() { setSortBy(opt.key) }}
                  className={'flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all border ' + (
                    sortBy === opt.key
                      ? 'bg-gray-900 text-white border-gray-900 shadow-sm'
                      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300 hover:text-gray-700'
                  )}
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={opt.icon} />
                  </svg>
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
                <div className="absolute inset-0 rounded-full border-2 border-blue-100"></div>
                <div className="absolute inset-0 rounded-full border-2 border-blue-600 border-t-transparent animate-spin"></div>
              </div>
              <p className="text-gray-400 text-sm">プロジェクトを読み込み中...</p>
            </div>
          </div>
        ) : sortedProjects.length > 0 ? (
          <div className="space-y-4">
            {sortedProjects.map(function(project: any) {
              var statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.created
              var displayPhase = Math.min(project.current_phase, MAX_PIPELINE_PHASE)
              var phaseLabel = PHASE_LABELS[displayPhase] || ('Phase ' + displayPhase)
              var phaseProgress = Math.round((displayPhase / MAX_PIPELINE_PHASE) * 100)
              var phaseColor = PHASE_COLORS[displayPhase] || PHASE_COLORS[1]
              var isEditingThisMemo = editingMemo === project.id
              var isDeleting = deletingId === project.id

              return (
                <div
                  key={project.id}
                  className="group relative bg-white rounded-2xl border border-gray-200/80 overflow-hidden hover:shadow-lg hover:shadow-gray-200/50 hover:border-gray-300/80 transition-all duration-300"
                >
                  {/* Top gradient accent */}
                  <div className={'absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ' + phaseColor.gradient} />

                  <div className="p-5 sm:p-6 pt-5">
                    {/* Top Row: Phase Icon + Name + Status + Actions */}
                    <div className="flex items-start gap-3 sm:gap-4">
                      {/* Phase Icon */}
                      <div className={'hidden sm:flex w-12 h-12 rounded-xl items-center justify-center flex-shrink-0 ring-1 ' + phaseColor.bg + ' ' + phaseColor.ring}>
                        <svg className={'w-5 h-5 ' + phaseColor.text} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d={PHASE_ICONS[displayPhase] || PHASE_ICONS[1]} />
                        </svg>
                      </div>

                      {/* Project Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 sm:gap-3 mb-1.5 flex-wrap">
                          <Link
                            href={getPhaseRoute(project.id, project.current_phase)}
                            className="text-base sm:text-lg font-bold text-gray-900 hover:text-blue-600 transition-colors truncate"
                          >
                            {project.name}
                          </Link>
                          <span className={'inline-flex items-center gap-1.5 flex-shrink-0 text-xs px-2.5 py-1 rounded-full font-medium ' + statusConfig.bg + ' ' + statusConfig.text}>
                            <span className={'w-1.5 h-1.5 rounded-full ' + statusConfig.dot}></span>
                            {statusConfig.label}
                          </span>
                        </div>

                        {/* Meta Info */}
                        <div className="flex items-center gap-3 sm:gap-4 text-xs text-gray-400">
                          <span className="flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            {formatDate(project.created_at)}
                          </span>
                          <span className="hidden sm:flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {formatDateTime(project.updated_at)}
                          </span>
                          {project.template_id && (
                            <span className="hidden sm:flex items-center gap-1 text-gray-300">
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                              </svg>
                              {project.template_id}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Link
                          href={getPhaseRoute(project.id, project.current_phase)}
                          className="group/btn flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md shadow-blue-600/20 hover:shadow-lg hover:shadow-blue-600/30 min-h-[44px]"
                        >
                          <span className="hidden sm:inline">続ける</span>
                          <svg className="w-4 h-4 transition-transform group-hover/btn:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                          </svg>
                        </Link>
                        <button
                          onClick={function() { handleStartEditMemo(project.id, project.memo || '') }}
                          className="p-2.5 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 hover:text-gray-600 hover:border-gray-300 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
                          title="メモを編集"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        {!isDeleting ? (
                          <button
                            onClick={function() { setDeletingId(project.id) }}
                            className="p-2.5 rounded-xl border border-gray-200 text-gray-300 hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
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
                              className="px-3 py-2.5 rounded-xl text-xs font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 transition-all shadow-sm min-h-[44px]"
                            >
                              {deleteMutation.isPending ? '削除中...' : '削除する'}
                            </button>
                            <button
                              onClick={function() { setDeletingId(null) }}
                              className="px-3 py-2.5 rounded-xl text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-all min-h-[44px]"
                            >
                              取消
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Phase Progress */}
                    <div className="mt-5 sm:ml-16">
                      <div className="flex items-center justify-between mb-2.5">
                        <div className="flex items-center gap-2">
                          <span className={'inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg ' + phaseColor.bg + ' ' + phaseColor.text}>
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d={PHASE_ICONS[displayPhase] || PHASE_ICONS[1]} />
                            </svg>
                            Phase {displayPhase}
                          </span>
                          <span className="text-xs font-medium text-gray-600">{phaseLabel}</span>
                        </div>
                        <span className="text-xs font-bold text-gray-400">{phaseProgress}%</span>
                      </div>

                      {/* Step Progress Bar */}
                      <div className="flex gap-1.5">
                        {[1, 2, 3, 4, 5, 6, 7, 8].map(function(phase) {
                          var isDone = phase < displayPhase
                          var isCurrent = phase === displayPhase
                          var pColor = PHASE_COLORS[phase] || PHASE_COLORS[1]
                          return (
                            <div
                              key={phase}
                              className="flex-1 group/step relative"
                              title={'Phase ' + phase + ': ' + (PHASE_LABELS[phase] || '')}
                            >
                              <div className={'h-2 rounded-full transition-all duration-500 ' + (
                                isDone
                                  ? 'bg-gradient-to-r ' + pColor.gradient
                                  : isCurrent
                                    ? 'bg-gradient-to-r ' + pColor.gradient + ' animate-pulse'
                                    : 'bg-gray-100'
                              )} />
                            </div>
                          )
                        })}
                      </div>

                      {/* Phase Labels Row */}
                      <div className="hidden sm:flex gap-1.5 mt-1.5">
                        {[1, 2, 3, 4, 5, 6, 7, 8].map(function(phase) {
                          var isDone = phase < displayPhase
                          var isCurrent = phase === displayPhase
                          return (
                            <div key={phase} className="flex-1 text-center">
                              <span className={'text-[10px] leading-none font-medium transition-colors ' + (
                                isCurrent ? PHASE_COLORS[phase].text :
                                isDone ? 'text-gray-400' :
                                'text-gray-200'
                              )}>
                                {PHASE_LABELS[phase]}
                              </span>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Memo Section */}
                    {isEditingThisMemo ? (
                      <div className="mt-4 sm:ml-16 flex gap-2">
                        <input
                          type="text"
                          value={memoText}
                          onChange={function(e) { setMemoText(e.target.value) }}
                          onKeyDown={function(e) {
                            if (e.key === 'Enter') handleMemoSave(project.id)
                            if (e.key === 'Escape') setEditingMemo(null)
                          }}
                          placeholder="メモを入力（例: クライアントA社向け、第2四半期見直し）"
                          className="flex-1 text-sm border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all bg-gray-50 focus:bg-white"
                          autoFocus
                        />
                        <button
                          onClick={function() { handleMemoSave(project.id) }}
                          disabled={updateMutation.isPending}
                          className="px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-all shadow-sm"
                        >
                          保存
                        </button>
                        <button
                          onClick={function() { setEditingMemo(null) }}
                          className="px-3 py-2.5 rounded-xl text-sm text-gray-500 bg-gray-100 hover:bg-gray-200 transition-all"
                        >
                          取消
                        </button>
                      </div>
                    ) : project.memo ? (
                      <button
                        onClick={function() { handleStartEditMemo(project.id, project.memo || '') }}
                        className="mt-4 sm:ml-16 w-auto sm:w-[calc(100%-4rem)] text-left group/memo"
                      >
                        <div className="flex items-start gap-2.5 px-4 py-3 rounded-xl bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-100/80 hover:border-amber-200 hover:shadow-sm transition-all">
                          <svg className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                          </svg>
                          <span className="text-sm text-amber-800 group-hover/memo:text-amber-900 transition-colors">{project.memo}</span>
                          <svg className="w-3 h-3 text-amber-300 mt-0.5 flex-shrink-0 opacity-0 group-hover/memo:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </div>
                      </button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        ) : projects && projects.length > 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-200/80 shadow-sm">
            <svg className="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-gray-500 text-sm mb-2">フィルター条件に一致するプロジェクトがありません</p>
            <button
              onClick={function() { setFilter('all') }}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium transition-colors"
            >
              フィルターをリセット
            </button>
          </div>
        ) : (
          <div className="text-center py-24 bg-white rounded-2xl border-2 border-dashed border-gray-200 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50/40 via-transparent to-indigo-50/40" />
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center mx-auto mb-5">
                <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-gray-500 mb-1 font-medium">プロジェクトがありません</p>
              <p className="text-gray-400 text-sm mb-5">最初のプロジェクトを作成して収益計画を始めましょう</p>
              <Link
                href="/projects/new"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg shadow-blue-600/25 font-medium"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                最初のプロジェクトを作成
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
