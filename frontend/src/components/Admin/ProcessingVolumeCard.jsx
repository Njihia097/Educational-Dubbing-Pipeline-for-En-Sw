// frontend/src/components/Admin/ProcessingVolumeCard.jsx

export default function ProcessingVolumeCard({ metrics }) {
  if (!metrics || !metrics.text_analytics) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Processing Volume</h3>
        <p className="text-xs text-slate-500">No data available. Process some videos to see volume metrics.</p>
      </div>
    )
  }
  
  // Check if we have any meaningful data
  const hasData = metrics.text_analytics.total_videos_processed > 0 || 
                  metrics.text_analytics.total_english_words > 0
  
  if (!hasData) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Processing Volume</h3>
        <p className="text-xs text-slate-500">No processing volume data available yet.</p>
      </div>
    )
  }

  const ta = metrics.text_analytics

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">Processing Volume</h3>
      
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-600">Total Videos</span>
            <span className="text-sm font-semibold text-slate-900">
              {ta.total_videos_processed || 0}
            </span>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-600">Total Words Processed</span>
            <span className="text-xs font-semibold text-slate-900">
              {(ta.total_english_words || 0).toLocaleString()}
            </span>
          </div>
          <p className="text-[10px] text-slate-500">
            English: {ta.total_english_words?.toLocaleString() || 0} | Swahili: {ta.total_swahili_words?.toLocaleString() || 0}
          </p>
        </div>

        <div className="pt-2 border-t border-slate-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700">Avg Words/Video</span>
            <span className="text-sm font-semibold text-slate-900">
              {ta.avg_words_per_video ? ta.avg_words_per_video.toFixed(0) : '—'}
            </span>
          </div>
        </div>

        {ta.avg_video_duration_seconds && (
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-600">Avg Video Duration</span>
              <span className="text-xs font-semibold text-slate-900">
                {formatDuration(ta.avg_video_duration_seconds)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function formatDuration(seconds) {
  if (!seconds) return '—'
  if (seconds < 60) return `${seconds.toFixed(0)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}m ${secs}s`
}

