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

var STATUS_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  created: { label: '作成済み', bg: 'bg-gray-100', text: 'text-gray-600' },
  active: { label: '進行中', bg: 'bg-blue-100', text: 'text-blue-700' },
  completed: { label: '完了', bg: 'bg-emerald-100', text: 'text-emerald-700' },
  archived: { label: 'アーカイブ', bg: 'bg-amber-100', text: 'text-amber-700' },
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

  // Filter and sort projects
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
      <div className="flex items-center justify-between mb-8 gap-3">
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">プロジェクト管理</h1>
          <p className="text-gray-500 mt-1 text-sm hidden sm:block">収益計画プロジェクトを管理・閲覧</p>
        </div>
        <Link
          href="/projects/new"
          className="flex items-center gap-2 bg-blue-600 text-white px-4 sm:px-5 py-3 rounded-xl hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md font-medium min-h-[44px] flex-shrink-0"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span className="hidden sm:inline">新規プロジェクト</span>
          <span className="sm:hidden">新規</span>
        </Link>
      </div>

      {/* Status Summary Cards */}
      {projects && projects.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <button
            onClick={function() { setFilter('all') }}
            className={'rounded-xl p-4 border-2 transition-all text-left ' + (
              filter === 'all'
                ? 'border-gray-900 bg-gray-50 shadow-sm'
                : 'border-gray-200 bg-white hover:border-gray-300'
            )}
          >
            <div className="text-2xl font-bold text-gray-900">{projects.length}</div>
            <div className="text-xs text-gray-500 mt-1">全プロジェクト</div>
          </button>
          {Object.keys(STATUS_CONFIG).map(function(status) {
            var config = STATUS_CONFIG[status]
            var count = statusCounts[status] || 0
            if (count === 0 && status !== 'active') return null
            return (
              <button
                key={status}
                onClick={function() { setFilter(filter === status ? 'all' : status) }}
                className={'rounded-xl p-4 border-2 transition-all text-left ' + (
                  filter === status
                    ? 'border-gray-900 bg-gray-50 shadow-sm'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                )}
              >
                <div className="text-2xl font-bold text-gray-900">{count}</div>
                <div className={'text-xs mt-1 ' + config.text}>{config.label}</div>
              </button>
            )
          })}
        </div>
      )}

      {/* Sort Controls */}
      {projects && projects.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs text-gray-400">並び替え:</span>
          {[
            { key: 'date' as const, label: '作成日' },
            { key: 'name' as const, label: '名前' },
            { key: 'phase' as const, label: 'フェーズ' },
          ].map(function(opt) {
            return (
              <button
                key={opt.key}
                onClick={function() { setSortBy(opt.key) }}
                className={'text-xs px-3 py-1.5 rounded-lg transition-all ' + (
                  sortBy === opt.key
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
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
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-gray-500 text-sm">読み込み中...</p>
          </div>
        </div>
      ) : sortedProjects.length > 0 ? (
        <div className="space-y-4">
          {sortedProjects.map(function(project: any) {
            var statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.created
            var phaseLabel = PHASE_LABELS[project.current_phase] || ('Phase ' + project.current_phase)
            var phaseProgress = Math.round((project.current_phase / 8) * 100)
            var isEditingThisMemo = editingMemo === project.id
            var isDeleting = deletingId === project.id

            return (
              <div
                key={project.id}
                className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-all"
              >
                <div className="p-4 sm:p-5">
                  {/* Top Row: Name, Status, Actions */}
                  <div className="flex items-start gap-3 sm:gap-4">
                    {/* Project Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 sm:gap-3 mb-1 flex-wrap">
                        <Link
                          href={getPhaseRoute(project.id, project.current_phase)}
                          className="text-base sm:text-lg font-semibold text-gray-900 hover:text-blue-600 transition-colors truncate"
                        >
                          {project.name}
                        </Link>
                        <span className={'flex-shrink-0 text-xs px-2.5 py-0.5 rounded-full font-medium ' + statusConfig.bg + ' ' + statusConfig.text}>
                          {statusConfig.label}
                        </span>
                      </div>

                      {/* Meta Info */}
                      <div className="flex items-center gap-2 sm:gap-4 text-xs text-gray-400 flex-wrap">
                        <span>作成: {formatDate(project.created_at)}</span>
                        <span className="hidden sm:inline">更新: {formatDateTime(project.updated_at)}</span>
                        <span className="hidden sm:inline text-gray-300">{project.template_id}</span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Link
                        href={getPhaseRoute(project.id, project.current_phase)}
                        className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 transition-colors min-h-[44px]"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        <span className="hidden sm:inline">続ける</span>
                      </Link>
                      <button
                        onClick={function() { handleStartEditMemo(project.id, project.memo || '') }}
                        className="p-2.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                        title="メモを編集"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {!isDeleting ? (
                        <button
                          onClick={function() { setDeletingId(project.id) }}
                          className="p-2.5 rounded-lg border border-gray-200 text-gray-400 hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                          title="削除"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      ) : (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={function() { deleteMutation.mutate(project.id) }}
                            disabled={deleteMutation.isPending}
                            className="px-3 py-2 rounded-lg text-xs font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 transition-colors min-h-[44px]"
                          >
                            {deleteMutation.isPending ? '削除中...' : '削除する'}
                          </button>
                          <button
                            onClick={function() { setDeletingId(null) }}
                            className="px-3 py-2 rounded-lg text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors min-h-[44px]"
                          >
                            取消
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Phase Progress */}
                  <div className="mt-4">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xs font-medium text-gray-600">
                        Phase {project.current_phase}: {phaseLabel}
                      </span>
                      <span className="text-xs text-gray-400">{phaseProgress}%</span>
                    </div>
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5, 6, 7, 8].map(function(phase) {
                        var isDone = phase < project.current_phase
                        var isCurrent = phase === project.current_phase
                        return (
                          <div
                            key={phase}
                            className={'h-1.5 flex-1 rounded-full transition-all ' + (
                              isDone
                                ? 'bg-emerald-500'
                                : isCurrent
                                  ? 'bg-blue-500'
                                  : 'bg-gray-200'
                            )}
                            title={'Phase ' + phase + ': ' + (PHASE_LABELS[phase] || '')}
                          />
                        )
                      })}
                    </div>
                    {/* Phase Labels Row - hidden on mobile, visible on sm+ */}
                    <div className="hidden sm:flex gap-1 mt-1">
                      {[1, 2, 3, 4, 5, 6, 7, 8].map(function(phase) {
                        var isCurrent = phase === project.current_phase
                        return (
                          <div key={phase} className="flex-1 text-center">
                            <span className={'text-[10px] ' + (isCurrent ? 'text-blue-600 font-medium' : 'text-gray-300')}>
                              {PHASE_LABELS[phase]}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Memo Section */}
                  {isEditingThisMemo ? (
                    <div className="mt-4 flex gap-2">
                      <input
                        type="text"
                        value={memoText}
                        onChange={function(e) { setMemoText(e.target.value) }}
                        onKeyDown={function(e) {
                          if (e.key === 'Enter') handleMemoSave(project.id)
                          if (e.key === 'Escape') setEditingMemo(null)
                        }}
                        placeholder="メモを入力（例: クライアントA社向け、第2四半期見直し）"
                        className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        autoFocus
                      />
                      <button
                        onClick={function() { handleMemoSave(project.id) }}
                        disabled={updateMutation.isPending}
                        className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
                      >
                        保存
                      </button>
                      <button
                        onClick={function() { setEditingMemo(null) }}
                        className="px-3 py-2 rounded-lg text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors"
                      >
                        取消
                      </button>
                    </div>
                  ) : project.memo ? (
                    <button
                      onClick={function() { handleStartEditMemo(project.id, project.memo || '') }}
                      className="mt-3 w-full text-left px-4 py-2.5 rounded-lg bg-amber-50 border border-amber-100 hover:bg-amber-100 transition-colors"
                    >
                      <div className="flex items-start gap-2">
                        <svg className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                        </svg>
                        <span className="text-sm text-amber-800">{project.memo}</span>
                      </div>
                    </button>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      ) : projects && projects.length > 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500">フィルター条件に一致するプロジェクトがありません</p>
          <button
            onClick={function() { setFilter('all') }}
            className="text-blue-600 hover:underline mt-2 inline-block text-sm"
          >
            フィルターをリセット
          </button>
        </div>
      ) : (
        <div className="text-center py-20 bg-white rounded-xl border-2 border-dashed border-gray-300">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500 mb-2">プロジェクトがありません</p>
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            最初のプロジェクトを作成
          </Link>
        </div>
      )}
    </div>
  )
}
