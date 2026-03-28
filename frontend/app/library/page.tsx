'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface JobSummary {
  id: string
  status: string
  job_type: string
  input_data: Record<string, unknown>
  output_data: Record<string, unknown> | null
  created_at: string
}

const STATUS_BADGE: Record<string, string> = {
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  pending: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  cancelled: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300',
}

export default function LibraryPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const limit = 20

  useEffect(() => {
    setLoading(true)
    fetch(`${API_URL}/api/jobs/?limit=${limit}&offset=${page * limit}`)
      .then((r) => r.ok ? r.json() : { jobs: [], total: 0 })
      .then((data) => {
        setJobs(data.jobs || [])
        setTotal(data.total || 0)
      })
      .catch(() => setJobs([]))
      .finally(() => setLoading(false))
  }, [page])

  const totalPages = Math.ceil(total / limit)

  return (
    <main className="min-h-screen p-6 md:p-12 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Job History</h1>
          <p className="mt-1 text-sm text-gray-500">{total} experiment{total !== 1 ? 's' : ''}</p>
        </div>
        <Link href="/"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          New Pipeline
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 animate-pulse">
              <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-3 w-32 bg-gray-200 dark:bg-gray-700 rounded mt-2" />
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="h-16 w-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
            <svg className="h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <h2 className="text-lg font-medium text-gray-500">No experiments yet</h2>
          <p className="mt-1 text-sm text-gray-400">Your previous experiments will appear here</p>
          <Link href="/"
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Start your first pipeline
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id}
                className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{job.job_type}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[job.status] || STATUS_BADGE.pending}`}>
                      {job.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-mono truncate max-w-md">
                    {job.id}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>
                <Link href={`/jobs/${job.id}`}
                  className="text-sm text-blue-600 hover:underline shrink-0 ml-4">
                  View
                </Link>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
                className="rounded px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 disabled:opacity-40">
                Previous
              </button>
              <span className="px-3 py-1 text-sm text-gray-500">
                Page {page + 1} of {totalPages}
              </span>
              <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
                className="rounded px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 disabled:opacity-40">
                Next
              </button>
            </div>
          )}
        </>
      )}
    </main>
  )
}
