'use client'

import { useState, useEffect } from 'react'
import { useJobProgress } from '@/lib/websocket'
import { api } from '@/lib/api'

const STEP_LABELS: Record<string, string> = {
  target_resolution: 'Resolving target',
  molecule_preparation: 'Preparing molecules',
  admet_prefilter: 'ADMET pre-filter',
  docking: 'Molecular docking',
  admet_tier2: 'ADMET analysis',
  ranking: 'Ranking candidates',
  protein_design: 'Designing protein binders',
  molecule_generation: 'Generating novel molecules',
  admet_scoring: 'ADMET scoring',
}

const TASK_STEPS: Record<string, string[]> = {
  virtual_screening: ['target_resolution', 'molecule_preparation', 'admet_prefilter', 'docking', 'admet_tier2', 'ranking'],
  protein_design: ['target_resolution', 'protein_design'],
  denovo_generation: ['target_resolution', 'molecule_generation', 'admet_scoring'],
}

interface Props {
  jobId: string
  taskType?: string
  onComplete: () => void
}

export default function Step4Running({ jobId, taskType, onComplete }: Props) {
  const { progress } = useJobProgress(jobId)
  const [elapsed, setElapsed] = useState(0)
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    const start = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [])

  // Detect completion from WebSocket progress
  useEffect(() => {
    if (!completed && (progress?.status === 'completed' || progress?.status === 'failed')) {
      setCompleted(true)
      onComplete()
    }
  }, [progress?.status, onComplete, completed])

  // Fallback: poll job status every 5 seconds in case WebSocket doesn't work
  useEffect(() => {
    if (completed) return
    const interval = setInterval(async () => {
      try {
        const job = await api.jobs.get(jobId)
        if (job.status === 'completed' || job.status === 'failed') {
          setCompleted(true)
          onComplete()
        }
      } catch { /* ignore polling errors */ }
    }, 5000)
    return () => clearInterval(interval)
  }, [jobId, onComplete, completed])

  const pct = progress?.progress_pct ?? 0
  const allSteps = TASK_STEPS[taskType || 'virtual_screening'] || TASK_STEPS.virtual_screening
  const completedSteps = new Set(progress?.completed_steps ?? [])
  const current = progress?.current_step ?? ''
  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600 dark:text-gray-400">{progress?.message || 'Starting pipeline...'}</span>
          <span className="text-gray-500">{pct}%</span>
        </div>
        <div className="h-3 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
          <div className="h-full rounded-full bg-blue-500 transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Step checklist */}
      <div className="space-y-2">
        {allSteps.map((step) => {
          const isDone = completedSteps.has(step)
          const isRunning = current === step && !isDone
          return (
            <div key={step} className="flex items-center gap-3 text-sm">
              {isDone ? (
                <svg className="h-5 w-5 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : isRunning ? (
                <svg className="h-5 w-5 text-blue-500 animate-spin shrink-0" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <div className="h-5 w-5 rounded-full border-2 border-gray-300 dark:border-gray-600 shrink-0" />
              )}
              <span className={isDone ? 'text-gray-500' : isRunning ? 'font-medium' : 'text-gray-400'}>
                {STEP_LABELS[step] || step}
              </span>
            </div>
          )
        })}
      </div>

      {/* Elapsed time */}
      <p className="text-xs text-gray-400 text-center">
        Elapsed: {mins}:{secs.toString().padStart(2, '0')}
      </p>

      {elapsed > 3600 && (
        <div className="rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 p-4 text-sm text-amber-700 dark:text-amber-300">
          Pipeline has been running for over 60 minutes. Large molecule libraries may take longer.
        </div>
      )}

      {progress?.status === 'failed' && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-300 space-y-2">
          <p className="font-medium">Pipeline failed at: {STEP_LABELS[progress.current_step] || progress.current_step || 'unknown step'}</p>
          <p>{progress.message}</p>
        </div>
      )}
    </div>
  )
}
