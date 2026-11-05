import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import type { Issue } from '@/types'

/**
 * `actionLabel` is optional and purely cosmetic -- when provided, it renders
 * as a small pill next to the status badge (e.g. "Review Resolution",
 * "Upload Documents") to make the card's destination explicit on dashboard
 * widgets that link somewhere more specific than the issue detail page.
 * The entire row is still a single <Link> (unchanged); this does not add a
 * second interactive/clickable element, just a label.
 *
 * `showCategory` is also optional -- when true, the category name is
 * appended to the reference line (e.g. "Missing Result · #ISSUE-0004").
 * Every existing call site that omits both props renders exactly as before.
 */
export function IssueCard({
  issue,
  to,
  actionLabel,
  showCategory,
}: {
  issue: Issue
  to: string
  actionLabel?: string
  showCategory?: boolean
}) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-4 rounded-xl px-3 py-3 transition-colors hover:bg-slate-50"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-slate-800">{issue.title}</p>
        <p className="truncate text-xs text-slate-400">
          {showCategory && <>{issue.category} · </>}#ISSUE-{String(issue.id).padStart(4, '0')}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <StatusBadge status={issue.status} />
        {actionLabel && (
          <span className="whitespace-nowrap rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700">
            {actionLabel}
          </span>
        )}
        <ChevronRight className="size-4 text-slate-300" />
      </div>
    </Link>
  )
}
