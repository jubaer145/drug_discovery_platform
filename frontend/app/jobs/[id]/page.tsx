'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import type { Job } from '@/lib/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const STATUS_BADGE: Record<string, string> = {
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  pending: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
}

export default function JobPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/jobs/${params.id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Job not found (${r.status})`)
        return r.json()
      })
      .then((data) => setJob(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [params.id])

  if (loading) {
    return (
      <main className="min-h-screen p-6 md:p-12 max-w-5xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </main>
    )
  }

  if (error || !job) {
    return (
      <main className="min-h-screen p-6 md:p-12 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold">Job Not Found</h1>
        <p className="mt-2 text-gray-500">{error || 'This job does not exist.'}</p>
        <Link href="/library" className="mt-4 inline-block text-blue-600 hover:underline">
          Back to History
        </Link>
      </main>
    )
  }

  const output = job.output_data as Record<string, unknown> | null
  const summary = output?.pipeline_summary as Record<string, number> | null
  const candidates = (output?.ranked_candidates as Array<Record<string, unknown>>) || []
  const pipelineError = output?.error as string | null

  return (
    <main className="min-h-screen p-6 md:p-12 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{job.job_type} Job</h1>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[job.status] || STATUS_BADGE.pending}`}>
              {job.status}
            </span>
          </div>
          <p className="text-xs text-gray-500 font-mono mt-1">{job.id}</p>
          <p className="text-sm text-gray-400 mt-1">
            Created: {new Date(job.created_at).toLocaleString()}
          </p>
        </div>
        <Link href="/library" className="text-sm text-blue-600 hover:underline">
          Back to History
        </Link>
      </div>

      {/* Error state */}
      {job.status === 'failed' && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4">
          <p className="text-sm font-medium text-red-800 dark:text-red-200">Pipeline Failed</p>
          <p className="text-sm text-red-600 dark:text-red-400 mt-1">{pipelineError || job.error || 'Unknown error'}</p>
        </div>
      )}

      {/* Pipeline summary */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Input molecules', value: summary.total_input_molecules },
            { label: 'After ADMET filter', value: summary.after_admet_prefilter },
            { label: 'Successfully docked', value: summary.successfully_docked },
            { label: 'Top candidates', value: summary.top_candidates },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-center">
              <p className="text-2xl font-bold">{value ?? '—'}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Ranked candidates */}
      {candidates.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">SMILES</th>
                <th className="px-3 py-2 text-right">Affinity</th>
                <th className="px-3 py-2 text-right">Score</th>
                <th className="px-3 py-2 text-center">ADMET</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {candidates.map((c, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-3 py-2 font-medium">{(c.rank as number) || i + 1}</td>
                  <td className="px-3 py-2 font-mono text-xs max-w-[250px] truncate">{c.smiles as string}</td>
                  <td className="px-3 py-2 text-right">{((c.docking_affinity_kcal_mol as number) || 0).toFixed(1)}</td>
                  <td className="px-3 py-2 text-right font-medium">{((c.composite_score as number) || 0).toFixed(3)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`inline-block h-3 w-3 rounded-full ${
                      c.overall_flag === 'GREEN' ? 'bg-green-500' :
                      c.overall_flag === 'AMBER' ? 'bg-amber-500' :
                      c.overall_flag === 'RED' ? 'bg-red-500' : 'bg-gray-400'
                    }`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* No results */}
      {job.status === 'completed' && candidates.length === 0 && !pipelineError && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg font-medium">Pipeline completed with no ranked candidates</p>
          <p className="text-sm mt-1">This may be because docking tools were unavailable or all molecules were filtered out.</p>
        </div>
      )}

      {/* Raw input/output for debugging */}
      <details className="rounded-lg border border-gray-200 dark:border-gray-700">
        <summary className="px-4 py-2 text-sm text-gray-500 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
          Raw job data
        </summary>
        <div className="p-4 space-y-4">
          <div>
            <h3 className="text-xs font-medium text-gray-500 mb-1">Input</h3>
            <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded overflow-auto max-h-40">
              {JSON.stringify(job.input_data, null, 2)}
            </pre>
          </div>
          {job.output_data && (
            <div>
              <h3 className="text-xs font-medium text-gray-500 mb-1">Output</h3>
              <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded overflow-auto max-h-60">
                {JSON.stringify(job.output_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </details>
    </main>
  )
}
