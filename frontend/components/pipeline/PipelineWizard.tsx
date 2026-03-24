'use client'

import { usePipeline } from '@/hooks/usePipeline'

export default function PipelineWizard() {
  const { step } = usePipeline()
  return (
    <div>
      <p>Step {step} of 6 — coming soon</p>
    </div>
  )
}
