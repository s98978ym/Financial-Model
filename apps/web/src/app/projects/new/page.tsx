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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">新規プロジェクト</h1>

      {/* Project Name */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          プロジェクト名
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例: SaaS事業計画 2026"
          className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* LLM Selection (Admin Only) */}
      {isAdmin && llmModelsQuery.data && (
        <div className="mb-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-sm font-medium text-purple-700">LLM設定</span>
            <span className="text-[10px] bg-purple-200 text-purple-700 px-1.5 py-0.5 rounded-full">管理者</span>
          </div>
          <p className="text-xs text-purple-600 mb-3">
            このプロジェクトで使用するLLMを選択（未選択の場合はシステムデフォルトを使用）
          </p>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-purple-700 mb-1">プロバイダー</label>
              <select
                value={llmProvider}
                onChange={function(e) { handleLlmProviderChange(e.target.value) }}
                className="w-full text-sm border border-purple-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 bg-white"
              >
                <option value="">デフォルト</option>
                {llmProviders.map(function(p) {
                  return <option key={p.id} value={p.id}>{p.label}</option>
                })}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-purple-700 mb-1">モデル</label>
              <select
                value={llmModel}
                onChange={function(e) { setLlmModel(e.target.value) }}
                disabled={!llmProvider}
                className="w-full text-sm border border-purple-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-400 bg-white disabled:opacity-50 disabled:cursor-not-allowed"
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
            <p className="text-[10px] text-purple-500 mt-2">
              {(function() {
                var m = llmCatalog.find(function(x: any) { return x.model_id === llmModel })
                return m ? m.description : ''
              })()}
            </p>
          )}
        </div>
      )}

      {/* Upload Mode Tabs */}
      <div className="mb-4">
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setUploadMode('file')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              uploadMode === 'file'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            ファイルアップロード
          </button>
          <button
            onClick={() => setUploadMode('text')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              uploadMode === 'text'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            テキスト貼り付け
          </button>
        </div>
      </div>

      {/* File Upload */}
      {uploadMode === 'file' && (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragOver
              ? 'border-blue-400 bg-blue-50'
              : file
                ? 'border-green-400 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          {file ? (
            <div>
              <p className="text-green-700 font-medium">{file.name}</p>
              <p className="text-sm text-gray-500 mt-1">
                {(file.size / 1024 / 1024).toFixed(1)} MB
              </p>
              <button
                onClick={() => setFile(null)}
                className="text-sm text-red-500 hover:underline mt-2"
              >
                ファイルを変更
              </button>
            </div>
          ) : (
            <div>
              <p className="text-gray-500">
                PDF / DOCX / PPTX ファイルをドラッグ&ドロップ
              </p>
              <p className="text-sm text-gray-400 mt-1">または</p>
              <label className="inline-block mt-2 cursor-pointer text-blue-600 hover:underline">
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
            className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          />
          <p className="text-xs text-gray-400 mt-1">
            {text.length.toLocaleString()} 文字
          </p>
        </div>
      )}

      {/* Submit */}
      <div className="mt-8 flex justify-end gap-3">
        <button
          onClick={() => router.push('/')}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          キャンセル
        </button>
        <button
          onClick={() => createProject.mutate()}
          disabled={createProject.isPending || (!file && !text)}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {createProject.isPending ? '作成中...' : 'プロジェクトを作成して分析開始'}
        </button>
      </div>

      {createProject.isError && (
        <p className="text-red-500 text-sm mt-4">
          エラーが発生しました: {(createProject.error as Error).message}
        </p>
      )}
    </div>
  )
}
