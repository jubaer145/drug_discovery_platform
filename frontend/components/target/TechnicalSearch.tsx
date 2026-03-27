'use client'

import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'
import type { TargetSuggestion } from '@/lib/types'

interface SearchResult {
  uniprot_id: string
  protein_name: string
  gene_symbol: string
  organism: string
}

interface Props {
  onTargetSelected: (target: TargetSuggestion) => void
}

export default function TechnicalSearch({ onTargetSelected }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [selected, setSelected] = useState<SearchResult | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (query.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }

    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await api.targets.search(query, 5)
        setResults(data)
        setShowDropdown(data.length > 0)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
  }, [query])

  function handleSelect(result: SearchResult) {
    setSelected(result)
    setQuery(result.protein_name)
    setShowDropdown(false)

    // Map search result to TargetSuggestion shape
    onTargetSelected({
      protein_name: result.protein_name,
      gene_symbol: result.gene_symbol,
      uniprot_id: result.uniprot_id,
      full_name: result.protein_name,
      confidence: 'high',
      mechanism_summary: `Target resolved via UniProt accession ${result.uniprot_id}`,
      druggability_note: 'Resolved from technical search',
      tags: [result.organism],
      has_pdb_structure: true,
      clinical_stage: 'unknown',
      difficulty: 'moderate',
    })
  }

  return (
    <div className="space-y-4">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setSelected(null) }}
          onFocus={() => results.length > 0 && setShowDropdown(true)}
          placeholder="EGFR, P00533, 1IEP, or search by name..."
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
        />
        {loading && (
          <div className="absolute right-3 top-3">
            <svg className="h-5 w-5 animate-spin text-gray-400" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        )}

        {showDropdown && (
          <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg max-h-60 overflow-auto">
            {results.map((r) => (
              <button key={r.uniprot_id} onClick={() => handleSelect(r)}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 border-b last:border-0 border-gray-100 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{r.protein_name}</span>
                  <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">{r.gene_symbol}</code>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {r.uniprot_id} — {r.organism}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div className="rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 p-3 text-sm">
          Selected: <span className="font-medium">{selected.protein_name}</span> ({selected.gene_symbol}) — {selected.uniprot_id}
        </div>
      )}
    </div>
  )
}
