'use client'

import type { QASettings, TargetAudience, DetailLevel, AnswerLength } from '@/data/qaTemplates'
import { TARGET_OPTIONS, DETAIL_OPTIONS, LENGTH_OPTIONS, COUNT_OPTIONS } from '@/data/qaTemplates'

interface QASettingsProps {
  settings: QASettings
  onChange: (settings: QASettings) => void
  onGenerate: () => void
  isGenerating: boolean
}

function OptionCard({
  label,
  desc,
  selected,
  onClick,
  color,
}: {
  label: string
  desc: string
  selected: boolean
  onClick: () => void
  color?: string
}) {
  return (
    <button
      onClick={onClick}
      className={'flex-1 min-w-0 text-left p-3 rounded-2xl border-2 transition-all ' + (
        selected
          ? 'border-gold-500 bg-cream-100 shadow-warm'
          : 'border-cream-200 bg-white hover:border-cream-300 hover:bg-cream-50'
      )}
    >
      <div className={'text-sm font-medium ' + (selected ? 'text-gold-600' : 'text-dark-900')}>
        {label}
      </div>
      <div className="text-xs text-sand-500 mt-0.5">{desc}</div>
    </button>
  )
}

export function QASettingsPanel({ settings, onChange, onGenerate, isGenerating }: QASettingsProps) {
  function updateTarget(target: TargetAudience) {
    onChange(Object.assign({}, settings, { target: target }))
  }
  function updateDetail(detailLevel: DetailLevel) {
    onChange(Object.assign({}, settings, { detailLevel: detailLevel }))
  }
  function updateLength(answerLength: AnswerLength) {
    onChange(Object.assign({}, settings, { answerLength: answerLength }))
  }
  function updateCount(count: number) {
    onChange(Object.assign({}, settings, { count: count }))
  }

  return (
    <div className="bg-white rounded-3xl shadow-warm overflow-hidden">
      <div className="px-6 py-4 border-b border-cream-200 bg-cream-100">
        <h3 className="font-semibold text-dark-900">Q&A 設定</h3>
        <p className="text-xs text-sand-500 mt-0.5">ターゲットと形式を設定してQ&Aを生成</p>
      </div>

      <div className="p-6 space-y-6">
        {/* Target Audience */}
        <div>
          <label className="block text-sm font-medium text-sand-600 mb-2">
            誰に対するQ&A？
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {TARGET_OPTIONS.map(function(opt) {
              return (
                <OptionCard
                  key={opt.key}
                  label={opt.label}
                  desc={opt.desc}
                  selected={settings.target === opt.key}
                  onClick={function() { updateTarget(opt.key) }}
                />
              )
            })}
          </div>
        </div>

        {/* Detail Level */}
        <div>
          <label className="block text-sm font-medium text-sand-600 mb-2">
            詳しさ（どのような場面か？）
          </label>
          <div className="grid grid-cols-3 gap-2">
            {DETAIL_OPTIONS.map(function(opt) {
              return (
                <OptionCard
                  key={opt.key}
                  label={opt.label}
                  desc={opt.desc}
                  selected={settings.detailLevel === opt.key}
                  onClick={function() { updateDetail(opt.key) }}
                />
              )
            })}
          </div>
        </div>

        {/* Answer Length */}
        <div>
          <label className="block text-sm font-medium text-sand-600 mb-2">
            回答の長さ
          </label>
          <div className="grid grid-cols-3 gap-2">
            {LENGTH_OPTIONS.map(function(opt) {
              return (
                <OptionCard
                  key={opt.key}
                  label={opt.label + ' (' + opt.chars + ')'}
                  desc={opt.desc}
                  selected={settings.answerLength === opt.key}
                  onClick={function() { updateLength(opt.key) }}
                />
              )
            })}
          </div>
        </div>

        {/* Count */}
        <div>
          <label className="block text-sm font-medium text-sand-600 mb-2">
            Q&A数
          </label>
          <div className="flex gap-2">
            {COUNT_OPTIONS.map(function(count) {
              return (
                <button
                  key={count}
                  onClick={function() { updateCount(count) }}
                  className={'px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ' + (
                    settings.count === count
                      ? 'border-gold-500 bg-cream-100 text-gold-600'
                      : 'border-cream-200 bg-white text-sand-600 hover:border-cream-300'
                  )}
                >
                  {count}問
                </button>
              )
            })}
          </div>
        </div>

        {/* Generate Button */}
        <button
          onClick={onGenerate}
          disabled={isGenerating}
          className="w-full py-3 rounded-2xl font-medium text-white bg-dark-900 hover:bg-dark-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-warm hover:shadow-warm-md"
        >
          {isGenerating ? 'Q&A を生成中...' : 'Q&A を生成'}
        </button>
      </div>
    </div>
  )
}
