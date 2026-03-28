'use client'

import { useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const FLAG_DOT = { GREEN: 'bg-green-500', AMBER: 'bg-amber-500', RED: 'bg-red-500' }

interface Props {
  smiles: string
  rank?: number
  affinity?: number
  overall?: 'GREEN' | 'AMBER' | 'RED'
  score?: number
}

export default function MoleculeCard({ smiles, rank, affinity, overall, score }: Props) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(smiles)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 flex gap-3 items-start">
      {/* 2D structure image */}
      <img
        src={`${API_URL}/api/molecules/render?smiles=${encodeURIComponent(smiles)}&size=120`}
        alt={smiles}
        width={120}
        height={120}
        className="rounded bg-white shrink-0"
        loading="lazy"
      />

      <div className="min-w-0 flex-1 space-y-1">
        {rank != null && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-gray-500">#{rank}</span>
            {overall && <span className={`inline-block h-2.5 w-2.5 rounded-full ${FLAG_DOT[overall] || 'bg-gray-400'}`} />}
          </div>
        )}

        {/* SMILES with copy */}
        <div className="flex items-center gap-1">
          <code className="text-xs font-mono text-gray-600 dark:text-gray-400 truncate block max-w-[200px]">{smiles}</code>
          <button onClick={handleCopy} className="text-xs text-blue-500 hover:underline shrink-0">
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>

        {/* Scores */}
        <div className="flex gap-3 text-xs text-gray-500">
          {affinity != null && <span>Affinity: {affinity.toFixed(1)} kcal/mol</span>}
          {score != null && <span>Score: {score.toFixed(3)}</span>}
        </div>
      </div>
    </div>
  )
}
