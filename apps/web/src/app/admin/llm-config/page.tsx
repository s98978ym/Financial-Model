'use client'

import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, setAdminToken } from '@/lib/api'
import Link from 'next/link'

// -------------------------------------------------------------------
// Types
// -------------------------------------------------------------------
interface PhaseInfo {
  phase: number
  label: string
  description: string
  icon: string
  prompts: string[]
  model: string
  temperature: number
  max_tokens: number
}

interface PromptInfo {
  key: string
  display_name: string
  description: string
  phase: number
  prompt_type: string
  default_content: string
  current_content: string
  is_customized: boolean
  active_version_id: string | null
  scope: string
}

interface PromptVersion {
  id: string
  prompt_key: string
  project_id: string | null
  content: string
  label: string
  author: string
  is_active: boolean
  created_at: string
}

var PHASE_ICONS: Record<string, string> = {
  search: '\uD83D\uDD0D',
  map: '\uD83D\uDDFA\uFE0F',
  cube: '\uD83C\uDFD7\uFE0F',
  download: '\uD83D\uDCCA',
}

export default function AdminLLMConfigPage() {
  var queryClient = useQueryClient()

  // Auth state
  var [isAuthed, setIsAuthed] = useState(false)
  var [isCheckingAuth, setIsCheckingAuth] = useState(true)
  var [loginId, setLoginId] = useState('')
  var [loginPw, setLoginPw] = useState('')
  var [loginError, setLoginError] = useState('')
  var [isLoggingIn, setIsLoggingIn] = useState(false)

  // Check in-memory token on mount (no sessionStorage — avoids XSS exposure)
  useEffect(function() {
    var existing = require('@/lib/api').getAdminToken()
    if (existing) {
      setAdminToken(existing)
      api.verifyAdminToken().then(function() {
        setIsAuthed(true)
        setIsCheckingAuth(false)
      }).catch(function() {
        setAdminToken(null)
        setIsCheckingAuth(false)
      })
    } else {
      setIsCheckingAuth(false)
    }
  }, [])

  function handleLogin(e?: React.FormEvent) {
    if (e) e.preventDefault()
    setIsLoggingIn(true)
    setLoginError('')
    api.adminAuth(loginId, loginPw).then(function(res: any) {
      setAdminToken(res.token)
      setIsAuthed(true)
      setIsLoggingIn(false)
    }).catch(function() {
      setLoginError('IDまたはパスワードが正しくありません')
      setIsLoggingIn(false)
    })
  }

  var [selectedPromptKey, setSelectedPromptKey] = useState<string | null>(null)
  var [editContent, setEditContent] = useState('')
  var [editLabel, setEditLabel] = useState('')
  var [isEditing, setIsEditing] = useState(false)
  var [showVersions, setShowVersions] = useState(false)
  var [toast, setToast] = useState<{type: 'success' | 'error', text: string} | null>(null)
  var textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-dismiss toast
  useEffect(function() {
    if (toast) {
      var t = setTimeout(function() { setToast(null) }, 4000)
      return function() { clearTimeout(t) }
    }
  }, [toast])

  var phasesQuery = useQuery({
    queryKey: ['promptPhases'],
    queryFn: function() { return api.getPromptPhases() },
    enabled: isAuthed,
    retry: 2,
    retryDelay: 1000,
  })

  var promptsQuery = useQuery({
    queryKey: ['prompts', null],
    queryFn: function() { return api.listPrompts() },
    enabled: isAuthed,
    retry: 2,
    retryDelay: 1000,
  })

  var promptDetailQuery = useQuery({
    queryKey: ['promptDetail', selectedPromptKey, null],
    queryFn: function() { return api.getPrompt(selectedPromptKey!) },
    enabled: isAuthed && !!selectedPromptKey,
    retry: 2,
    retryDelay: 1000,
  })

  var phases: PhaseInfo[] = phasesQuery.data || []
  var prompts: PromptInfo[] = promptsQuery.data || []
  var promptDetail = promptDetailQuery.data as (PromptInfo & { versions: PromptVersion[] }) | undefined

  useEffect(function() {
    if (promptDetail) {
      setEditContent(promptDetail.current_content)
      setIsEditing(false)
      setShowVersions(false)
    }
  }, [promptDetail])

  useEffect(function() {
    if (textareaRef.current && isEditing) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [editContent, isEditing])

  var saveMutation = useMutation({
    mutationFn: function() {
      return api.updatePrompt(selectedPromptKey!, {
        content: editContent,
        label: editLabel,
      })
    },
    onSuccess: function() {
      queryClient.invalidateQueries({ queryKey: ['prompts'] })
      queryClient.invalidateQueries({ queryKey: ['promptDetail', selectedPromptKey] })
      setIsEditing(false)
      setEditLabel('')
      setToast({type: 'success', text: '保存しました'})
    },
    onError: function(err: any) {
      setToast({type: 'error', text: '保存に失敗: ' + (err.message || String(err))})
    },
  })

  var resetMutation = useMutation({
    mutationFn: function() {
      return api.resetPrompt(selectedPromptKey!)
    },
    onSuccess: function() {
      queryClient.invalidateQueries({ queryKey: ['prompts'] })
      queryClient.invalidateQueries({ queryKey: ['promptDetail', selectedPromptKey] })
      setToast({type: 'success', text: 'デフォルトに戻しました'})
    },
    onError: function(err: any) {
      setToast({type: 'error', text: 'リセットに失敗: ' + (err.message || String(err))})
    },
  })

  var activateVersionMutation = useMutation({
    mutationFn: function(versionId: string) {
      return api.activatePromptVersion(selectedPromptKey!, versionId)
    },
    onSuccess: function() {
      queryClient.invalidateQueries({ queryKey: ['prompts'] })
      queryClient.invalidateQueries({ queryKey: ['promptDetail', selectedPromptKey] })
      setShowVersions(false)
      setToast({type: 'success', text: 'バージョンを適用しました'})
    },
    onError: function(err: any) {
      setToast({type: 'error', text: 'バージョン適用に失敗: ' + (err.message || String(err))})
    },
  })

  var promptsByPhase: Record<number, PromptInfo[]> = {}
  prompts.forEach(function(p) {
    if (!promptsByPhase[p.phase]) promptsByPhase[p.phase] = []
    promptsByPhase[p.phase].push(p)
  })

  // Build ordered phase list for rendering prompt list.
  // Use phases from API if available, otherwise derive from prompts data.
  var phaseOrder: number[] = []
  if (phases.length > 0) {
    phases.forEach(function(ph) { phaseOrder.push(ph.phase) })
  } else {
    // Fallback: derive phase numbers from prompts
    var seen: Record<number, boolean> = {}
    prompts.forEach(function(p) {
      if (!seen[p.phase]) {
        seen[p.phase] = true
        phaseOrder.push(p.phase)
      }
    })
    phaseOrder.sort()
  }

  // Map phase numbers to labels (from API phases or fallback)
  var phaseLabels: Record<number, string> = {}
  phases.forEach(function(ph) { phaseLabels[ph.phase] = ph.label })
  // Fallback labels if phases API unavailable
  if (!phaseLabels[2]) phaseLabels[2] = 'BM分析'
  if (!phaseLabels[3]) phaseLabels[3] = 'テンプレマップ'
  if (!phaseLabels[4]) phaseLabels[4] = 'モデル設計'
  if (!phaseLabels[5]) phaseLabels[5] = 'パラメータ抽出'

  var selectedPrompt = prompts.find(function(p) { return p.key === selectedPromptKey })

  // Data loading state — only block on promptsQuery (phases is supplementary)
  var isDataLoading = promptsQuery.isLoading
  var dataError = promptsQuery.error

  // Loading auth check
  if (isCheckingAuth) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-3" />
          <p className="text-sm text-gray-400">認証確認中...</p>
        </div>
      </div>
    )
  }

  // Login form
  if (!isAuthed) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-full max-w-sm">
          <form onSubmit={handleLogin} className="bg-white rounded-2xl border border-gray-200 shadow-lg p-8">
            <div className="text-center mb-6">
              <div className="w-14 h-14 rounded-2xl bg-purple-100 flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h2 className="text-lg font-bold text-gray-900">管理者ログイン</h2>
              <p className="text-xs text-gray-400 mt-1">LLM設定管理へのアクセスには管理者認証が必要です</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">管理者ID</label>
                <input
                  type="text"
                  value={loginId}
                  onChange={function(e) { setLoginId(e.target.value) }}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-100 focus:border-purple-400 transition-colors"
                  placeholder="ID を入力"
                  autoFocus
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">パスワード</label>
                <input
                  type="password"
                  value={loginPw}
                  onChange={function(e) { setLoginPw(e.target.value) }}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-100 focus:border-purple-400 transition-colors"
                  placeholder="パスワードを入力"
                  autoComplete="current-password"
                />
              </div>

              {loginError && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                  <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span className="text-xs text-red-600">{loginError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoggingIn || !loginId || !loginPw}
                className="w-full bg-purple-600 text-white text-sm font-medium py-2.5 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoggingIn ? 'ログイン中...' : 'ログイン'}
              </button>
            </div>

            <div className="mt-5 text-center">
              <Link href="/" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
                ダッシュボードへ戻る
              </Link>
            </div>
          </form>
        </div>
      </div>
    )
  }

  // Data loading after auth
  if (isDataLoading) {
    return (
      <div className="max-w-[1200px] mx-auto">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900">LLM設定管理</h1>
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">管理者専用</span>
          </div>
        </div>
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="text-center">
            <div className="inline-block w-8 h-8 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-3" />
            <p className="text-sm text-gray-500">プロンプトデータを読み込み中...</p>
            <p className="text-xs text-gray-400 mt-1">バックエンドからフェーズ・プロンプト情報を取得しています</p>
          </div>
        </div>
      </div>
    )
  }

  // Data error after auth
  if (dataError) {
    return (
      <div className="max-w-[1200px] mx-auto">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900">LLM設定管理</h1>
          </div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <svg className="w-10 h-10 text-red-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <h3 className="text-sm font-semibold text-red-700 mb-1">データ取得エラー</h3>
          <p className="text-xs text-red-600 mb-4">
            {String((dataError as any)?.message || dataError)}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={function() {
                phasesQuery.refetch()
                promptsQuery.refetch()
              }}
              className="text-xs bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 font-medium"
            >
              再読み込み
            </button>
            <button
              onClick={function() {
                setAdminToken(null)
                setIsAuthed(false)
              }}
              className="text-xs text-red-600 px-4 py-2 rounded-lg border border-red-300 hover:bg-red-100"
            >
              再ログイン
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-[1200px] mx-auto">
      {/* Toast notification */}
      {toast && (
        <div className={'fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ' + (
          toast.type === 'success'
            ? 'bg-green-600 text-white'
            : 'bg-red-600 text-white'
        )}>
          {toast.text}
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900">LLM設定管理</h1>
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">管理者専用</span>
          </div>
          <p className="text-sm text-gray-500 ml-11">各フェーズのLLMプロンプトを管理・カスタマイズ（グローバル設定）</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={function() {
              setAdminToken(null)
              setIsAuthed(false)
            }}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            title="ログアウト"
          >
            ログアウト
          </button>
          <Link href="/" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
            ダッシュボードへ戻る
          </Link>
        </div>
      </div>

      {/* Pipeline Visualization */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">LLM使用パイプライン</h2>
        {phases.length === 0 ? (
          <p className="text-xs text-gray-400 py-4 text-center">フェーズ情報がありません</p>
        ) : (
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {phases.map(function(phase, idx) {
              var phasePrompts = promptsByPhase[phase.phase] || []
              var hasCustom = phasePrompts.some(function(p) { return p.is_customized })
              var isSelected = selectedPrompt && selectedPrompt.phase === phase.phase
              return (
                <div key={phase.phase} className="flex items-center flex-shrink-0">
                  <button
                    onClick={function() {
                      var first = phasePrompts[0]
                      if (first) setSelectedPromptKey(first.key)
                    }}
                    className={'relative flex flex-col items-center gap-1.5 px-4 py-3 rounded-xl border-2 transition-all min-w-[130px] ' + (
                      isSelected
                        ? 'border-purple-500 bg-purple-50 shadow-md shadow-purple-100'
                        : hasCustom
                          ? 'border-amber-300 bg-amber-50 hover:border-amber-400'
                          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                    )}
                  >
                    <span className="text-lg">{PHASE_ICONS[phase.icon] || ''}</span>
                    <span className={'text-xs font-semibold ' + (isSelected ? 'text-purple-700' : 'text-gray-700')}>
                      Phase {phase.phase}
                    </span>
                    <span className={'text-[10px] ' + (isSelected ? 'text-purple-600' : 'text-gray-500')}>
                      {phase.label}
                    </span>
                    {hasCustom && (
                      <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-amber-400 rounded-full flex items-center justify-center">
                        <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </span>
                    )}
                    <div className="flex gap-1 mt-1">
                      {phasePrompts.map(function(p) {
                        return (
                          <span
                            key={p.key}
                            className={'w-1.5 h-1.5 rounded-full ' + (
                              p.is_customized ? 'bg-amber-400' : 'bg-gray-300'
                            )}
                          />
                        )
                      })}
                    </div>
                  </button>
                  {idx < phases.length - 1 && (
                    <div className="flex flex-col items-center mx-1">
                      <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
        {phases[0] && (
          <div className="mt-3 flex items-center gap-4 text-[10px] text-gray-400 border-t border-gray-100 pt-3">
            <span>Model: <strong className="text-gray-600">{phases[0].model}</strong></span>
            <span>Temperature: <strong className="text-gray-600">{phases[0].temperature}</strong></span>
            <span>Max Tokens: <strong className="text-gray-600">{phases[0].max_tokens.toLocaleString()}</strong></span>
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left: Prompt Selector */}
        <div className="col-span-4">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-700">プロンプト一覧</h3>
              <p className="text-[10px] text-gray-400 mt-0.5">{prompts.length} 件のプロンプト</p>
            </div>
            {prompts.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-xs text-gray-400">プロンプトが見つかりません</p>
                <button
                  onClick={function() { promptsQuery.refetch() }}
                  className="mt-2 text-xs text-purple-600 hover:underline"
                >
                  再読み込み
                </button>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 max-h-[calc(100vh-380px)] overflow-y-auto">
                {phaseOrder.map(function(phaseNum) {
                  var phasePrompts = promptsByPhase[phaseNum] || []
                  if (phasePrompts.length === 0) return null
                  return (
                    <div key={phaseNum}>
                      <div className="px-4 py-2 bg-gray-50 sticky top-0 z-10">
                        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                          Phase {phaseNum} — {phaseLabels[phaseNum] || 'Phase ' + phaseNum}
                        </span>
                      </div>
                      {phasePrompts.map(function(p) {
                        var isSelected = selectedPromptKey === p.key
                        return (
                          <button
                            key={p.key}
                            onClick={function() { setSelectedPromptKey(p.key) }}
                            className={'w-full text-left px-4 py-2.5 transition-colors flex items-center gap-2 ' + (
                              isSelected
                                ? 'bg-purple-50 border-l-2 border-purple-500'
                                : 'hover:bg-gray-50 border-l-2 border-transparent'
                            )}
                          >
                            <div className={'w-5 h-5 rounded flex items-center justify-center text-[10px] flex-shrink-0 ' + (
                              p.prompt_type === 'system'
                                ? 'bg-blue-100 text-blue-600'
                                : 'bg-green-100 text-green-600'
                            )}>
                              {p.prompt_type === 'system' ? 'S' : 'U'}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="text-xs font-medium text-gray-800 truncate">{p.display_name}</div>
                              <div className="text-[10px] text-gray-400 truncate">{p.description}</div>
                            </div>
                            {p.is_customized && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 bg-amber-100 text-amber-600">
                                G
                              </span>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Prompt Editor */}
        <div className="col-span-8">
          {!selectedPromptKey && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <div className="text-3xl mb-3 opacity-30">&#x2190;</div>
              <p className="text-sm text-gray-400">左のリストからプロンプトを選択してください</p>
            </div>
          )}

          {selectedPromptKey && promptDetailQuery.isLoading && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <div className="inline-block w-6 h-6 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-3" />
              <p className="text-sm text-gray-400">読み込み中...</p>
            </div>
          )}

          {selectedPromptKey && promptDetailQuery.error && (
            <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
              <p className="text-sm text-red-600 mb-3">プロンプト詳細の取得に失敗しました</p>
              <button
                onClick={function() { promptDetailQuery.refetch() }}
                className="text-xs bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
              >
                再読み込み
              </button>
            </div>
          )}

          {selectedPromptKey && promptDetail && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* Editor Header */}
              <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-800">{promptDetail.display_name}</h3>
                  <p className="text-[10px] text-gray-400 mt-0.5">{promptDetail.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded">Global</span>
                  {promptDetail.is_customized && (
                    <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                      カスタム中
                    </span>
                  )}
                </div>
              </div>

              {/* Content Area */}
              <div className="p-4">
                {!isEditing ? (
                  <div className="relative group">
                    <pre className="text-xs text-gray-700 bg-gray-50 rounded-lg p-4 overflow-auto max-h-[500px] whitespace-pre-wrap font-mono leading-relaxed border border-gray-100">
                      {promptDetail.current_content}
                    </pre>
                    <button
                      onClick={function() {
                        setEditContent(promptDetail!.current_content)
                        setIsEditing(true)
                      }}
                      className="absolute top-2 right-2 bg-white border border-gray-200 text-gray-600 px-3 py-1.5 rounded-lg text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-50 shadow-sm"
                    >
                      編集
                    </button>
                    <div className="mt-2 text-[10px] text-gray-400 text-right">
                      {promptDetail.current_content.length.toLocaleString()} 文字
                      {promptDetail.is_customized && (
                        <span className="ml-2 text-amber-500">
                          (デフォルトから変更済み: {(promptDetail.current_content.length - promptDetail.default_content.length).toLocaleString()} 文字差)
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div>
                    <textarea
                      ref={textareaRef}
                      value={editContent}
                      onChange={function(e) { setEditContent(e.target.value) }}
                      className="w-full text-xs text-gray-700 bg-white rounded-lg p-4 border-2 border-purple-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-100 font-mono leading-relaxed min-h-[300px] max-h-[600px] resize-y outline-none"
                      spellCheck={false}
                    />
                    <div className="mt-2 flex items-center gap-3">
                      <input
                        type="text"
                        value={editLabel}
                        onChange={function(e) { setEditLabel(e.target.value) }}
                        placeholder="バージョンラベル (例: v2 詳細化)"
                        className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-100 focus:border-purple-300"
                      />
                      <span className="text-[10px] text-gray-400">{editContent.length.toLocaleString()} 文字</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Bar */}
              <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
                <div className="flex items-center gap-2">
                  {promptDetail.is_customized && (
                    <button
                      onClick={function() {
                        if (confirm('デフォルトプロンプトに戻しますか？')) {
                          resetMutation.mutate()
                        }
                      }}
                      disabled={resetMutation.isPending}
                      className="text-xs text-red-600 hover:text-red-700 px-3 py-1.5 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      {resetMutation.isPending ? 'リセット中...' : 'デフォルトに戻す'}
                    </button>
                  )}
                  {isEditing && (
                    <button
                      onClick={function() { setEditContent(promptDetail!.default_content) }}
                      className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      デフォルト文を挿入
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={function() { setShowVersions(!showVersions) }}
                    className={'text-xs px-3 py-1.5 rounded-lg transition-colors ' + (
                      showVersions
                        ? 'bg-purple-100 text-purple-700'
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                    )}
                  >
                    履歴 ({(promptDetail as any)?.versions?.length || 0})
                  </button>
                  {isEditing ? (
                    <>
                      <button
                        onClick={function() { setIsEditing(false) }}
                        className="text-xs text-gray-500 px-3 py-1.5 rounded-lg hover:bg-gray-100"
                      >
                        キャンセル
                      </button>
                      <button
                        onClick={function() { saveMutation.mutate() }}
                        disabled={saveMutation.isPending || (!editLabel.trim() && editContent === promptDetail.current_content)}
                        className="text-xs bg-purple-600 text-white px-4 py-1.5 rounded-lg hover:bg-purple-700 disabled:opacity-50 font-medium"
                      >
                        {saveMutation.isPending ? '保存中...' : '保存'}
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={function() {
                        setEditContent(promptDetail!.current_content)
                        setIsEditing(true)
                      }}
                      className="text-xs bg-purple-600 text-white px-4 py-1.5 rounded-lg hover:bg-purple-700 font-medium"
                    >
                      編集する
                    </button>
                  )}
                </div>
              </div>

              {/* Version History */}
              {showVersions && (
                <div className="border-t border-gray-200">
                  <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                    <h4 className="text-xs font-semibold text-gray-600">バージョン履歴</h4>
                  </div>
                  <div className="max-h-[300px] overflow-y-auto divide-y divide-gray-50">
                    {/* Default */}
                    <div className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors">
                      <div className={'w-2 h-2 rounded-full flex-shrink-0 ' + (
                        !promptDetail.is_customized ? 'bg-green-500' : 'bg-gray-300'
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-gray-800">デフォルト</span>
                          <span className="text-[10px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded">built-in</span>
                          {!promptDetail.is_customized && (
                            <span className="text-[10px] text-green-600 font-medium">適用中</span>
                          )}
                        </div>
                        <p className="text-[10px] text-gray-400 mt-0.5 truncate">
                          {promptDetail.default_content.substring(0, 80)}...
                        </p>
                      </div>
                      {promptDetail.is_customized && (
                        <button
                          onClick={function() {
                            if (confirm('デフォルトプロンプトに戻しますか？')) {
                              resetMutation.mutate()
                            }
                          }}
                          className="text-[10px] text-blue-600 hover:underline flex-shrink-0"
                        >
                          適用
                        </button>
                      )}
                    </div>

                    {((promptDetail as any)?.versions || []).map(function(v: PromptVersion) {
                      return (
                        <div key={v.id} className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors">
                          <div className={'w-2 h-2 rounded-full flex-shrink-0 ' + (
                            v.is_active ? 'bg-green-500' : 'bg-gray-300'
                          )} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium text-gray-800">
                                {v.label || new Date(v.created_at).toLocaleString('ja-JP')}
                              </span>
                              <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">Global</span>
                              {v.is_active && (
                                <span className="text-[10px] text-green-600 font-medium">適用中</span>
                              )}
                            </div>
                            <p className="text-[10px] text-gray-400 mt-0.5">
                              {v.author} ・ {new Date(v.created_at).toLocaleString('ja-JP')} ・ {v.content.length.toLocaleString()}文字
                            </p>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <button
                              onClick={function() {
                                setEditContent(v.content)
                                setIsEditing(true)
                                setShowVersions(false)
                              }}
                              className="text-[10px] text-gray-500 hover:underline"
                            >
                              参照
                            </button>
                            {!v.is_active && (
                              <button
                                onClick={function() { activateVersionMutation.mutate(v.id) }}
                                disabled={activateVersionMutation.isPending}
                                className="text-[10px] text-purple-600 hover:underline disabled:opacity-50"
                              >
                                適用
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })}

                    {((promptDetail as any)?.versions || []).length === 0 && (
                      <div className="px-5 py-6 text-center">
                        <p className="text-xs text-gray-400">まだカスタムバージョンはありません</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
