import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom' 
import { FilePlus2, ListChecks, Clock, CheckCircle2, Plus, Bot, User as UserIcon } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatCard } from '@/components/ui/StatCard'
import { IssueCard } from '@/components/ui/IssueCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { CardSkeleton } from '@/components/ui/Loading'
import { Alert } from '@/components/ui/Alert'
import { listIssues } from '@/api/issues'
import { useAuth } from '@/context/AuthContext'
import { extractErrorMessage } from '@/api/client'
import { formatDateTime, issueRef } from '@/lib/format'
import { getStudentActivityFeed, type NotificationEntry } from '@/lib/activityFeed'
import type { Issue } from '@/types'

export function StudentDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [issues, setIssues] = useState<Issue[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activity, setActivity] = useState<NotificationEntry[] | null>(null)

  useEffect(() => {
    let cancelled = false
    listIssues()
      .then((all) => {
        if (cancelled) return
        setIssues(all.filter((i) => i.student === user?.email))
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load your issues.')))
    return () => {
      cancelled = true
    }
  }, [user?.email])

  // Reuses the same fetch-and-flatten logic as the Notifications page
  // (lib/activityFeed.ts) -- this widget is just a 5-item preview of it,
  // not a separate implementation.
  useEffect(() => {
    let cancelled = false
    getStudentActivityFeed(user?.email).then((entries) => !cancelled && setActivity(entries))
    return () => {
      cancelled = true
    }
  }, [user?.email])

  const isLoading = issues === null
  const open = issues?.filter((i) => i.status === 'pending' || i.status === 'ready_for_review').length ?? 0
  const inProgress = issues?.filter((i) => i.status === 'in_progress').length ?? 0
  const resolved = issues?.filter((i) => i.status === 'resolved' || i.status === 'closed').length ?? 0
  const recent = [...(issues ?? [])].sort((a, b) => b.id - a.id).slice(0, 5)

  // Both widgets below reuse the exact issues[] already fetched above --
  // no new endpoint, no new fetch. "Awaiting Your Confirmation" is simply
  // every issue in the officer-resolved-but-not-yet-closed state (the same
  // status the IssueDetail page's ResolutionResponsePanel gates on).
  // "Awaiting Documents" is simply every issue the backend has already
  // flagged as incomplete (Issue.is_complete, already returned on the plain
  // list shape -- no per-issue detail fetch needed).
  const awaitingConfirmation = [...(issues ?? [])].filter((i) => i.status === 'resolved').sort((a, b) => b.id - a.id)
  const awaitingDocuments = [...(issues ?? [])].filter((i) => !i.is_complete).sort((a, b) => b.id - a.id)

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.first_name || user?.email}`}
        description="Here's what's happening with your submitted issues."
        actions={
          <Link
            to="/student/issues/new"
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            <Plus className="size-4" />
            Create Issue
          </Link>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={ListChecks}
            tone="blue"
            value={issues?.length ?? 0}
            label="Total Issues"
            onClick={() => navigate('/student/issues')}
          />

          <StatCard
            icon={Clock}
            tone="orange"
            value={open}
            label="Open / Under Review"
            onClick={() => navigate('/student/issues?status=open')}
          />

          <StatCard
            icon={FilePlus2}
            tone="purple"
            value={inProgress}
            label="In Progress"
            onClick={() => navigate('/student/issues?status=in_progress')}
          />

          <StatCard
            icon={CheckCircle2}
            tone="green"
            value={resolved}
            label="Resolved / Closed"
            onClick={() => navigate('/student/issues?status=resolved_closed')}
          />
        </div>
      )}

      {/* Action Required -- both sections always render (EmptyState when
          empty, skeleton while loading), per "every section must use
          EmptyState, no blank containers." */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">Awaiting Your Confirmation</h2>
          </div>
          <p className="mb-2 text-xs text-slate-400">
            An officer marked these resolved. Confirm to close them, or reject with an explanation.
          </p>

          {isLoading ? (
            <div className="space-y-2 pt-2">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : awaitingConfirmation.length === 0 ? (
            <EmptyState title="Nothing to confirm" description="Resolved issues awaiting your review will show up here." />
          ) : (
            <div className="divide-y divide-slate-50">
              {awaitingConfirmation.map((issue) => (
                <IssueCard
                  key={issue.id}
                  issue={issue}
                  to={`/student/issues/${issue.id}`}
                  actionLabel="Review Resolution"
                  showCategory
                />
              ))}
            </div>
          )}
        </div>

        <div className="card p-5">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">Awaiting Documents</h2>
          </div>
          <p className="mb-2 text-xs text-slate-400">
            These issues are still missing one or more required documents.
          </p>

          {isLoading ? (
            <div className="space-y-2 pt-2">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : awaitingDocuments.length === 0 ? (
            <EmptyState title="Nothing outstanding" description="Issues missing required documents will show up here." />
          ) : (
            <div className="divide-y divide-slate-50">
              {awaitingDocuments.map((issue) => (
                <IssueCard
                  key={issue.id}
                  issue={issue}
                  to={`/student/issues/${issue.id}/documents`}
                  actionLabel="Upload Documents"
                  showCategory
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card mt-6 p-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Recent Issues</h2>
          <Link to="/student/issues" className="text-xs font-semibold text-brand-600 hover:text-brand-700">
            View all
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-2 pt-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <EmptyState
            title="No issues yet"
            description="Create your first issue to get started."
            action={
              <Link
                to="/student/issues/new"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Create Issue
              </Link>
            }
          />
        ) : (
          <div className="divide-y divide-slate-50">
            {recent.map((issue) => (
              <IssueCard key={issue.id} issue={issue} to={`/student/issues/${issue.id}`} />
            ))}
          </div>
        )}
      </div>

      <div className="card mt-6 p-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Recent Activity</h2>
          <Link to="/student/notifications" className="text-xs font-semibold text-brand-600 hover:text-brand-700">
            View all notifications
          </Link>
        </div>

        {activity === null ? (
          <div className="space-y-2 pt-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        ) : activity.length === 0 ? (
          <EmptyState title="No activity yet" description="Updates on your issues will show up here." />
        ) : (
          <ul className="divide-y divide-slate-50">
            {activity.slice(0, 5).map((entry) => (
              <li key={`${entry.issueId}-${entry.id}`}>
                <Link
                  to={`/student/issues/${entry.issueId}`}
                  className="flex gap-3 rounded-lg px-1 py-2.5 transition-colors hover:bg-slate-50"
                >
                  <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-100">
                    {entry.is_system_action ? (
                      <Bot className="size-3.5 text-slate-500" />
                    ) : (
                      <UserIcon className="size-3.5 text-slate-500" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800">{entry.action}</p>
                    <p className="truncate text-xs text-slate-400">
                      {entry.issueTitle} · {issueRef(entry.issueId)} · {formatDateTime(entry.created_at)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
