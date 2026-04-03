'use client'

import { useEffect, useRef, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const ESMFOLD_URL = 'https://api.esmatlas.com/foldSequence/v1/pdb/'

interface Props {
  jobId: string
  sequence: string
  designName: string
}

export default function ProteinDesignViewer({ jobId, sequence, designName }: Props) {
  const viewerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [predicted, setPredicted] = useState(false)

  // Load 3Dmol.js
  useEffect(() => {
    if (document.querySelector('script[src*="3Dmol"]')) return
    const script = document.createElement('script')
    script.src = 'https://3Dmol.csb.pitt.edu/build/3Dmol-min.js'
    script.async = true
    document.head.appendChild(script)
  }, [])

  async function handlePredict() {
    if (!viewerRef.current || !sequence) return
    setLoading(true)
    setError(null)

    try {
      // 1. Fetch target PDB from MinIO
      let targetPdb: string | null = null
      try {
        const targetResp = await fetch(`${API_URL}/api/files/structures/${jobId}/receptor.pdb`)
        if (targetResp.ok) targetPdb = await targetResp.text()
      } catch { /* no target PDB available */ }

      // 2. Predict designed binder structure via ESMFold
      const cleanSeq = sequence.replace(/[^A-Z]/g, '')
      const esmResp = await fetch(ESMFOLD_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: cleanSeq,
      })

      if (!esmResp.ok) {
        throw new Error(`ESMFold returned ${esmResp.status}`)
      }

      const binderPdb = await esmResp.text()

      // 3. Wait for 3Dmol to be available
      const win = window as unknown as Record<string, unknown>
      const waitFor3Dmol = () => new Promise<unknown>((resolve) => {
        const check = setInterval(() => {
          if (win.$3Dmol) { clearInterval(check); resolve(win.$3Dmol) }
        }, 200)
      })

      const $3Dmol = await waitFor3Dmol() as {
        createViewer: (el: HTMLElement, opts: Record<string, unknown>) => {
          addModel: (data: string, format: string) => { setStyle: (sel: Record<string, unknown>, style: Record<string, unknown>) => void }
          zoomTo: () => void
          render: () => void
          zoom: (f: number) => void
        }
      }

      // 4. Render both structures
      viewerRef.current.innerHTML = ''
      const viewer = $3Dmol.createViewer(viewerRef.current, {
        backgroundColor: '0x1a1a2e',
        antialias: true,
      })

      // Add target protein (gray cartoon)
      if (targetPdb) {
        const targetModel = viewer.addModel(targetPdb, 'pdb')
        targetModel.setStyle({}, { cartoon: { color: 'gray', opacity: 0.6 } })
      }

      // Add designed binder (spectrum colored)
      const binderModel = viewer.addModel(binderPdb, 'pdb')
      binderModel.setStyle({}, { cartoon: { color: 'spectrum' } })

      viewer.zoomTo()
      viewer.render()
      viewer.zoom(0.8)
      setPredicted(true)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to predict structure')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-2">
      {!predicted && (
        <button
          onClick={handlePredict}
          disabled={loading}
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? (
            <span className="inline-flex items-center gap-1">
              <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Predicting 3D structure...
            </span>
          ) : (
            'Predict & View 3D Structure'
          )}
        </button>
      )}

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      {(loading || predicted) && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
          style={{ position: 'relative', width: '100%', height: '300px' }}>
          <div ref={viewerRef} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }} />
        </div>
      )}

      {predicted && (
        <p className="text-xs text-gray-400">
          {designName}: spectrum coloring | Target: gray (if available)
        </p>
      )}
    </div>
  )
}
