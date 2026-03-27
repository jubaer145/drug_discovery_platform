'use client'

import { useState } from 'react'
import type { TargetSuggestion, AIQueryResponse } from '@/lib/types'
import { api } from '@/lib/api'
import TargetSuggestionCard from './TargetSuggestionCard'

interface Props {
  onTargetSelected: (target: TargetSuggestion) => void
}

export default function NaturalLanguageQuery({ onTargetSelected }: Props) {
  const [query, setQuery] = useState('')
  const [maxTargets, setMaxTargets] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<AIQueryResponse | null>(null)
  const [selected, setSelected] = useState<TargetSuggestion | null>(null)

  const canSubmit = query.length >= 10 && query.length <= 500 && !loading

  async function handleSubmit() {
    if (!canSubmit) return
    setLoading(true)
    setError(null)
    setResponse(null)
    setSelected(null)

    try {
      const data = await api.ai.suggestTargets({ query, max_targets: maxTargets })
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get suggestions')
    } finally {
      setLoading(false)
    }
  }

  function handleSelect(target: TargetSuggestion) {
    setSelected(target)
    onTargetSelected(target)
  }

  return (
    <div className="space-y-6">
      {/* Input area */}
      <div className="space-y-3">
        <label htmlFor="disease-query" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Describe a disease, condition, or biological target
        </label>
        <textarea
          id="disease-query"
          rows={3}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. What proteins are involved in treatment-resistant depression? or Which molecular targets drive triple-negative breast cancer?"
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
        />
        <div className="flex items-center justify-between">
          <span className={`text-xs ${query.length < 10 ? 'text-gray-400' : query.length > 500 ? 'text-red-500' : 'text-gray-400'}`}>
            {query.length}/500 characters {query.length > 0 && query.length < 10 && '(minimum 10)'}
          </span>
          <div className="flex items-center gap-3">
            <label htmlFor="max-targets" className="text-xs text-gray-500">Max targets:</label>
            <select
              id="max-targets"
              value={maxTargets}
              onChange={(e) => setMaxTargets(Number(e.target.value))}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-xs"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing with AI...
            </span>
          ) : (
            'Find Drug Targets'
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Results */}
      {response && (
        <div className="space-y-4">
          {/* Interpretation banner */}
          <div className="rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 p-4">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
              {response.query_interpretation}
            </p>
            <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
              {response.confidence_explanation}
            </p>
          </div>

          {/* Target cards */}
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
            {response.targets.map((target) => (
              <TargetSuggestionCard
                key={target.gene_symbol}
                suggestion={target}
                selected={selected?.gene_symbol === target.gene_symbol}
                onSelect={handleSelect}
              />
            ))}
          </div>

          {response.targets.length === 0 && (
            <p className="text-center text-sm text-gray-500 py-8">
              No targets found. Try a more specific disease or condition description.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
