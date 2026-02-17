'use client'

interface EvidencePanelProps {
  cell: any | null
}

export function EvidencePanel({ cell }: EvidencePanelProps) {
  if (!cell) {
    return (
      <div className="bg-white rounded-3xl shadow-warm p-5 h-full">
        <h3 className="font-semibold text-dark-900 text-sm">エビデンス</h3>
        <p className="text-sand-400 text-sm mt-4">
          セルをクリックすると、根拠情報がここに表示されます
        </p>
      </div>
    )
  }

  const evidence = cell.evidence
  const confidence = cell.confidence
  const warnings = cell.warnings || []

  return (
    <div className="bg-white rounded-3xl shadow-warm p-5 space-y-4">
      {/* Cell Header */}
      <div>
        <h3 className="font-semibold text-dark-900 text-sm">
          {cell.sheet} / {cell.cell}
        </h3>
        <p className="text-sand-500 text-xs mt-0.5">
          {cell.label || cell.label_match || cell.assigned_concept || cell.concept || ''}
        </p>
        {cell.category && (
          <span className="inline-flex mt-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-cream-200 text-sand-600">
            {cell.category}
          </span>
        )}
      </div>

      {/* Confidence */}
      <div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-sand-400">確信度</span>
          <span
            className={`text-sm font-mono font-bold ${
              confidence >= 0.8
                ? 'text-emerald-600'
                : confidence >= 0.5
                  ? 'text-amber-600'
                  : 'text-red-500'
            }`}
          >
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <div className="mt-1.5 w-full bg-cream-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${
              confidence >= 0.8
                ? 'bg-emerald-500'
                : confidence >= 0.5
                  ? 'bg-amber-500'
                  : 'bg-red-400'
            }`}
            style={{ width: `${Math.round(confidence * 100)}%` }}
          />
        </div>
      </div>

      {/* Source */}
      {cell.source && (
        <div>
          <span className="text-xs text-sand-400">ソース: </span>
          <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium ${
            cell.source === 'document' ? 'bg-blue-50 text-blue-700' :
            cell.source === 'inferred' ? 'bg-amber-50 text-amber-700' : 'bg-cream-200 text-sand-500'
          }`}>
            {cell.source === 'document' ? '文書' :
             cell.source === 'inferred' ? '推定' : 'デフォルト'}
          </span>
        </div>
      )}

      {/* Evidence Quote */}
      {evidence?.quote ? (
        <div>
          <span className="text-xs text-sand-400 block mb-1.5">原文引用:</span>
          <blockquote className="bg-cream-100 border-l-3 border-gold-400 px-3 py-2.5 text-sm text-dark-900 italic rounded-r-xl">
            &ldquo;{evidence.quote}&rdquo;
          </blockquote>
          {evidence.page && (
            <p className="text-xs text-sand-400 mt-1">
              ページ {evidence.page}
            </p>
          )}
        </div>
      ) : (
        <div className="bg-cream-100 rounded-2xl p-3">
          <p className="text-xs text-sand-500">
            文書に記載なし — デフォルト値または推定値を使用
          </p>
        </div>
      )}

      {/* Rationale */}
      {(evidence?.rationale || cell.reasoning) && (
        <div>
          <span className="text-xs text-sand-400 block mb-1">根拠:</span>
          <p className="text-sm text-dark-900">{evidence?.rationale || cell.reasoning}</p>
        </div>
      )}

      {/* Value (if Phase 5 extraction) */}
      {cell.value != null && (
        <div>
          <span className="text-xs text-sand-400 block mb-1">抽出値:</span>
          <p className="text-lg font-mono font-bold text-dark-900">
            {typeof cell.value === 'number' ? cell.value.toLocaleString() : cell.value}
          </p>
          {cell.original_text && (
            <p className="text-xs text-sand-400 mt-0.5">原文: {cell.original_text}</p>
          )}
        </div>
      )}

      {/* Segment info */}
      {cell.segment && (
        <div>
          <span className="text-xs text-sand-400">セグメント: </span>
          <span className="text-xs text-dark-900">{cell.segment}</span>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div>
          <span className="text-xs text-sand-400 block mb-1">警告:</span>
          <ul className="space-y-1">
            {warnings.map((w: string, i: number) => (
              <li key={i} className="text-xs text-red-500 flex items-start gap-1">
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
