import { ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

export function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number
  totalPages: number
  onChange: (page: number) => void
}) {
  if (totalPages <= 1) return null

  return (
    <div className="mt-4 flex items-center justify-between text-sm">
      <p className="text-slate-400">
        Page {page} of {totalPages}
      </p>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className={clsx(
            'flex size-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors',
            page <= 1 ? 'opacity-40' : 'hover:bg-slate-50',
          )}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" />
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className={clsx(
            'flex size-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors',
            page >= totalPages ? 'opacity-40' : 'hover:bg-slate-50',
          )}
          aria-label="Next page"
        >
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  )
}
