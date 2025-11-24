// frontend/src/components/PipelineTracker.jsx
import React, { useMemo } from 'react'

const CANONICAL_STEPS = [
  'asr',
  'punctuate',
  'translate',
  'tts',
  'separate_music',
  'mix',
  'replace_audio',
]

function fallbackStepProgress(state) {
  switch ((state || '').toLowerCase()) {
    case 'succeeded':
    case 'completed':
      return 100
    case 'running':
      return 50
    case 'queued':
    case 'pending':
      return 0
    case 'failed':
    case 'error':
      return 0
    default:
      return 0
  }
}

/**
 * Option A aware overall progress:
 *  - Prefer job.progress or job.meta.progress (if backend ever sets them)
 *  - Otherwise derive a coarse % from job.state for a single /full chain
 *  - Only fall back to per-step averaging if job.state is missing
 */
function deriveOverallProgress(job, steps) {
  if (!job) return null

  // 1) Explicit numeric progress from backend (future proof)
  if (typeof job.progress === 'number') {
    return Math.round(job.progress)
  }
  if (typeof job.meta?.progress === 'number') {
    return Math.round(job.meta.progress)
  }

  // 2) Full-chain coarse mapping from job.state
  const st = (job.state || '').toLowerCase()
  if (['queued', 'pending'].includes(st)) return 0
  if (st === 'running') return 50
  if (['completed', 'succeeded'].includes(st)) return 100
  if (['failed', 'cancelled', 'error'].includes(st)) return 100

  // 3) Fallback: average step progress (legacy, just in case)
  if (!steps.length) return null

  const values = steps.map((s) =>
    typeof s.progress === 'number' ? s.progress : fallbackStepProgress(s.state)
  )
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length)
}

function resolveActiveStep(job, orderedSteps) {
  if (!job) return null
  if (job.current_step) return job.current_step

  const running = orderedSteps.find((s) => s.state === 'running')
  if (running) return running.name

  for (let i = orderedSteps.length - 1; i >= 0; i--) {
    if (['succeeded', 'completed'].includes(orderedSteps[i].state)) {
      return orderedSteps[i].name
    }
  }
  return null
}

export default function PipelineTracker({
  job,
  loading,
  error,
  onRetry,
}) {
  const orderedSteps = useMemo(() => {
    if (!job || !Array.isArray(job.steps)) return []

    // Map actual JobStep rows by name
    const map = new Map()
    job.steps.forEach((s) => s?.name && map.set(s.name, s))

    // Ensure we always render the canonical logical stages
    return CANONICAL_STEPS.map((name) =>
      map.get(name) || {
        name,
        state: 'pending',
        progress: null,
        started_at: null,
        finished_at: null,
      }
    )
  }, [job])

  const overallProgress = deriveOverallProgress(job, orderedSteps)
  const activeStep = resolveActiveStep(job, orderedSteps)

  const isTerminal =
    job && ['completed', 'succeeded', 'failed', 'cancelled'].includes(job.state)

  const isFailed = job && job.state === 'failed'

  if (!job && loading) {
    return <p className="text-sm text-slate-500">Fetching job status…</p>
  }

  if (!job && error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
        {error}
      </div>
    )
  }

  if (!job) return null

  return (
    <div className="space-y-3">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="text-sm flex items-center gap-2">
          <span className="font-medium text-slate-700">
            Full chain state:
          </span>
          <span className="font-mono text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-800">
            {job.state}
          </span>

          {job.retry_count > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
              retries: {job.retry_count}
            </span>
          )}
        </div>

        <div className="text-xs text-slate-500">
          Full chain progress:{' '}
          {typeof overallProgress === 'number' ? `${overallProgress}%` : '—'}
        </div>
      </div>

      {/* Full-chain Progress bar */}
      {typeof overallProgress === 'number' && (
        <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full bg-sky-500 transition-all"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      )}

      {/* Terminal state summary */}
      {isTerminal && (
        <div
          className={`rounded-lg border px-3 py-2 text-xs ${
            isFailed
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-emerald-50 border-emerald-200 text-emerald-800'
          }`}
        >
          {isFailed ? (
            <div className="flex items-center justify-between gap-2">
              <div className="flex flex-col">
                <span className="font-medium">Pipeline failed.</span>
                {job.last_error_message && (
                  <span className="text-[11px] text-red-700 mt-1">
                    {job.last_error_message}
                  </span>
                )}
              </div>

              {typeof onRetry === 'function' && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="rounded-md bg-amber-500 text-white px-2 py-1 text-[11px] hover:bg-amber-600 transition"
                >
                  Retry Job
                </button>
              )}
            </div>
          ) : (
            <span>Full chain completed successfully.</span>
          )}
        </div>
      )}

      {/* Logical steps list (visual only in Option A) */}
      <div>
        <p className="text-xs font-medium text-slate-500 mb-1">
          Logical pipeline stages
        </p>
        <ul className="space-y-1.5">
          {orderedSteps.map((step) => {
            const stepProgress =
              typeof step.progress === 'number'
                ? step.progress
                : fallbackStepProgress(step.state)

            const isActive = activeStep === step.name

            return (
              <li
                key={step.name}
                className={`flex items-center justify-between rounded-lg border px-3 py-1.5 text-xs ${
                  isActive ? 'border-sky-300 bg-sky-50' : 'border-slate-100 bg-white'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px]">{step.name}</span>
                  {isActive && (
                    <span className="text-[10px] text-sky-700 uppercase">
                      ACTIVE
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500">
                    {step.state}
                  </span>
                  <div className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full bg-sky-400"
                      style={{ width: `${stepProgress}%` }}
                    />
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
