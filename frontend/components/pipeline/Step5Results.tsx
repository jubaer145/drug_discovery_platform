'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { RankedCandidate, PipelineResult } from '@/lib/types'

const FLAG_COLORS = { GREEN: 'bg-green-500', AMBER: 'bg-amber-500', RED: 'bg-red-500' }

interface Props {
  jobId: string
  onViewPose: (candidate: RankedCandidate) => void
}

export default function Step5Results({ jobId, onViewPose }: Props) {
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)

  useEffect(() => {
    api.jobs.get(jobId).then((job) => {
      if (job.output_data) {
        setResult(job.output_data as unknown as PipelineResult)
      }
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [jobId])

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-lg bg-gray-200 dark:bg-gray-800 h-16" />
          ))}
        </div>
        <div className="rounded-lg bg-gray-200 dark:bg-gray-800 h-64" />
      </div>
    )
  }

  if (!result || !result.pipeline_summary) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
        <div className="h-16 w-16 rounded-full bg-amber-100 dark:bg-amber-900 flex items-center justify-center">
          <svg className="h-8 w-8 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
          </svg>
        </div>
        <h2 className="text-lg font-medium">No docking results</h2>
        <p className="text-sm text-gray-500 max-w-md">
          No molecules achieved sufficient binding affinity. This can happen when docking tools
          are not available or all molecules were filtered out.
        </p>
        <div className="text-sm text-gray-400 space-y-1">
          <p>Try:</p>
          <ul className="list-disc list-inside">
            <li>Using broader ADMET filters</li>
            <li>Adding more diverse molecules</li>
            <li>Selecting a different target binding region</li>
          </ul>
        </div>
      </div>
    )
  }

  const summary = result.pipeline_summary

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Input', value: summary.total_input_molecules },
          { label: 'After ADMET filter', value: summary.after_admet_prefilter },
          { label: 'Docked', value: summary.successfully_docked },
          { label: 'Top candidates', value: summary.top_candidates },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-center">
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Results table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">SMILES</th>
              <th className="px-3 py-2 text-right">Affinity</th>
              <th className="px-3 py-2 text-right">Score</th>
              <th className="px-3 py-2 text-center">ADMET</th>
              <th className="px-3 py-2 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {result.ranked_candidates.map((c) => (
              <>
                <tr key={c.rank} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"
                  onClick={() => setExpanded(expanded === c.rank ? null : c.rank)}>
                  <td className="px-3 py-2 font-medium">{c.rank}</td>
                  <td className="px-3 py-2 font-mono text-xs max-w-[200px] truncate">{c.smiles}</td>
                  <td className="px-3 py-2 text-right">{c.docking_affinity_kcal_mol.toFixed(1)}</td>
                  <td className="px-3 py-2 text-right font-medium">{c.composite_score.toFixed(3)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`inline-block h-3 w-3 rounded-full ${FLAG_COLORS[c.overall_flag] || 'bg-gray-400'}`} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button onClick={(e) => { e.stopPropagation(); onViewPose(c) }}
                      className="text-blue-600 hover:underline text-xs">View 3D</button>
                  </td>
                </tr>
                {expanded === c.rank && c.admet?.tier1 && (
                  <tr key={`${c.rank}-detail`}>
                    <td colSpan={6} className="px-4 py-3 bg-gray-50 dark:bg-gray-900">
                      <div className="grid grid-cols-4 gap-3 text-xs">
                        <div>MW: {c.admet.tier1.mw}</div>
                        <div>LogP: {c.admet.tier1.logp}</div>
                        <div>HBD: {c.admet.tier1.hbd}</div>
                        <div>HBA: {c.admet.tier1.hba}</div>
                        <div>TPSA: {c.admet.tier1.tpsa}</div>
                        <div>QED: {c.admet.tier1.qed}</div>
                        <div>SA: {c.admet.tier1.sa_score}</div>
                        <div>Lipinski: {c.admet.tier1.lipinski_pass ? 'Pass' : 'Fail'}</div>
                      </div>
                      {c.admet.flags && c.admet.flags.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {c.admet.flags.map((f, i) => (
                            <p key={i} className={`text-xs ${f.type === 'warning' ? 'text-amber-600' : 'text-blue-500'}`}>
                              {f.type === 'warning' ? '\u26A0' : '\u2139'} {f.message}
                            </p>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
