import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, Bot, User } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageLoader } from '@/components/ui/Loading'
import { Alert } from '@/components/ui/Alert'
import { useAuth } from '@/context/AuthContext'
import { extractErrorMessage } from '@/api/client'
import { formatDateTime, issueRef } from '@/lib/format'
import { getStudentActivityFeed, type NotificationEntry } from '@/lib/activityFeed'

/**
 * There is no notifications endpoint on the backend -- see
 * lib/activityFeed.ts, which this screen (and the Student Dashboard's
 * "Recent Activity" widget) both build on top of.
 */
export function Notifications() {
  const { user } = useAuth()
  const [entries, setEntries] = useState<NotificationEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    getStudentActivityFeed(user?.email)
      .then((flattened) => !cancelled && setEntries(flattened))
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load notifications.')))

    return () => {
      cancelled = true
    }
  }, [user?.email])

  const grouped = useMemo(() => entries ?? [], [entries])

  if (error) {
    return (
      <div className="mx-auto max-w-2xl">
        <Alert variant="error">{error}</Alert>
      </div>
    )
  }

  if (!entries) return <PageLoader label="Loading notifications…" />

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Notifications" description="Updates from all of your submitted issues." />

      {grouped.length === 0 ? (
        <EmptyState icon={Bell} title="No activity yet" description="Updates on your issues will show up here." />
      ) : (
        <ul className="card divide-y divide-slate-50 p-2">
          {grouped.map((entry) => (
            <li key={`${entry.issueId}-${entry.id}`}>
              <Link
                to={`/student/issues/${entry.issueId}`}
                className="flex gap-3 rounded-lg px-3 py-3.5 transition-colors hover:bg-slate-50"
              >
                <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-100">
                  {entry.is_system_action ? (
                    <Bot className="size-4 text-slate-500" />
                  ) : (
                    <User className="size-4 text-slate-500" />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800">{entry.action}</p>
                  <p className="truncate text-xs text-slate-400">
                    {entry.issueTitle} · {issueRef(entry.issueId)}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-400">{formatDateTime(entry.created_at)}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
