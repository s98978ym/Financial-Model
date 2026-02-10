'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'

export default function NewProjectPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [uploadMode, setUploadMode] = useState<'file' | 'text'>('file')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const createProject = useMutation({
    mutationFn: async () => {
      // 1. Create project
      const project = await api.createProject({ name: name || '新規プロジェクト' })

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
