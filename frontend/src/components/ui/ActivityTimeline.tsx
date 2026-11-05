import { Bot, User } from 'lucide-react'
import type { IssueActivityRecord } from '@/types'
import { formatDateTime } from '@/lib/format'
import { EmptyState } from './EmptyState'

export function ActivityTimeline({ activities }: { activities: IssueActivityRecord[] }) {
  if (activities.length === 0) {
    return <EmptyState title="No activity yet" description="Actions on this issue will show up here." />
  }

  const sorted = [...activities].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )

  return (
    <ul className="space-y-4">
      {sorted.map((activity) => (
        <li key={activity.id} className="flex gap-3">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-100">
            {activity.is_system_action ? (
              <Bot className="size-3.5 text-slate-500" />
            ) : (
              <User className="size-3.5 text-slate-500" />
            )}
          </div>
          <div className="min-w-0 flex-1 border-b border-slate-100 pb-4 last:border-0 last:pb-0">
            <p className="text-sm font-medium text-slate-800">{activity.action}</p>
            <p className="text-xs text-slate-400">
              {activity.is_system_action ? 'System' : (activity.performed_by ?? 'Unknown')} ·{' '}
              {formatDateTime(activity.created_at)}
            </p>
            {activity.notes && <p className="mt-1 text-sm text-slate-600">{activity.notes}</p>}
          </div>
        </li>
      ))}
    </ul>
  )
}
