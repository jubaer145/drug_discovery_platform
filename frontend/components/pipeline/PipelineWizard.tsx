'use client'

import { useState } from 'react'
import { usePipeline } from '@/hooks/usePipeline'
import type { TargetSuggestion } from '@/lib/types'
import Step1Target from './Step1Target'

const STEPS = [
  { num: 1, label: 'Target' },
  { num: 2, label: 'Structure' },
  { num: 3, label: 'Molecules' },
  { num: 4, label: 'Docking' },
  { num: 5, label: 'ADMET' },
  { num: 6, label: 'Results' },
] as const

export default function PipelineWizard() {
  const { step, nextStep, prevStep } = usePipeline()
  const [selectedTarget, setSelectedTarget] = useState<TargetSuggestion | null>(null)

  return (
    <div className="space-y-8">
      {/* Step indicator */}
      <nav className="flex items-center justify-between">
        {STEPS.map(({ num, label }, i) => (
          <div key={num} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors ${
                  num === step
                    ? 'bg-blue-600 text-white'
                    : num < step
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                    : 'bg-gray-100 text-gray-400 dark:bg-gray-800'
                }`}
              >
                {num < step ? (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  num
                )}
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
        {step === 1 && (
          <Step1Target onTargetSelected={setSelectedTarget} />
        )}
        {step === 2 && (
          <Placeholder label="Structure Prediction" detail={selectedTarget ? `Selected target: ${selectedTarget.protein_name}` : undefined} />
        )}
        {step === 3 && <Placeholder label="Molecule Selection" />}
        {step === 4 && <Placeholder label="Docking Simulation" />}
        {step === 5 && <Placeholder label="ADMET Prediction" />}
        {step === 6 && <Placeholder label="Results & Visualization" />}
      </div>

      {/* Navigation */}
      <div className="flex justify-between border-t border-gray-200 dark:border-gray-700 pt-4">
        <button
          onClick={prevStep}
          disabled={step === 1}
          className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Back
        </button>
        <button
          onClick={nextStep}
          disabled={step === 6 || (step === 1 && !selectedTarget)}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed"
        >
          {step === 1 && selectedTarget ? `Continue with ${selectedTarget.protein_name}` : 'Next'}
        </button>
      </div>
    </div>
  )
}

function Placeholder({ label, detail }: { label: string; detail?: string }) {
  return (
    <div className="flex h-[400px] items-center justify-center rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
      <div className="text-center">
        <p className="text-lg font-medium text-gray-400">{label}</p>
        <p className="mt-1 text-sm text-gray-400">Coming soon</p>
        {detail && <p className="mt-2 text-xs text-gray-500">{detail}</p>}
      </div>
    </div>
  )
}
