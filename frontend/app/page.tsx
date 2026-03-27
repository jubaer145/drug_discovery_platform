import PipelineWizard from '@/components/pipeline/PipelineWizard'

export default function Home() {
  return (
    <main className="min-h-screen p-6 md:p-12 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold tracking-tight mb-8">Drug Discovery Platform</h1>
      <PipelineWizard />
    </main>
  )
}
