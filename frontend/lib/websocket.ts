'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { JobProgressUpdate } from './types'
import { api } from './api'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000'

export function useJobProgress(jobId: string | null) {
  const [progress, setProgress] = useState<JobProgressUpdate | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)

  const connect = useCallback(() => {
    if (!jobId) return

    const ws = new WebSocket(`${WS_URL}/ws/jobs/${jobId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      retriesRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as JobProgressUpdate
        setProgress(msg)
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      if (retriesRef.current < 3) {
        retriesRef.current++
        setTimeout(connect, 2000)
      }
    }

    ws.onerror = () => ws.close()
  }, [jobId])

  // Fallback polling
  useEffect(() => {
    if (!jobId || isConnected) return
    const interval = setInterval(async () => {
      try {
        const job = await api.jobs.get(jobId)
        setProgress({
          job_id: jobId,
          status: job.status,
          step: '',
          progress_pct: job.status === 'completed' ? 100 : job.status === 'running' ? 50 : 0,
          message: job.status === 'completed' ? 'Complete' : 'Running...',
          completed_steps: [],
          current_step: '',
          pending_steps: [],
          timestamp: job.updated_at,
        })
      } catch { /* ignore */ }
    }, 3000)
    return () => clearInterval(interval)
  }, [jobId, isConnected])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return { progress, isConnected }
}
