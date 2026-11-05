import { ISSUE_STATUS_LABELS, type IssueStatus } from '@/types'
import clsx from 'clsx'

const STYLES: Record<IssueStatus, string> = {
  pending: 'bg-slate-100 text-slate-600',
  ready_for_review: 'bg-blue-50 text-blue-600',
  in_progress: 'bg-orange-50 text-orange-700',
  resolved: 'bg-emerald-50 text-emerald-700',
  closed: 'bg-slate-100 text-slate-500',
}

export function StatusBadge({ status, className }: { status: IssueStatus; className?: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold',
        STYLES[status],
        className,
      )}
    >
      {ISSUE_STATUS_LABELS[status]}
    </span>
  )
}

const PRIORITY_STYLES: Record<'Low' | 'Medium' | 'High', string> = {
  Low: 'text-slate-500',
  Medium: 'text-amber-600',
  High: 'text-red-600',
}

/**
 * Priority appears in the reference design's staff tables, but the backend's
 * Issue model has no priority field -- there is nothing to bind this to yet.
 * Exported for later use; not wired into any real data anywhere in this app.
 */
export function PriorityDot({ level }: { level: 'Low' | 'Medium' | 'High' }) {
  return (
    <span className={clsx('inline-flex items-center gap-1.5 text-sm font-medium', PRIORITY_STYLES[level])}>
      <span className="size-1.5 rounded-full bg-current" />
      {level}
    </span>
  )
}

/** Placeholder for reference-design fields the backend doesn't track yet (e.g. issue priority). */
export function NotTracked({ label }: { label?: string }) {
  return (
    <span className="text-sm text-slate-400" title={label ?? 'Not tracked by the backend yet'}>
      —
    </span>
  )
}
