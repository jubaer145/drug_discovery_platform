'use client'

import { useState, useCallback } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface ValidationResult {
  smiles: string
  valid: boolean
  error: string | null
}

interface Props {
  onSmilesReady: (smiles: string[]) => void
}

export default function SmilesInput({ onSmilesReady }: Props) {
  const [text, setText] = useState('')
  const [results, setResults] = useState<ValidationResult[]>([])
  const [validating, setValidating] = useState(false)

  const validate = useCallback(async (input: string) => {
    const lines = input.split(/[\n,]/).map((s) => s.trim()).filter(Boolean)
    if (lines.length === 0) {
      setResults([])
      return
    }

    setValidating(true)
    try {
      const res = await fetch(`${API_URL}/api/molecules/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ smiles_list: lines }),
      })
      if (res.ok) {
        const data: ValidationResult[] = await res.json()
        setResults(data)
        const valid = data.filter((r) => r.valid).map((r) => r.smiles)
        onSmilesReady(valid)
      }
    } catch {
      // ignore validation errors
    } finally {
      setValidating(false)
    }
  }, [onSmilesReady])

  function handleChange(value: string) {
    setText(value)
    // Debounce validation
    const timeout = setTimeout(() => validate(value), 500)
    return () => clearTimeout(timeout)
  }

  const validCount = results.filter((r) => r.valid).length
  const invalidCount = results.filter((r) => !r.valid).length

  return (
    <div className="space-y-3">
      <textarea
        rows={6}
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={"Paste SMILES (one per line or comma-separated)\nCC(=O)Oc1ccccc1C(=O)O\nc1ccc2[nH]c(=O)c(=O)[nH]c2c1"}
        className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 font-mono text-sm focus:border-blue-500 outline-none"
      />

      {results.length > 0 && (
        <div className="text-sm">
          <span className="text-green-600">{validCount} valid</span>
          {invalidCount > 0 && (
            <span className="text-red-500 ml-2">{invalidCount} invalid</span>
          )}
          {validating && <span className="text-gray-400 ml-2">Validating...</span>}
        </div>
      )}

      {invalidCount > 0 && (
        <div className="max-h-32 overflow-auto rounded border border-red-200 dark:border-red-800 p-2 text-xs space-y-0.5">
          {results.filter((r) => !r.valid).map((r, i) => (
            <div key={i} className="text-red-500">
              <span className="font-mono">{r.smiles}</span> — {r.error}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
