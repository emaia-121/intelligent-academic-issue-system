import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom' 
import { Inbox, Clock, CheckCircle2, ListChecks } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatCard } from '@/components/ui/StatCard'
import { IssueCard } from '@/components/ui/IssueCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { CardSkeleton } from '@/components/ui/Loading'
import { Alert } from '@/components/ui/Alert'
import { IssuesByStatusChart } from '@/components/charts/IssuesByStatusChart'
import { listIssues } from '@/api/issues'
import { computeStatusCounts } from '@/api/mock/reports'
import { useAuth } from '@/context/AuthContext'
import { extractErrorMessage } from '@/api/client'
import { ROLE_WORKLOAD_CONFIG, type StaffRole } from '@/lib/roleWorkloadConfig'
import type { Issue } from '@/types'

/**
 * One Staff Dashboard component, made role-aware internally -- not eleven
 * separate dashboards. `user.role` (the real Role, not just RoleGroup)
 * selects a RoleWorkloadConfig (lib/roleWorkloadConfig.ts, a mirror of
 * issues/workflow/definitions.py) that drives the title, which categories
 * this dashboard cares about, and the empty-state wording. The underlying
 * data source, permissions, and workflow behavior are unchanged: this is
 * still just GET /api/issues/, still filtered client-side.
 */
export function StaffDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate() 
  const [issues, setIssues] = useState<Issue[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Falls back to an unfiltered, generically-labeled view if `user.role`
  // somehow isn't one of the 11 configured staff roles (shouldn't happen --
  // RoleRoute already restricts this page to RoleGroup 'staff' -- but this
  // keeps the dashboard from ever rendering blank instead of degrading
  // gracefully to the old generic behavior).
  const config = user ? ROLE_WORKLOAD_CONFIG[user.role as StaffRole] : undefined

  useEffect(() => {
    let cancelled = false
    listIssues()
      .then((all) => {
        if (cancelled) return
        const mine = all.filter((i) => i.assigned_to === user?.email)
        setIssues(config ? mine.filter((i) => config.categories.includes(i.category)) : mine)
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load assigned issues.')))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.email, user?.role])

  const isLoading = issues === null
  const awaitingReview = issues?.filter((i) => i.status === 'ready_for_review').length ?? 0
  const inProgress = issues?.filter((i) => i.status === 'in_progress').length ?? 0
  const resolved = issues?.filter((i) => i.status === 'resolved' || i.status === 'closed').length ?? 0
  const queue = [...(issues ?? [])]
    .filter((i) => i.status !== 'resolved' && i.status !== 'closed')
    .sort((a, b) => a.id - b.id)
    .slice(0, 6)

  // Only worth showing when this role's work actually spans more than one
  // category (e.g. Course Adviser, Exams Officer) -- for single-category
  // roles (ICT Officer, Registry, ...) it would just repeat the "Assigned
  // to Me" stat card.
  const byCategory = useMemo(() => {
    if (!config || config.categories.length < 2 || !issues) return []
    return config.categories
      .map((category) => ({
        category,
        active: issues.filter((i) => i.category === category && i.status !== 'resolved' && i.status !== 'closed')
          .length,
      }))
      .filter((row) => row.active > 0)
  }, [config, issues])

  // computeStatusCounts() is the same pure counter getAdminOverview() uses
  // for the system-wide chart on the Admin Dashboard -- called here on
  // `issues`, which is already scoped to assigned_to === this officer (see
  // the fetch above), so this chart only ever reflects this officer's own
  // workload, never system-wide statistics.
  const statusCounts = useMemo(() => computeStatusCounts(issues ?? []), [issues])

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.first_name || user?.email}`}
        description={config ? config.title : "Here's your assigned workload."}
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
            label="Assigned to Me"
            onClick={() => navigate('/staff/issues?assignment=mine')}
          />
          <StatCard
            icon={Clock}
            tone="orange"
            value={awaitingReview}
            label="Awaiting Review"
            onClick={() => navigate('/staff/issues?status=ready_for_review')}
          />
          <StatCard
            icon={Inbox}
            tone="purple"
            value={inProgress}
            label="In Progress"
            onClick={() => navigate('/staff/issues?status=in_progress')}
          />
          <StatCard
            icon={CheckCircle2}
            tone="green"
            value={resolved}
            label="Resolved / Closed"
            onClick={() => navigate('/staff/issues?status=resolved_closed')}
          />
        </div>
      )}

      {!isLoading && byCategory.length > 0 && (
        <div className="card mt-6 p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-800">By Category</h2>
          <div className="divide-y divide-slate-50">
            {byCategory.map((row) => (
              <div key={row.category} className="flex items-center justify-between py-2.5 text-sm">
                <span className="font-medium text-slate-700">{row.category}</span>
                <span className="font-semibold text-slate-800">{row.active}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card mt-6 p-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Active Queue</h2>
          <Link to="/staff/issues" className="text-xs font-semibold text-brand-600 hover:text-brand-700">
            View all assigned
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-2 pt-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        ) : queue.length === 0 ? (
          <EmptyState
            title="Queue is clear"
            description={config ? config.emptyMessage : 'Nothing assigned to you needs attention right now.'}
          />
        ) : (
          <div className="divide-y divide-slate-50">
            {queue.map((issue) => (
              <IssueCard key={issue.id} issue={issue} to={`/staff/issues/${issue.id}`} />
            ))}
          </div>
        )}
      </div>

      <div className="card mt-6 p-5">
        <h2 className="mb-1 text-sm font-semibold text-slate-800">Your Workload</h2>
        <p className="mb-3 text-xs text-slate-400">
          Status breakdown of issues currently assigned to you -- not a system-wide statistic.
        </p>

        {isLoading ? (
          <div className="h-64 animate-pulse rounded-lg bg-slate-100" />
        ) : (issues?.length ?? 0) === 0 ? (
          <EmptyState title="Nothing assigned yet" description="Your workload chart will appear once issues are assigned to you." />
        ) : (
          <IssuesByStatusChart counts={statusCounts} height={220} />
        )}
      </div>
    </div>
  )
}
