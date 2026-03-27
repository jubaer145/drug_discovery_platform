'use client'

import type { TargetSuggestion } from '@/lib/types'

const confidenceColor = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-red-100 text-red-800',
} as const

const stageLabel = {
  approved: 'Approved',
  phase3_trials: 'Phase 3',
  preclinical: 'Preclinical',
  unknown: 'Unknown',
} as const

const stageColor = {
  approved: 'bg-blue-100 text-blue-800',
  phase3_trials: 'bg-indigo-100 text-indigo-800',
  preclinical: 'bg-amber-100 text-amber-800',
  unknown: 'bg-gray-100 text-gray-600',
} as const

const difficultyColor = {
  easy: 'text-green-600',
  moderate: 'text-yellow-600',
  difficult: 'text-red-600',
} as const

interface Props {
  suggestion: TargetSuggestion
  selected?: boolean
  onSelect?: (suggestion: TargetSuggestion) => void
}

export default function TargetSuggestionCard({ suggestion, selected, onSelect }: Props) {
  const s = suggestion

  return (
    <button
      type="button"
      onClick={() => onSelect?.(s)}
      className={`w-full text-left rounded-lg border-2 p-4 transition-colors hover:border-blue-400
        ${selected ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900'}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-lg leading-tight">{s.protein_name}</h3>
            <code className="rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-xs font-mono">
              {s.gene_symbol}
            </code>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{s.full_name}</p>
        </div>

        {/* Confidence badge */}
        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${confidenceColor[s.confidence]}`}>
          {s.confidence}
        </span>
      </div>

      {/* Badges row */}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-full px-2 py-0.5 font-medium ${stageColor[s.clinical_stage]}`}>
          {stageLabel[s.clinical_stage]}
        </span>
        <span className={`font-medium ${difficultyColor[s.difficulty]}`}>
          {s.difficulty.charAt(0).toUpperCase() + s.difficulty.slice(1)} difficulty
        </span>
        <span className={s.has_pdb_structure ? 'text-green-600' : 'text-gray-400'}>
          {s.has_pdb_structure ? '3D structure available' : 'No 3D structure'}
        </span>
      </div>

      {/* Body */}
      <p className="mt-3 text-sm text-gray-700 dark:text-gray-300">{s.mechanism_summary}</p>
      <p className="mt-1 text-xs italic text-gray-500 dark:text-gray-400">{s.druggability_note}</p>

      {/* Tags */}
      {s.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {s.tags.map((tag) => (
            <span key={tag} className="rounded bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* UniProt ID */}
      {s.uniprot_id && (
        <p className="mt-2 text-xs text-gray-400">UniProt: {s.uniprot_id}</p>
      )}
    </button>
  )
}
