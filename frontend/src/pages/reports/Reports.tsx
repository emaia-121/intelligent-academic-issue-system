import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ListChecks, FolderOpen, CheckCircle2, Clock } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatCard } from '@/components/ui/StatCard'
import { CardSkeleton } from '@/components/ui/Loading'
import { Alert } from '@/components/ui/Alert'
import { IssuesByStatusChart } from '@/components/charts/IssuesByStatusChart'
import { getAdminOverview, getDepartmentSummaries, getIssueTrend } from '@/api/mock/reports'
import { extractErrorMessage } from '@/api/client'
import type { AdminOverviewStats, DepartmentSummary, IssueTrendPoint } from '@/types'
import { useLocation, useNavigate } from 'react-router-dom' 

/**
 * Shared analytics view (used by both /staff/reports and /admin/reports).
 * The status breakdown, trend line, and department summaries below are all
 * computed from the real /api/issues/ response -- see src/api/mock/reports.ts
 * for exactly which numbers are real vs. mock-store-derived.
 */
export function Reports() {
  const [overview, setOverview] = useState<AdminOverviewStats | null>(null)
  const [trend, setTrend] = useState<IssueTrendPoint[] | null>(null)
  const [departments, setDepartments] = useState<DepartmentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const navigate = useNavigate()
  const location = useLocation()

  const issuesPath = location.pathname.startsWith('/admin/')
    ? '/admin/issues'
    : '/staff/issues'

  useEffect(() => {
    let cancelled = false
    Promise.all([getAdminOverview(), getIssueTrend(), getDepartmentSummaries()])
      .then(([o, t, d]) => {
        if (cancelled) return
        setOverview(o)
        setTrend(t)
        setDepartments(d)
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load reports.')))
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return <Alert variant="error">{error}</Alert>
  }

  const isLoading = !overview || !trend || !departments

  return (
    <div>
      <PageHeader title="Reports" description="Issue volume, resolution trends, and department performance." />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={ListChecks} tone="blue" value={overview.total_issues} label="Total Issues" onClick={() => navigate(issuesPath)} />
          <StatCard icon={Clock} tone="orange" value={overview.open_issues} label="Open Issues" onClick={() => navigate(`${issuesPath}?status=open`)} />
          <StatCard
            icon={CheckCircle2}
            tone="green"
            value={overview.issues_by_status.resolved + overview.issues_by_status.closed}
            label="Resolved / Closed"
            onClick={() => navigate(`${issuesPath}?status=resolved_closed`)}
          />
          <StatCard icon={FolderOpen} tone="purple" value={overview.total_categories} label="Categories in Use" onClick={() => navigate(issuesPath)} />
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="card p-6">
          <h2 className="mb-4 text-sm font-semibold text-slate-800">Submitted vs. Resolved</h2>
          {isLoading ? (
            <div className="h-64 animate-pulse rounded-lg bg-slate-100" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="submitted" stroke="#2563eb" strokeWidth={2} dot={false} name="Submitted" />
                <Line type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2} dot={false} name="Resolved" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="card p-6">
          <h2 className="mb-4 text-sm font-semibold text-slate-800">Issues by Status</h2>
          {isLoading ? (
            <div className="h-64 animate-pulse rounded-lg bg-slate-100" />
          ) : (
            <IssuesByStatusChart counts={overview.issues_by_status} />
          )}
        </section>
      </div>

      <section className="card mt-6 overflow-x-auto p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-800">Department Summary</h2>
        {isLoading ? (
          <div className="h-40 animate-pulse rounded-lg bg-slate-100" />
        ) : departments.length === 0 ? (
          <p className="text-sm text-slate-400">No issues have been submitted yet.</p>
        ) : (
          <table className="w-full min-w-max text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-3 py-2.5">Department</th>
                <th className="px-3 py-2.5">Open</th>
                <th className="px-3 py-2.5">Resolved</th>
                <th className="px-3 py-2.5">Avg. Resolution Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {departments.map((d) => (
                <tr key={d.department}>
                  <td className="px-3 py-3 font-medium text-slate-700">{d.department}</td>
                  <td className="px-3 py-3 text-slate-600">{d.open}</td>
                  <td className="px-3 py-3 text-slate-600">{d.resolved}</td>
                  <td className="px-3 py-3 text-slate-600">
                    {d.avg_resolution_days > 0 ? `${d.avg_resolution_days} days` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
