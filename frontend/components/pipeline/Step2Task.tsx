'use client'

import { useState } from 'react'
import type { TargetSuggestion, MoleculeInput } from '@/lib/types'

type TaskType = 'virtual_screening' | 'protein_design' | 'denovo_generation'

interface Props {
  selectedTarget: TargetSuggestion | null
  onTaskSelected: (task: TaskType, molecules: MoleculeInput) => void
}

const TASKS = [
  { id: 'virtual_screening' as TaskType, title: 'Virtual Screening', desc: 'Test molecules against this target', detail: 'Dock a library of molecules and rank by binding affinity + ADMET', available: true },
  { id: 'protein_design' as TaskType, title: 'Protein Design', desc: 'Design a novel protein binder with AI', detail: 'AI-powered protein sequence design for the target binding site', available: true },
  { id: 'denovo_generation' as TaskType, title: 'De Novo Generation', desc: 'Generate new molecules from scratch', detail: 'AI generates novel drug-like molecules targeting this protein', available: true },
]

export default function Step2Task({ selectedTarget, onTaskSelected }: Props) {
  const [selected, setSelected] = useState<TaskType | null>(null)
  const [smilesText, setSmilesText] = useState('')
  const [useZinc, setUseZinc] = useState(false)
  const [numDesigns, setNumDesigns] = useState(8)
  const [numMolecules, setNumMolecules] = useState(20)

  function handleContinue() {
    if (!selected) return

    if (selected === 'virtual_screening') {
      const smilesList = smilesText.split(/[\n,]/).map((s) => s.trim()).filter(Boolean)
      const molecules: MoleculeInput = useZinc ? { use_zinc_subset: true } : { smiles: smilesList }
      onTaskSelected(selected, molecules)
    } else {
      // Protein design and de novo don't need molecule input
      onTaskSelected(selected, {})
    }
  }

  const canContinue = (() => {
    if (!selected) return false
    if (selected === 'virtual_screening') return useZinc || smilesText.trim().length > 0
    return true
  })()

  return (
    <div className="space-y-6">
      {selectedTarget && (
        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-sm">
          Target: <span className="font-medium">{selectedTarget.protein_name}</span> ({selectedTarget.gene_symbol})
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-3">
        {TASKS.map((t) => (
          <button key={t.id} disabled={!t.available} onClick={() => setSelected(t.id)}
            className={`rounded-lg border-2 p-4 text-left transition-colors ${
              selected === t.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
              : t.available ? 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
              : 'border-gray-100 dark:border-gray-800 opacity-50 cursor-not-allowed'}`}>
            <h3 className="font-semibold">{t.title}</h3>
            <p className="mt-1 text-sm text-gray-500">{t.desc}</p>
            <p className="mt-2 text-xs text-gray-400">{t.detail}</p>
          </button>
        ))}
      </div>

      {/* Virtual Screening options */}
      {selected === 'virtual_screening' && (
        <div className="space-y-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-medium">Provide molecules to screen</h4>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={useZinc} onChange={(e) => setUseZinc(e.target.checked)} className="rounded" />
            Use ZINC drug-like subset (5,000 molecules)
          </label>
          {!useZinc && (
            <textarea rows={5} value={smilesText} onChange={(e) => setSmilesText(e.target.value)}
              placeholder={"CC(=O)Oc1ccccc1C(=O)O\nc1ccc2[nH]c(=O)c(=O)[nH]c2c1\nCCO"}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 font-mono text-sm focus:border-blue-500 outline-none" />
          )}
        </div>
      )}

      {/* Protein Design options */}
      {selected === 'protein_design' && (
        <div className="space-y-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-medium">Protein Design Options</h4>
          <p className="text-sm text-gray-500">
            AI will design novel protein binder sequences that target the binding site of {selectedTarget?.protein_name || 'the target protein'}.
          </p>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600 dark:text-gray-400">Number of designs:</label>
            <select value={numDesigns} onChange={(e) => setNumDesigns(Number(e.target.value))}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm">
              {[4, 8, 12, 16, 20].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
      )}

      {/* De Novo Generation options */}
      {selected === 'denovo_generation' && (
        <div className="space-y-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-medium">De Novo Generation Options</h4>
          <p className="text-sm text-gray-500">
            AI will generate novel drug-like molecules designed to bind {selectedTarget?.protein_name || 'the target protein'}.
            Generated molecules are validated by RDKit and scored with ADMET.
          </p>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600 dark:text-gray-400">Number of molecules:</label>
            <select value={numMolecules} onChange={(e) => setNumMolecules(Number(e.target.value))}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm">
              {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
      )}

      {selected && (
        <button onClick={handleContinue} disabled={!canContinue}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed">
          {selected === 'virtual_screening' ? `Continue with ${useZinc ? '5,000 ZINC molecules' : 'custom molecules'}`
            : selected === 'protein_design' ? `Design ${numDesigns} protein binders`
            : `Generate ${numMolecules} novel molecules`}
        </button>
      )}
    </div>
  )
}
