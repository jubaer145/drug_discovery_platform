'use client'

import { useState } from 'react'
import type { TargetSuggestion } from '@/lib/types'
import NaturalLanguageQuery from '@/components/target/NaturalLanguageQuery'
import TechnicalSearch from '@/components/target/TechnicalSearch'

type Tab = 'natural' | 'technical'

interface Props {
  onTargetSelected: (target: TargetSuggestion) => void
}

export default function Step1Target({ onTargetSelected }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('natural')

  return (
    <div>
      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab('natural')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'natural'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Describe Disease
          </button>
          <button
            onClick={() => setActiveTab('technical')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'technical'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Technical Search
          </button>
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'natural' ? (
        <NaturalLanguageQuery onTargetSelected={onTargetSelected} />
      ) : (
        <TechnicalSearch onTargetSelected={onTargetSelected} />
      )}
    </div>
  )
}
