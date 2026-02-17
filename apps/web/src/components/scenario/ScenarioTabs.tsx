'use client'

interface ScenarioTabsProps {
  active: 'base' | 'best' | 'worst'
  onChange: (scenario: 'base' | 'best' | 'worst') => void
  completionStatus?: Record<string, boolean>
}

const TABS = [
  { key: 'base' as const, label: 'Base', desc: '基本シナリオ', color: 'base' },
  { key: 'best' as const, label: 'Best', desc: '売上+20% / コスト-10%', color: 'best' },
  { key: 'worst' as const, label: 'Worst', desc: '売上-20% / コスト+15%', color: 'worst' },
]

export function ScenarioTabs({ active, onChange, completionStatus }: ScenarioTabsProps) {
  return (
    <div className="flex gap-2">
      {TABS.map((tab) => {
        const isActive = active === tab.key
        const isComplete = completionStatus?.[tab.key] ?? false
        const colorMap: Record<string, string> = {
          base: isActive ? 'bg-dark-900 text-white shadow-warm' : 'bg-white text-sand-600 shadow-warm hover:bg-cream-50',
          best: isActive ? 'bg-emerald-600 text-white shadow-warm' : 'bg-white text-sand-600 shadow-warm hover:bg-cream-50',
          worst: isActive ? 'bg-red-600 text-white shadow-warm' : 'bg-white text-sand-600 shadow-warm hover:bg-cream-50',
        }

        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`px-4 py-2 rounded-2xl transition-colors relative ${colorMap[tab.color as keyof typeof colorMap]}`}
          >
            <div className="flex items-center gap-1.5">
              <span className="font-medium">{tab.label}</span>
              {isComplete ? (
                <span className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] ${
                  isActive ? 'bg-white/30 text-white' : 'bg-green-100 text-green-600'
                }`} title="設定完了">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </span>
              ) : (
                <span className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] ${
                  isActive ? 'bg-white/20 text-white/70' : 'bg-cream-200 text-sand-400'
                }`} title="未設定">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <circle cx="12" cy="12" r="9" />
                  </svg>
                </span>
              )}
            </div>
            <span className="text-xs block opacity-75">{tab.desc}</span>
          </button>
        )
      })}
    </div>
  )
}
