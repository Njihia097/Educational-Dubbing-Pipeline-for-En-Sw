// frontend/src/components/TranscriptViewer.jsx
import { useEffect, useRef, useState } from 'react'

function formatTime(seconds) {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = (seconds % 60).toFixed(3)
  return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.padStart(6, '0')}`
}

function calculateCPS(text, duration) {
  if (!duration || duration <= 0) return 0
  return Math.round(text.length / duration)
}

export default function TranscriptViewer({
  englishSegments = [],
  swahiliSegments = [],
  currentTime = 0,
  onSegmentClick,
  hideOriginal = false,
  autoScroll = true,
  onHideOriginalChange,
  onAutoScrollChange,
}) {
  const containerRef = useRef(null)
  const activeSegmentRef = useRef(null)

  // Find active segment based on current time
  const activeIndex = swahiliSegments.findIndex(
    (seg) => currentTime >= seg.start && currentTime < seg.end
  )

  // Auto-scroll to active segment
  useEffect(() => {
    if (!autoScroll || activeIndex === -1 || !activeSegmentRef.current) return

    const element = activeSegmentRef.current
    const container = containerRef.current
    if (!container) return

    const containerRect = container.getBoundingClientRect()
    const elementRect = element.getBoundingClientRect()

    // Check if element is outside viewport
    if (
      elementRect.top < containerRect.top ||
      elementRect.bottom > containerRect.bottom
    ) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [activeIndex, autoScroll])

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-white">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-700">Swahili</span>
          {/* <span className="text-xs">🇰🇪</span> */}
          <button className="text-slate-400 hover:text-slate-600">
            {/* <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg> */}
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1 text-xs rounded-md bg-yellow-500 text-white hover:bg-yellow-600">
            Synced-Transcripts
          </button>
        </div>
      </div>

      {/* Transcript List */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {swahiliSegments.length === 0 ? (
          <div className="text-center text-slate-400 text-sm py-8">
            No transcripts available yet
          </div>
        ) : (
          swahiliSegments.map((swSeg, index) => {
            const enSeg = englishSegments[index] || {}
            const isActive = index === activeIndex
            const duration = swSeg.end - swSeg.start
            const cps = calculateCPS(swSeg.text, duration)

            return (
              <div
                key={index}
                ref={isActive ? activeSegmentRef : null}
                onClick={() => onSegmentClick?.(swSeg.start)}
                className={`
                  p-3 rounded-lg border cursor-pointer transition-all
                  ${
                    isActive
                      ? 'bg-yellow-50 border-yellow-300 shadow-sm'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }
                `}
              >
                {/* Segment Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      className="w-4 h-4 text-yellow-600 rounded border-slate-300"
                    />
                    <span className="text-xs font-medium text-slate-600">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    {/* <span className="text-xs text-slate-500">Rafiki</span> */}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">{cps} CPS</span>
                    <span className="text-xs text-slate-500 font-mono">
                      {formatTime(swSeg.start)} - {formatTime(swSeg.end)}
                    </span>
                    {/* <span className="px-1.5 py-0.5 text-[10px] rounded bg-blue-100 text-blue-700">
                      AI
                    </span> */}
                  </div>
                </div>

                {/* English Text (if not hidden) */}
                {!hideOriginal && enSeg.text && (
                  <div className="mb-2 px-2 py-1.5 rounded bg-blue-50/50 border border-blue-100 text-sm text-slate-700">
                    {enSeg.text}
                  </div>
                )}

                {/* Swahili Text */}
                <div className="flex items-start justify-between gap-2">
                  <p
                    className={`text-sm flex-1 px-2 py-1.5 rounded ${
                      isActive
                        ? 'bg-yellow-100 text-slate-900 font-medium border border-yellow-200'
                        : 'bg-emerald-50/50 text-slate-800 border border-emerald-100'
                    }`}
                  >
                    {swSeg.text}
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onSegmentClick?.(swSeg.start)
                    }}
                    className="text-slate-400 hover:text-slate-600 p-1"
                    title="Play segment"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                    </svg>
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Footer Controls */}
      <div className="p-3 border-t border-slate-200 bg-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => onAutoScrollChange?.(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300"
              />
              Auto-Scroll
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={hideOriginal}
                onChange={(e) => onHideOriginalChange?.(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300"
              />
              Hide Original
            </label>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50">
              Undo
            </button>
            <button className="px-3 py-1 text-xs rounded border border-slate-300 text-slate-700 hover:bg-slate-50">
              Redo
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

