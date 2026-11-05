/**
 * Admin reporting/analytics. There is no analytics endpoint on the backend,
 * but the issue-level numbers here are computed from the *real* `/api/issues/`
 * response where possible (status breakdown, department breakdown, trend
 * line) -- only the "total users" / "total departments" counts fall back to
 * the mock admin store, since accounts/departments have no list endpoint.
 */
import { listIssues } from '@/api/issues'
import { listDepartments, listUsers } from '@/api/mock/store'
import type { AdminOverviewStats, DepartmentSummary, Issue, IssueTrendPoint } from '@/types'

/**
 * Pure status-breakdown counter -- extracted out of getAdminOverview() below
 * so it can be reused wherever a status breakdown is needed, not just for
 * the system-wide admin view. getAdminOverview() calls this on every issue
 * in the system; the Staff Dashboard's workload chart
 * (pages/staff/Dashboard.tsx) calls this on that officer's own
 * already-filtered issues instead -- same counting logic, different input,
 * so the aggregation itself is never duplicated.
 */
export function computeStatusCounts(issues: Issue[]): AdminOverviewStats['issues_by_status'] {
  const counts: AdminOverviewStats['issues_by_status'] = {
    pending: 0,
    ready_for_review: 0,
    in_progress: 0,
    resolved: 0,
    closed: 0,
  }
  for (const issue of issues) counts[issue.status] += 1
  return counts
}

export async function getAdminOverview(): Promise<AdminOverviewStats> {
  const [issues, departments, users] = await Promise.all([listIssues(), listDepartments(), listUsers()])

  const issues_by_status = computeStatusCounts(issues)

  const categories = new Set(issues.map((i) => i.category))

  return {
    total_users: users.length,
    total_departments: departments.length,
    total_categories: categories.size,
    open_issues: issues_by_status.pending + issues_by_status.ready_for_review + issues_by_status.in_progress,
    issues_by_status,
    total_issues: issues.length,
  }
}

/** Buckets real issues by created_at month for a lightweight trend chart. */
export async function getIssueTrend(): Promise<IssueTrendPoint[]> {
  const issues = await listIssues()
  const byMonth = new Map<string, { submitted: number; resolved: number }>()

  for (const issue of issues) {
    const d = new Date(issue.created_at)
    const label = d.toLocaleDateString('en-US', { month: 'short' })
    const bucket = byMonth.get(label) ?? { submitted: 0, resolved: 0 }
    bucket.submitted += 1
    if (issue.status === 'resolved' || issue.status === 'closed') bucket.resolved += 1
    byMonth.set(label, bucket)
  }

  if (byMonth.size === 0) {
    return [{ label: 'This month', submitted: 0, resolved: 0 }]
  }

  return Array.from(byMonth.entries()).map(([label, v]) => ({ label, ...v }))
}

export async function getDepartmentSummaries(): Promise<DepartmentSummary[]> {
  const issues = await listIssues()
  const byDept = new Map<string, Issue[]>()
  for (const issue of issues) {
    const list = byDept.get(issue.department) ?? []
    list.push(issue)
    byDept.set(issue.department, list)
  }

  return Array.from(byDept.entries()).map(([department, list]) => {
    const resolved = list.filter(
      (i) => (i.status === 'resolved' || i.status === 'closed') && i.resolved_at
    )

    const open = list.length - list.filter(
      (i) => i.status === 'resolved' || i.status === 'closed'
    ).length

    const avgDays =
      resolved.length === 0
        ? 0
        : resolved.reduce((sum, i) => {
          const created = new Date(i.created_at).getTime()
          const resolvedAt = new Date(i.resolved_at!).getTime()

          return sum + Math.max(0, (resolvedAt - created) / 86_400_000)
        }, 0) / resolved.length

    return {
      department,
      open,
      resolved: resolved.length,
      avg_resolution_days: Math.round(avgDays * 10) / 10, 
    }
  })
}
