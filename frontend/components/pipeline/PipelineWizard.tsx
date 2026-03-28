'use client'

import { useState, useCallback } from 'react'
import { usePipeline } from '@/hooks/usePipeline'
import type { TargetSuggestion, MoleculeInput, RankedCandidate } from '@/lib/types'
import { api } from '@/lib/api'
import Step1Target from './Step1Target'
import Step2Task from './Step2Task'
import Step3Structure from './Step3Structure'
import Step4Running from './Step4Running'
import Step5Results from './Step5Results'
import Step6Viewer from './Step6Viewer'

const STEPS = [
  { num: 1, label: 'Target' },
  { num: 2, label: 'Task' },
  { num: 3, label: 'Structure' },
  { num: 4, label: 'Running' },
  { num: 5, label: 'Results' },
  { num: 6, label: 'Viewer' },
] as const

export default function PipelineWizard() {
  const { step, nextStep, prevStep, goToStep } = usePipeline()
  const [selectedTarget, setSelectedTarget] = useState<TargetSuggestion | null>(null)
  const [taskType, setTaskType] = useState<string | null>(null)
  const [molecules, setMolecules] = useState<MoleculeInput | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [viewCandidate, setViewCandidate] = useState<RankedCandidate | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleTaskSelected(task: string, mols: MoleculeInput) {
    setTaskType(task)
    setMolecules(mols)
    nextStep() // go to step 3
  }

  async function handleConfirmPipeline() {
    if (!selectedTarget || !molecules) return
    setError(null)
    try {
      const res = await api.pipeline.run({
        target_uniprot_id: selectedTarget.uniprot_id || undefined,
        target_pdb_id: selectedTarget.uniprot_id ? undefined : selectedTarget.gene_symbol,
        task_type: taskType as 'virtual_screening',
        molecules,
      })
      setJobId(res.job_id)
      nextStep() // go to step 4
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline failed to start')
    }
  }

  const handlePipelineComplete = useCallback(() => {
    goToStep(5)
  }, [goToStep])

  function handleViewPose(candidate: RankedCandidate) {
    setViewCandidate(candidate)
    goToStep(6)
  }

  // Determine if Next button should be enabled
  const canGoNext = (() => {
    if (step === 1) return !!selectedTarget
    if (step === 2) return !!taskType && !!molecules
    if (step === 3) return true
    return false
  })()

  return (
    <div className="space-y-8">
      {/* Step indicator */}
      <nav className="flex items-center justify-between">
        {STEPS.map(({ num, label }, i) => (
          <div key={num} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-2">
              <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors ${
                num === step ? 'bg-blue-600 text-white'
                : num < step ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                : 'bg-gray-100 text-gray-400 dark:bg-gray-800'}`}>
                {num < step ? (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : num}
              </div>
              <span className={`text-sm hidden sm:inline ${num === step ? 'font-medium text-gray-900 dark:text-white' : 'text-gray-400'}`}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`mx-3 h-px flex-1 ${num < step ? 'bg-blue-300' : 'bg-gray-200 dark:bg-gray-700'}`} />
            )}
          </div>
        ))}
      </nav>

      {/* Step content */}
      <div className="min-h-[400px]">
        {step === 1 && <Step1Target onTargetSelected={setSelectedTarget} />}
        {step === 2 && <Step2Task selectedTarget={selectedTarget} onTaskSelected={handleTaskSelected} />}
        {step === 3 && <Step3Structure selectedTarget={selectedTarget} onConfirm={handleConfirmPipeline} />}
        {step === 4 && jobId && <Step4Running jobId={jobId} onComplete={handlePipelineComplete} />}
        {step === 5 && jobId && <Step5Results jobId={jobId} onViewPose={handleViewPose} />}
        {step === 6 && jobId && <Step6Viewer jobId={jobId} pdbPath={viewCandidate?.pose_3d_path} />}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Navigation — hidden during running/results */}
      {step <= 3 && (
        <div className="flex justify-between border-t border-gray-200 dark:border-gray-700 pt-4">
          <button onClick={prevStep} disabled={step === 1}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed">
            Back
          </button>
          {step < 3 && (
            <button onClick={nextStep} disabled={!canGoNext}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed">
              {step === 1 && selectedTarget ? `Continue with ${selectedTarget.protein_name}` : 'Next'}
            </button>
          )}
        </div>
      )}

      {step >= 5 && (
        <div className="flex justify-between border-t border-gray-200 dark:border-gray-700 pt-4">
          <button onClick={() => goToStep(5)}
            className={`rounded-lg border px-4 py-2 text-sm font-medium ${step === 5 ? 'border-blue-500 text-blue-600' : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'}`}>
            Results Table
          </button>
          <button onClick={() => goToStep(1)}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
            New Pipeline
          </button>
        </div>
      )}
    </div>
  )
}
