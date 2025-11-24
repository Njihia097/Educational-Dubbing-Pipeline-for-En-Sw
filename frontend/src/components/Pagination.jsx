// frontend/src/components/Pagination.jsx

export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  compact = false,
}) {
  const currentPage = page || 1
  const size = pageSize || 20
  const totalItems = total || 0
  const totalPages = Math.max(1, Math.ceil(totalItems / size))

  const canPrev = currentPage > 1
  const canNext = currentPage < totalPages

  if (totalPages <= 1 && totalItems <= size) {
    return null
  }

  return (
    <div className="flex items-center justify-between text-[11px] text-slate-600 mt-3">
      {!compact && (
        <div>
          Showing{' '}
          <span className="font-medium">
            {(currentPage - 1) * size + 1}
          </span>{' '}
          –{' '}
          <span className="font-medium">
            {Math.min(currentPage * size, totalItems)}
          </span>{' '}
          of <span className="font-medium">{totalItems}</span> jobs
        </div>
      )}

      <div className="flex items-center gap-2 ml-auto">
        <button
          type="button"
          disabled={!canPrev}
          onClick={() => canPrev && onPageChange(currentPage - 1)}
          className="px-2 py-1 rounded-md border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50"
        >
          Prev
        </button>
        <span className="px-2">
          Page <span className="font-semibold">{currentPage}</span> of{' '}
          <span className="font-semibold">{totalPages}</span>
        </span>
        <button
          type="button"
          disabled={!canNext}
          onClick={() => canNext && onPageChange(currentPage + 1)}
          className="px-2 py-1 rounded-md border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}
