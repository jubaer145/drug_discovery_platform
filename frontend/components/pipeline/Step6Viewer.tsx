'use client'

import { useEffect, useRef } from 'react'

interface Props {
  jobId: string
  pdbPath?: string | null
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function Step6Viewer({ jobId, pdbPath }: Props) {
  const viewerRef = useRef<HTMLDivElement>(null)
  const viewerInstanceRef = useRef<unknown>(null)

  useEffect(() => {
    const existing = document.querySelector('script[src*="3Dmol"]')
    if (existing) return

    const script = document.createElement('script')
    script.src = 'https://3Dmol.csb.pitt.edu/build/3Dmol-min.js'
    script.async = true
    document.head.appendChild(script)
  }, [])

  useEffect(() => {
    if (!viewerRef.current) return

    const interval = setInterval(() => {
      const win = window as unknown as Record<string, unknown>
      if (win.$3Dmol) {
        clearInterval(interval)
        initViewer(win.$3Dmol)
      }
    }, 200)

    async function initViewer(lib: unknown) {
      if (!viewerRef.current) return
      const $3Dmol = lib as {
        createViewer: (el: HTMLElement, opts: Record<string, unknown>) => {
          addModel: (data: string, format: string) => { setStyle: (sel: Record<string, unknown>, style: Record<string, unknown>) => void }
          zoomTo: () => void
          render: () => void
          zoom: (factor: number) => void
        }
      }

      viewerRef.current.innerHTML = ''
      const viewer = $3Dmol.createViewer(viewerRef.current, {
        backgroundColor: '0x1a1a2e',
        antialias: true,
      })
      viewerInstanceRef.current = viewer

      // Try multiple paths to find the PDB
      const paths = [
        `${API_URL}/api/structures/${jobId}/download`,
        `${API_URL}/api/files/structures/${jobId}/receptor.pdb`,
      ]

      let pdbData: string | null = null
      for (const url of paths) {
        try {
          const r = await fetch(url)
          if (r.ok) {
            pdbData = await r.text()
            break
          }
        } catch { /* try next */ }
      }

      if (pdbData) {
        const model = viewer.addModel(pdbData, 'pdb')
        model.setStyle({}, { cartoon: { color: 'spectrum' } })
        viewer.zoomTo()
        viewer.render()
        viewer.zoom(0.8)
      }
    }

    return () => clearInterval(interval)
  }, [jobId, pdbPath])

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div ref={viewerRef} className="w-full h-[500px] bg-gray-900" />
      </div>
      <div className="flex gap-3 text-xs text-gray-500">
        <span>Protein rendered as cartoon (spectrum coloring)</span>
        {pdbPath && <span>Source: {pdbPath}</span>}
      </div>
      {!pdbPath && !jobId && (
        <div className="text-center py-12 text-gray-400">
          <p>3D viewer requires a completed pipeline with a structure file.</p>
        </div>
      )}
    </div>
  )
}
