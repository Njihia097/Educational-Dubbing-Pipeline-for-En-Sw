// frontend/src/components/JobStatusPanel.jsx
import { useEffect, useState } from 'react'
import useJobStatus from '../hooks/useJobStatus'

export default function JobStatusPanel({ jobId }) {
  const { status, loading, error } = useJobStatus(jobId, { pollIntervalMs: 2500 })

  if (!jobId) return null

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-900">
          Pipeline status
        </h3>
        <span className="text-xs font-mono text-slate-500">
          Job: {jobId.slice(0, 8)}…
        </span>
      </div>

      {loading && !status && (
        <p className="text-sm text-slate-500">Fetching job status…</p>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700 mb-3">
          {error}
        </div>
      )}

      {status && (
        <>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm">
              <span className="font-medium text-slate-700">State:&nbsp;</span>
              <span className="font-mono text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-800">
                {status.state}
              </span>
            </div>
            <div className="text-xs text-slate-500">
              Progress: {status.progress != null ? `${status.progress}%` : '—'}
            </div>
          </div>

          {/* Simple linear progress – backend sets job.progress if available */}
          {status.progress != null && (
            <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden mb-3">
              <div
                className="h-full bg-sky-500 transition-all"
                style={{ width: `${Math.min(100, Math.max(0, status.progress))}%` }}
              />
            </div>
          )}

          {/* Steps list */}
          <div className="mt-2">
            <p className="text-xs font-medium text-slate-500 mb-1">
              Steps
            </p>
            <ul className="space-y-1">
              {status.steps?.map((step) => (
                <li
                  key={step.name}
                  className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-1.5 text-xs"
                >
                  <span className="font-mono text-[11px] text-slate-700">
                    {step.name}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {step.state}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Placeholder for later: download links, original vs dubbed player, etc. */}
        </>
      )}
    </div>
  )
}
