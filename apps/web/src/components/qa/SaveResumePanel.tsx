'use client'

import { useState, useEffect, useRef } from 'react'

interface SaveResumePanelProps {
  projectId: string
  projectState: any
}

interface SavedSnapshot {
  id: string
  projectId: string
  name: string
  timestamp: string
  data: any
}

var STORAGE_KEY = 'plgen_saved_projects'

function getSavedSnapshots(): SavedSnapshot[] {
  try {
    var raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveSnapshot(snapshot: SavedSnapshot) {
  var list = getSavedSnapshots()
  // Keep max 20 snapshots
  list.unshift(snapshot)
  if (list.length > 20) list = list.slice(0, 20)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

function deleteSnapshot(id: string) {
  var list = getSavedSnapshots().filter(function(s) { return s.id !== id })
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

function formatDate(ts: string): string {
  var d = new Date(ts)
  return d.getFullYear() + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
}

export function SaveResumePanel({ projectId, projectState }: SaveResumePanelProps) {
  var [snapshots, setSnapshots] = useState<SavedSnapshot[]>([])
  var [saveMessage, setSaveMessage] = useState('')
  var [saveName, setSaveName] = useState('')
  var fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(function() {
    setSnapshots(getSavedSnapshots())
  }, [])

  // Save to localStorage
  function handleSave() {
    if (!projectState) return
    var name = saveName.trim() || ('プロジェクト保存 ' + formatDate(new Date().toISOString()))
    var snapshot: SavedSnapshot = {
      id: 'snap_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
      projectId: projectId,
      name: name,
      timestamp: new Date().toISOString(),
      data: projectState,
    }
    saveSnapshot(snapshot)
    setSnapshots(getSavedSnapshots())
    setSaveName('')
    setSaveMessage('保存しました')
    setTimeout(function() { setSaveMessage('') }, 2000)
  }

  // Download as JSON file
  function handleDownload() {
    if (!projectState) return
    var blob = new Blob([JSON.stringify(projectState, null, 2)], { type: 'application/json' })
    var url = URL.createObjectURL(blob)
    var a = document.createElement('a')
    a.href = url
    a.download = 'pl-model-' + projectId.slice(0, 8) + '-' + new Date().toISOString().slice(0, 10) + '.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Upload JSON file
  function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    var file = e.target.files && e.target.files[0]
    if (!file) return
    var reader = new FileReader()
    reader.onload = function(ev) {
      try {
        var data = JSON.parse(ev.target?.result as string)
        var snapshot: SavedSnapshot = {
          id: 'snap_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
          projectId: data.project?.id || projectId,
          name: (data.project?.name || (file && file.name) || 'import') + ' (インポート)',
          timestamp: new Date().toISOString(),
          data: data,
        }
        saveSnapshot(snapshot)
        setSnapshots(getSavedSnapshots())
        setSaveMessage('インポートしました')
        setTimeout(function() { setSaveMessage('') }, 2000)
      } catch {
        setSaveMessage('ファイルの読み込みに失敗しました')
        setTimeout(function() { setSaveMessage('') }, 3000)
      }
    }
    reader.readAsText(file)
    // Reset input
    e.target.value = ''
  }

  function handleDelete(id: string) {
    deleteSnapshot(id)
    setSnapshots(getSavedSnapshots())
  }

  // Download a specific snapshot
  function handleSnapshotDownload(snapshot: SavedSnapshot) {
    var blob = new Blob([JSON.stringify(snapshot.data, null, 2)], { type: 'application/json' })
    var url = URL.createObjectURL(blob)
    var a = document.createElement('a')
    a.href = url
    a.download = 'pl-model-' + snapshot.name.slice(0, 20) + '.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  var projectSnapshots = snapshots.filter(function(s) { return s.projectId === projectId })
  var otherSnapshots = snapshots.filter(function(s) { return s.projectId !== projectId })

  return (
    <div className="bg-white rounded-3xl shadow-warm overflow-hidden">
      <div className="px-6 py-4 border-b border-cream-200 bg-cream-100">
        <h3 className="font-semibold text-dark-900">保存・再開</h3>
        <p className="text-xs text-sand-500 mt-0.5">モデルとPLデータを保存し、後から再開できます</p>
      </div>

      <div className="p-6 space-y-5">
        {/* Save Section */}
        <div className="flex gap-3">
          <input
            type="text"
            value={saveName}
            onChange={function(e) { setSaveName(e.target.value) }}
            placeholder="保存名を入力（オプション）"
            className="flex-1 text-sm border border-cream-200 rounded-2xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-transparent"
          />
          <button
            onClick={handleSave}
            disabled={!projectState}
            className="px-4 py-2 rounded-2xl text-sm font-medium text-white bg-dark-900 hover:bg-dark-800 disabled:opacity-50 transition-colors"
          >
            保存
          </button>
        </div>

        {saveMessage && (
          <div className={'text-xs px-3 py-2 rounded-lg ' + (
            saveMessage.includes('失敗') ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'
          )}>
            {saveMessage}
          </div>
        )}

        {/* Export/Import Actions */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={handleDownload}
            disabled={!projectState}
            className="flex items-center justify-center gap-2 py-2.5 rounded-2xl border-2 border-cream-200 text-sm font-medium text-sand-600 hover:bg-cream-50 hover:border-cream-300 disabled:opacity-50 transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            JSONダウンロード
          </button>
          <button
            onClick={function() { fileInputRef.current && fileInputRef.current.click() }}
            className="flex items-center justify-center gap-2 py-2.5 rounded-2xl border-2 border-cream-200 text-sm font-medium text-sand-600 hover:bg-cream-50 hover:border-cream-300 transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l4 4m0 0l4-4m-4 4V4" />
            </svg>
            JSONインポート
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleUpload}
            className="hidden"
          />
        </div>

        {/* Google Drive Note */}
        <div className="px-4 py-3 rounded-2xl bg-cream-100 border border-cream-200">
          <div className="flex items-center gap-2 mb-1">
            <svg className="w-4 h-4 text-sand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs font-medium text-sand-500">Google Drive 連携</span>
          </div>
          <p className="text-xs text-sand-400">
            JSONファイルをダウンロードし、Google Driveに手動保存することで
            クラウドバックアップが可能です。再開時はファイルをインポートしてください。
          </p>
        </div>

        {/* Saved Snapshots */}
        {projectSnapshots.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-dark-900 mb-2">このプロジェクトの保存データ</h4>
            <div className="space-y-2">
              {projectSnapshots.map(function(snap) {
                return (
                  <div key={snap.id} className="flex items-center gap-3 px-4 py-2.5 rounded-2xl border border-cream-200 bg-cream-50 hover:bg-cream-100 transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-dark-900 truncate">{snap.name}</div>
                      <div className="text-xs text-sand-400">{formatDate(snap.timestamp)}</div>
                    </div>
                    <button
                      onClick={function() { handleSnapshotDownload(snap) }}
                      className="text-xs px-2.5 py-1 rounded border border-cream-200 text-sand-600 hover:bg-white transition-colors"
                    >
                      DL
                    </button>
                    <button
                      onClick={function() { handleDelete(snap.id) }}
                      className="text-xs px-2.5 py-1 rounded border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                    >
                      削除
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {otherSnapshots.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-sand-600 mb-2">その他の保存データ</h4>
            <div className="space-y-2">
              {otherSnapshots.slice(0, 5).map(function(snap) {
                return (
                  <div key={snap.id} className="flex items-center gap-3 px-4 py-2.5 rounded-2xl border border-cream-200 hover:bg-cream-50 transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-sand-600 truncate">{snap.name}</div>
                      <div className="text-xs text-sand-400">{formatDate(snap.timestamp)}</div>
                    </div>
                    <button
                      onClick={function() { handleSnapshotDownload(snap) }}
                      className="text-xs px-2.5 py-1 rounded border border-cream-200 text-sand-600 hover:bg-white transition-colors"
                    >
                      DL
                    </button>
                    <button
                      onClick={function() { handleDelete(snap.id) }}
                      className="text-xs px-2.5 py-1 rounded border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                    >
                      削除
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
