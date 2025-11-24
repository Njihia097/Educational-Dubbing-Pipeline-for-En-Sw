// frontend/src/components/Admin/TextAnalyticsCard.jsx

export default function TextAnalyticsCard({ analytics }) {
  if (!analytics) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Text Analytics</h3>
        <p className="text-xs text-slate-500">No data available. Process some videos to see analytics.</p>
      </div>
    )
  }
  
  // Check if we have any data to display
  const hasData = analytics.english_word_count || analytics.swahili_word_count || 
                  analytics.translation_ratio || analytics.segment_count
  
  if (!hasData) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Text Analytics</h3>
        <p className="text-xs text-slate-500">No text analytics data available yet.</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">Text Analytics</h3>
      
      <div className="space-y-3">
        {analytics.english_word_count && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-600">English Words</span>
              <span className="text-xs font-semibold text-slate-900">
                {analytics.english_word_count.total?.toLocaleString() || 0}
              </span>
            </div>
            {analytics.english_word_count.avg && (
              <p className="text-[10px] text-slate-500">
                Avg: {analytics.english_word_count.avg.toFixed(0)} per video
              </p>
            )}
          </div>
        )}

        {analytics.swahili_word_count && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-600">Swahili Words</span>
              <span className="text-xs font-semibold text-slate-900">
                {analytics.swahili_word_count.total?.toLocaleString() || 0}
              </span>
            </div>
            {analytics.swahili_word_count.avg && (
              <p className="text-[10px] text-slate-500">
                Avg: {analytics.swahili_word_count.avg.toFixed(0)} per video
              </p>
            )}
          </div>
        )}

        {analytics.translation_ratio && (
          <div className="pt-2 border-t border-slate-200">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-700">Translation Ratio</span>
              <span className="text-xs font-semibold text-slate-900">
                {analytics.translation_ratio.avg ? analytics.translation_ratio.avg.toFixed(2) : '—'}
              </span>
            </div>
            <p className="text-[10px] text-slate-500">
              Swahili/English word ratio
            </p>
          </div>
        )}

        {analytics.segment_count && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-600">Avg Segments</span>
              <span className="text-xs font-semibold text-slate-900">
                {analytics.segment_count.avg ? analytics.segment_count.avg.toFixed(1) : '—'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

