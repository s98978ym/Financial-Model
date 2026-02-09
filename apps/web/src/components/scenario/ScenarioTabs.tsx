'use client'

interface ScenarioTabsProps {
  active: 'base' | 'best' | 'worst'
  onChange: (scenario: 'base' | 'best' | 'worst') => void
}

const TABS = [
  { key: 'base' as const, label: 'Base', desc: '基本シナリオ', color: 'blue' },
  { key: 'best' as const, label: 'Best', desc: '売上+20% / コスト-10%', color: 'green' },
  { key: 'worst' as const, label: 'Worst', desc: '売上-20% / コスト+15%', color: 'red' },
]

export function ScenarioTabs({ active, onChange }: ScenarioTabsProps) {
  return (
    <div className="flex gap-2">
      {TABS.map((tab) => {
        const isActive = active === tab.key
        const colorMap: Record<string, string> = {
          blue: isActive ? 'bg-blue-600 text-white' : 'bg-white text-blue-600 border-blue-200 hover:bg-blue-50',
          green: isActive ? 'bg-green-600 text-white' : 'bg-white text-green-600 border-green-200 hover:bg-green-50',
          red: isActive ? 'bg-red-600 text-white' : 'bg-white text-red-600 border-red-200 hover:bg-red-50',
        }

        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`px-4 py-2 rounded-lg border transition-colors ${colorMap[tab.color]}`}
          >
            <span className="font-medium">{tab.label}</span>
            <span className="text-xs block opacity-75">{tab.desc}</span>
          </button>
        )
      })}
    </div>
  )
}
