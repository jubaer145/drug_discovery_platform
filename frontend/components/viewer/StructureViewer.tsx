'use client'

import { useEffect, useRef } from 'react'

export default function StructureViewer({ pdbData }: { pdbData: string }) {
  const viewerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // 3Dmol.js initialised here — implemented in Sprint 6
    // Load via CDN: https://3dmol.csb.pitt.edu/build/3Dmol-min.js
  }, [pdbData])

  return <div ref={viewerRef} className="h-96 w-full rounded-lg bg-gray-100 dark:bg-gray-800" />
}
