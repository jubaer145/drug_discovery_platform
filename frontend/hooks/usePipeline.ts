'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import type { PipelineRequest } from '@/lib/types'

export type PipelineStep = 1 | 2 | 3 | 4 | 5 | 6

export function usePipeline() {
  const [step, setStep] = useState<PipelineStep>(1)
  const [jobId, setJobId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runPipeline = async (request: PipelineRequest) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.pipeline.run(request)
      setJobId(res.job_id)
      setStep(4)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline failed')
    } finally {
      setLoading(false)
    }
  }

  const nextStep = () => setStep((s) => Math.min(s + 1, 6) as PipelineStep)
  const prevStep = () => setStep((s) => Math.max(s - 1, 1) as PipelineStep)
  const goToStep = (s: PipelineStep) => setStep(s)

  return { step, jobId, loading, error, runPipeline, nextStep, prevStep, goToStep }
}
