'use client'

import type { TargetSuggestion } from '@/lib/types'

interface Props {
  selectedTarget: TargetSuggestion | null
  onConfirm: () => void
}

export default function Step3Structure({ selectedTarget, onConfirm }: Props) {
  if (!selectedTarget) {
    return <div className="text-center text-gray-400 py-12">No target selected</div>
  }

  const hasPdb = selectedTarget.has_pdb_structure

  return (
    <div className="space-y-6">
      {/* Structure status banner */}
      <div className={`rounded-lg p-4 ${hasPdb
        ? 'bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800'
        : 'bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800'}`}>
        <p className={`text-sm font-medium ${hasPdb ? 'text-green-800 dark:text-green-200' : 'text-amber-800 dark:text-amber-200'}`}>
          {hasPdb
            ? `Experimental structure found for ${selectedTarget.protein_name}`
            : `No experimental structure — will predict with ESMFold`}
        </p>
        {hasPdb && selectedTarget.uniprot_id && (
          <p className="mt-1 text-xs text-green-600 dark:text-green-400">
            UniProt: {selectedTarget.uniprot_id} — structures available in PDB
          </p>
        )}
      </div>

      {/* Target summary */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">{selectedTarget.protein_name}</h3>
          <code className="rounded bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-mono">{selectedTarget.gene_symbol}</code>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">{selectedTarget.full_name}</p>
        <p className="text-sm text-gray-500">{selectedTarget.mechanism_summary}</p>

        <div className="flex flex-wrap gap-2 text-xs">
          <span className={`rounded-full px-2 py-0.5 font-medium ${
            selectedTarget.clinical_stage === 'approved' ? 'bg-blue-100 text-blue-800' :
            selectedTarget.clinical_stage === 'phase3_trials' ? 'bg-indigo-100 text-indigo-800' :
            'bg-amber-100 text-amber-800'}`}>
            {selectedTarget.clinical_stage === 'phase3_trials' ? 'Phase 3' : selectedTarget.clinical_stage}
          </span>
          <span className={`font-medium ${
            selectedTarget.difficulty === 'easy' ? 'text-green-600' :
            selectedTarget.difficulty === 'moderate' ? 'text-yellow-600' : 'text-red-600'}`}>
            {selectedTarget.difficulty} difficulty
          </span>
        </div>
      </div>

      {/* 3D viewer placeholder */}
      <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-600 h-48 flex items-center justify-center">
        <p className="text-sm text-gray-400">3D structure preview — available after pipeline completes</p>
      </div>

      <button onClick={onConfirm}
        className="w-full rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700">
        Confirm and Run Pipeline
      </button>
    </div>
  )
}
