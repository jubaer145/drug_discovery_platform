'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import type { Job } from '@/lib/types'

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!jobId) return
    setLoading(true)
    try {
      const data = await api.jobs.get(jobId)
      setJob(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    void refresh()
    const interval = setInterval(() => {
      if (job?.status === 'pending' || job?.status === 'running') {
        void refresh()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [jobId, job?.status, refresh])

  return { job, loading, error, refresh }
}
