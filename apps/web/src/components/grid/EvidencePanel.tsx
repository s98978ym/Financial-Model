'use client'

interface EvidencePanelProps {
  cell: any | null
}

export function EvidencePanel({ cell }: EvidencePanelProps) {
  if (!cell) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 h-full">
        <h3 className="font-medium text-gray-500 text-sm">エビデンス</h3>
        <p className="text-gray-400 text-sm mt-4">
          セルをクリックすると、根拠情報がここに表示されます
        </p>
      </div>
    )
  }

  const evidence = cell.evidence
  const confidence = cell.confidence
  const warnings = cell.warnings || []

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
      {/* Cell Header */}
      <div>
        <h3 className="font-medium text-gray-900 text-sm">
          {cell.sheet} / {cell.cell}
        </h3>
        <p className="text-gray-500 text-xs mt-0.5">
          {cell.label || cell.label_match || cell.assigned_concept || cell.concept || ''}
        </p>
        {cell.category && (
          <span className="inline-flex mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600">
            {cell.category}
          </span>
        )}
      </div>

      {/* Confidence */}
      <div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">確信度</span>
          <span
            className={`text-sm font-mono font-bold ${
              confidence >= 0.8
                ? 'text-green-600'
                : confidence >= 0.5
                  ? 'text-yellow-600'
                  : 'text-red-600'
            }`}
          >
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <div className="mt-1 w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${
              confidence >= 0.8
                ? 'bg-green-500'
                : confidence >= 0.5
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
            }`}
            style={{ width: `${Math.round(confidence * 100)}%` }}
          />
        </div>
      </div>

      {/* Source */}
      {cell.source && (
        <div>
          <span className="text-xs text-gray-500">ソース: </span>
          <span className={`source-badge ${
            cell.source === 'document' ? 'source-doc' :
            cell.source === 'inferred' ? 'source-infer' : 'source-default'
          }`}>
            {cell.source === 'document' ? '文書' :
             cell.source === 'inferred' ? '推定' : 'デフォルト'}
          </span>
        </div>
      )}

      {/* Evidence Quote */}
      {evidence?.quote ? (
        <div>
          <span className="text-xs text-gray-500 block mb-1">原文引用:</span>
          <blockquote className="bg-blue-50 border-l-3 border-blue-400 px-3 py-2 text-sm text-gray-700 italic">
            &ldquo;{evidence.quote}&rdquo;
          </blockquote>
          {evidence.page && (
            <p className="text-xs text-gray-400 mt-1">
              ページ {evidence.page}
            </p>
          )}
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
          <p className="text-xs text-yellow-700">
            文書に記載なし — デフォルト値または推定値を使用
          </p>
        </div>
      )}

      {/* Rationale */}
      {(evidence?.rationale || cell.reasoning) && (
        <div>
          <span className="text-xs text-gray-500 block mb-1">根拠:</span>
          <p className="text-sm text-gray-600">{evidence?.rationale || cell.reasoning}</p>
        </div>
      )}

      {/* Value (if Phase 5 extraction) */}
      {cell.value != null && (
        <div>
          <span className="text-xs text-gray-500 block mb-1">抽出値:</span>
          <p className="text-lg font-mono font-bold text-blue-700">
            {typeof cell.value === 'number' ? cell.value.toLocaleString() : cell.value}
          </p>
          {cell.original_text && (
            <p className="text-xs text-gray-400 mt-0.5">原文: {cell.original_text}</p>
          )}
        </div>
      )}

      {/* Segment info */}
      {cell.segment && (
        <div>
          <span className="text-xs text-gray-500">セグメント: </span>
          <span className="text-xs text-gray-700">{cell.segment}</span>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div>
          <span className="text-xs text-gray-500 block mb-1">警告:</span>
          <ul className="space-y-1">
            {warnings.map((w: string, i: number) => (
              <li key={i} className="text-xs text-red-600 flex items-start gap-1">
                <span className="mt-0.5">!</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
