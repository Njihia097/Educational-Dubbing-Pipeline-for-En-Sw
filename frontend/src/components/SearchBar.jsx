// frontend/src/components/SearchBar.jsx

export default function SearchBar({
  value,
  onChange,
  placeholder = 'Search…',
  children, // optional filters on the right
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-3">
      <div className="flex-1 max-w-xs">
        <div className="relative">
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
          />
          {value && (
            <button
              type="button"
              onClick={() => onChange('')}
              className="absolute right-2 top-1.5 text-[10px] text-slate-400 hover:text-slate-600"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}
