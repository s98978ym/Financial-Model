'use client'

interface CompletionChecklistProps {
  stats: {
    total: number
    mapped: number
    highConf: number
    midConf: number
    lowConf: number
    docSource: number
  }
  nextActions: string[]
}

export function CompletionChecklist({ stats, nextActions }: CompletionChecklistProps) {
  const completionPct = stats.total > 0 ? Math.round((stats.mapped / stats.total) * 100) : 0
  const docPct = stats.mapped > 0 ? Math.round((stats.docSource / stats.mapped) * 100) : 0

  return (
    <div className="bg-white rounded-3xl shadow-warm p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-dark-900">完了状況</h3>

        {/* Completion Ring */}
        <div className="relative w-14 h-14">
          <svg className="w-14 h-14 -rotate-90" viewBox="0 0 100 100">
            <circle
              cx="50" cy="50" r="45"
              fill="none"
              stroke="#E8E0D4"
              strokeWidth="8"
            />
            <circle
              cx="50" cy="50" r="45"
              fill="none"
              stroke={completionPct >= 80 ? '#22c55e' : completionPct >= 50 ? '#eab308' : '#ef4444'}
              strokeWidth="8"
              strokeDasharray="283"
              strokeDashoffset={283 - (283 * completionPct) / 100}
              strokeLinecap="round"
              className="transition-all duration-700 ease-out"
              style={{ animation: 'ring-fill 1s ease-out' }}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-dark-900">
            {completionPct}%
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div className="bg-cream-100 rounded-2xl p-2 text-center">
          <div className="text-lg font-bold text-dark-900">
            {stats.mapped}/{stats.total}
          </div>
          <div className="text-xs text-sand-400">マッピング済み</div>
        </div>
        <div className="bg-green-50 rounded-2xl p-2 text-center">
          <div className="text-lg font-bold text-green-700">{stats.highConf}</div>
          <div className="text-xs text-sand-400">高確信度</div>
        </div>
        <div className="bg-yellow-50 rounded-2xl p-2 text-center">
          <div className="text-lg font-bold text-yellow-700">{stats.midConf}</div>
          <div className="text-xs text-sand-400">中確信度</div>
        </div>
        <div className="bg-red-50 rounded-2xl p-2 text-center">
          <div className="text-lg font-bold text-red-700">{stats.lowConf}</div>
          <div className="text-xs text-sand-400">低確信度</div>
        </div>
      </div>

      {/* Document Source Rate */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-sand-500 mb-1">
          <span>文書由来率</span>
          <span>{docPct}%</span>
        </div>
        <div className="w-full bg-cream-200 rounded-full h-2">
          <div
            className="bg-gold-500 h-2 rounded-full transition-all"
            style={{ width: `${docPct}%` }}
          />
        </div>
      </div>

      {/* Next Actions */}
      {nextActions.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-sand-400 mb-2">
            次にやるべきこと:
          </h4>
          <ul className="space-y-1.5">
            {nextActions.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-dark-900">
                <span className="flex-shrink-0 w-5 h-5 bg-gold-100 text-gold-600 rounded-full flex items-center justify-center text-xs font-bold">
                  {i + 1}
                </span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
