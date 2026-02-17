'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, getAdminToken } from '@/lib/api'

export default function NewProjectPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [uploadMode, setUploadMode] = useState<'file' | 'text'>('file')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)

  // Admin-only LLM selection
  const isAdmin = !!getAdminToken()
  const [llmProvider, setLlmProvider] = useState('')
  const [llmModel, setLlmModel] = useState('')

  // Fetch LLM catalog (only for admin)
  var llmModelsQuery = useQuery({
    queryKey: ['llmModels'],
    queryFn: function() { return api.getLLMModels() },
    enabled: isAdmin,
  })

  var llmProviders: { id: string; label: string }[] = llmModelsQuery.data?.providers || []
  var llmCatalog: any[] = llmModelsQuery.data?.models || []
  var filteredModels = llmCatalog.filter(function(m: any) { return m.provider === llmProvider })

  function handleLlmProviderChange(newProvider: string) {
    setLlmProvider(newProvider)
    var models = llmCatalog.filter(function(m: any) { return m.provider === newProvider })
    var std = models.find(function(m: any) { return m.tier === 'standard' })
    setLlmModel(std ? std.model_id : (models[0]?.model_id || ''))
  }

  const createProject = useMutation({
    mutationFn: async () => {
      // 1. Create project (with optional LLM override for admin)
      var createBody: any = { name: name || '新規プロジェクト' }
      if (isAdmin && llmProvider && llmModel) {
        createBody.llm_provider = llmProvider
        createBody.llm_model = llmModel
      }
      const project = await api.createProject(createBody)

      // 2. Upload document
      let doc: any = null
      if (uploadMode === 'text' && text) {
        doc = await api.uploadDocument(project.id, { kind: 'text', text })
      } else if (uploadMode === 'file' && file) {
        doc = await api.uploadDocumentFile(project.id, file)
      }

      // 3. Run Phase 1 scan (template scan + text extraction)
      if (doc?.id) {
        await api.phase1Scan({
          project_id: project.id,
          document_id: doc.id,
          template_id: 'v2_ib_grade',
        })
      }

      return project
    },
    onSuccess: (project) => {
      router.push(`/projects/${project.id}/phase2`)
    },
  })

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
      setUploadMode('file')
    }
  }, [])

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-dark-900">新規プロジェクト</h1>
        <p className="text-sand-500 mt-1 text-sm">事業計画書をアップロードして収益モデルを生成</p>
      </div>

      {/* Project Name */}
      <div className="bg-white rounded-3xl shadow-warm p-6 mb-4">
        <label className="block text-sm font-semibold text-dark-900 mb-2">
          プロジェクト名
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例: SaaS事業計画 2026"
          className="w-full bg-cream-100 border-0 rounded-2xl px-4 py-3 text-dark-900 placeholder:text-sand-300 focus:outline-none focus:ring-2 focus:ring-gold-400/30 transition-all"
        />
      </div>

      {/* LLM Selection (Admin Only) */}
      {isAdmin && llmModelsQuery.data && (
        <div className="bg-white rounded-3xl shadow-warm p-6 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-xl bg-cream-200 flex items-center justify-center">
              <svg className="w-4 h-4 text-gold-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-dark-900">LLM設定</span>
            <span className="text-[10px] bg-gold-500/10 text-gold-600 px-2 py-0.5 rounded-full font-medium">管理者</span>
          </div>
          <p className="text-xs text-sand-400 mb-4">
            このプロジェクトで使用するLLMを選択（未選択の場合はシステムデフォルトを使用）
          </p>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-sand-500 mb-1">プロバイダー</label>
              <select
                value={llmProvider}
                onChange={function(e) { handleLlmProviderChange(e.target.value) }}
                className="w-full text-sm bg-cream-100 border-0 rounded-xl px-3 py-2.5 text-dark-900 focus:outline-none focus:ring-2 focus:ring-gold-400/30"
              >
                <option value="">デフォルト</option>
                {llmProviders.map(function(p) {
                  return <option key={p.id} value={p.id}>{p.label}</option>
                })}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-sand-500 mb-1">モデル</label>
              <select
                value={llmModel}
                onChange={function(e) { setLlmModel(e.target.value) }}
                disabled={!llmProvider}
                className="w-full text-sm bg-cream-100 border-0 rounded-xl px-3 py-2.5 text-dark-900 focus:outline-none focus:ring-2 focus:ring-gold-400/30 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="">選択してください</option>
                {filteredModels.map(function(m: any) {
                  var tierBadge = m.tier === 'premium' ? ' [Premium]' : m.tier === 'fast' ? ' [Fast]' : ''
                  return <option key={m.model_id} value={m.model_id}>{m.label}{tierBadge}</option>
                })}
              </select>
            </div>
          </div>
          {llmProvider && llmModel && (
            <p className="text-[10px] text-sand-400 mt-2">
              {(function() {
                var m = llmCatalog.find(function(x: any) { return x.model_id === llmModel })
                return m ? m.description : ''
              })()}
            </p>
          )}
        </div>
      )}

      {/* Upload Section */}
      <div className="bg-white rounded-3xl shadow-warm p-6 mb-4">
        {/* Mode Tabs */}
        <div className="flex gap-2 mb-5">
          <button
            onClick={() => setUploadMode('file')}
            className={'px-4 py-2 text-sm font-medium rounded-full transition-all ' + (
              uploadMode === 'file'
                ? 'bg-dark-900 text-white shadow-warm-sm'
                : 'bg-cream-100 text-sand-500 hover:bg-cream-200'
            )}
          >
            ファイルアップロード
          </button>
          <button
            onClick={() => setUploadMode('text')}
            className={'px-4 py-2 text-sm font-medium rounded-full transition-all ' + (
              uploadMode === 'text'
                ? 'bg-dark-900 text-white shadow-warm-sm'
                : 'bg-cream-100 text-sand-500 hover:bg-cream-200'
            )}
          >
            テキスト貼り付け
          </button>
        </div>

        {/* File Upload */}
        {uploadMode === 'file' && (
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            className={'rounded-3xl p-12 text-center transition-all border-2 border-dashed ' + (
              dragOver
                ? 'border-gold-400 bg-gold-50'
                : file
                  ? 'border-emerald-300 bg-emerald-50'
                  : 'border-cream-400 bg-cream-50 hover:border-sand-300'
            )}
          >
            {file ? (
              <div>
                <div className="w-12 h-12 rounded-2xl bg-emerald-100 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-dark-900 font-medium">{file.name}</p>
                <p className="text-sm text-sand-400 mt-1">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </p>
                <button
                  onClick={() => setFile(null)}
                  className="text-sm text-red-400 hover:text-red-500 mt-3 font-medium transition-colors"
                >
                  ファイルを変更
                </button>
              </div>
            ) : (
              <div>
                <div className="w-12 h-12 rounded-2xl bg-cream-200 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-sand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <p className="text-sand-500">
                  PDF / DOCX / PPTX ファイルをドラッグ&ドロップ
                </p>
                <p className="text-sm text-sand-300 mt-1">または</p>
                <label className="inline-block mt-2 cursor-pointer text-gold-600 hover:text-gold-500 font-medium transition-colors">
                  ファイルを選択
                  <input
                    type="file"
                    accept=".pdf,.docx,.pptx"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </label>
              </div>
            )}
          </div>
        )}

        {/* Text Paste */}
        {uploadMode === 'text' && (
          <div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="事業計画書のテキストを貼り付けてください（NotebookLM等からのコピー対応）"
              rows={12}
              className="w-full bg-cream-50 border-0 rounded-2xl px-4 py-3 text-dark-900 placeholder:text-sand-300 focus:outline-none focus:ring-2 focus:ring-gold-400/30 font-mono text-sm transition-all"
            />
            <p className="text-xs text-sand-400 mt-2">
              {text.length.toLocaleString()} 文字
            </p>
          </div>
        )}
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3 mt-6">
        <button
          onClick={() => router.push('/')}
          className="px-5 py-3 text-sand-500 hover:text-dark-900 rounded-2xl hover:bg-white transition-all font-medium"
        >
          キャンセル
        </button>
        <button
          onClick={() => createProject.mutate()}
          disabled={createProject.isPending || (!file && !text)}
          className="bg-dark-900 text-white px-6 py-3 rounded-2xl hover:bg-dark-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-warm-md hover:shadow-warm-lg font-medium"
        >
          {createProject.isPending ? (
            <span className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              作成中...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              プロジェクトを作成
              <svg className="w-4 h-4 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </span>
          )}
        </button>
      </div>

      {createProject.isError && (
        <div className="mt-4 bg-red-50 rounded-2xl p-4">
          <p className="text-red-600 text-sm">
            エラーが発生しました: {(createProject.error as Error).message}
          </p>
        </div>
      )}
    </div>
  )
}
