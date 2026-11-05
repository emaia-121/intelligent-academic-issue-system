import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom' 
import { Users, Building2, ListChecks, Clock, AlertTriangle, UserX } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatCard } from '@/components/ui/StatCard'
import { CardSkeleton } from '@/components/ui/Loading'
import { IssueCard } from '@/components/ui/IssueCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { Alert } from '@/components/ui/Alert'
import { IssuesByStatusChart } from '@/components/charts/IssuesByStatusChart'
import { getAdminOverview } from '@/api/mock/reports'
import { listIssues } from '@/api/issues'
import { getStaffDirectory, type StaffDirectoryEntry } from '@/api/auth'
import { extractErrorMessage } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { CATEGORY_STARTING_ROLE, buildRoleCounts, type RoleCount, type StaffRole } from '@/lib/roleWorkloadConfig'
import { DEPARTMENT_SCOPED_ROLES, ROLE_LABELS } from '@/types'
import type { AdminOverviewStats, Issue } from '@/types'

const QUICK_LINKS = [
  { to: '/admin/staff/new', label: 'Create Staff Account' },
  { to: '/admin/users', label: 'Staff Accounts' },
  { to: '/admin/departments', label: 'Manage Departments' },
  { to: '/admin/categories', label: 'Manage Categories' },
  
]

interface RoleBreakdownRow {
  role: StaffRole
  issues: Issue[]
  categoryCounts: { category: string; count: number }[]
  availableOfficers: number
}

/**
 * Groups unassigned issues by the workflow role that should have received
 * them first, per CATEGORY_STARTING_ROLE (lib/roleWorkloadConfig.ts, a
 * mirror of WorkflowDefinition.starting_role). This is safe because
 * Issue.assigned_to is only ever left null by
 * perform_initial_assignment() failing to resolve the category's
 * starting_role (see that function's docstring in
 * issues/workflow/service.py) -- forward_issue()/send_back_issue() raise
 * instead of leaving an issue unassigned, so a starting-role lookup is
 * always the correct explanation for any unassigned issue in the system
 * today.
 *
 * `availableOfficers` counts staff directory entries system-wide for that
 * role (GET /api/accounts/staff/directory/), exactly as specified -- not
 * scoped to any particular student's department. See the deliverables
 * note on this: the real backend lookup for department-scoped roles
 * (find_officer_for_role in issues/workflow/roles.py) additionally scopes
 * by the issue's student's own department, which isn't exposed on the
 * Issue list/detail shape today, so this widget can only show whether a
 * role is staffed *anywhere*, not whether it's staffed in the specific
 * department each affected issue needs.
 */
function buildRoleBreakdown(unassigned: Issue[], staff: StaffDirectoryEntry[]): RoleBreakdownRow[] {
  const byRole = new Map<StaffRole, Map<string, number>>()

  for (const issue of unassigned) {
    const role = CATEGORY_STARTING_ROLE[issue.category]
    if (!role) continue // Not one of the 12 canonical categories -- shouldn't happen; skip defensively rather than crash.
    const categories = byRole.get(role) ?? new Map<string, number>()
    categories.set(issue.category, (categories.get(issue.category) ?? 0) + 1)
    byRole.set(role, categories)
  }

  const rows: RoleBreakdownRow[] = Array.from(byRole.entries()).map(([role, categories]) => ({
    role,
    issues: unassigned.filter((i) => CATEGORY_STARTING_ROLE[i.category] === role),
    categoryCounts: Array.from(categories.entries())
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count),
    availableOfficers: staff.filter((s) => s.role === role).length,
  }))

  return rows.sort((a, b) => b.issues.length - a.issues.length)
}

export function AdminDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [overview, setOverview] = useState<AdminOverviewStats | null>(null)
  const [recent, setRecent] = useState<Issue[] | null>(null)
  const [unassigned, setUnassigned] = useState<Issue[] | null>(null)
  const [staff, setStaff] = useState<StaffDirectoryEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([getAdminOverview(), listIssues(), listIssues({ unassigned: true }), getStaffDirectory()])
      .then(([o, issues, unassignedIssues, staffDirectory]) => {
        if (cancelled) return
        setOverview(o)
        setRecent([...issues].sort((a, b) => b.id - a.id).slice(0, 6))
        setUnassigned(unassignedIssues)
        setStaff(staffDirectory)
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load dashboard data.')))
    return () => {
      cancelled = true
    }
  }, [])

  const isLoading = !overview || unassigned === null || staff === null

  const roleBreakdown = useMemo(
    () => (unassigned && staff ? buildRoleBreakdown(unassigned, staff) : []),
    [unassigned, staff],
  )

  // Reuses the exact same `staff` fetch above (getStaffDirectory(), already
  // loaded for the Unassigned by Role widget) -- no second request.
  const roleCounts = useMemo(() => (staff ? buildRoleCounts(staff) : []), [staff])

  const roleCountColumns: DataTableColumn<RoleCount>[] = [
    {
      key: 'role',
      header: 'Role',
      render: (row) => <span className="font-medium text-slate-700">{ROLE_LABELS[row.role]}</span>,
    },
    {
      key: 'count',
      header: 'Staff Count',
      render: (row) => (
        <span className={row.count === 0 ? 'font-semibold text-red-600' : 'font-semibold text-slate-800'}>
          {row.count}
        </span>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.first_name || user?.email}`}
        description="System-wide overview."
      />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      {isLoading || !overview ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard icon={ListChecks} tone="blue" value={overview.total_issues} label="Total Issues" onClick={() => navigate('/admin/issues')} />
          <StatCard icon={Clock} tone="orange" value={overview.open_issues} label="Open Issues" onClick={() => navigate('/admin/issues?status=open')} />
          <StatCard icon={AlertTriangle} tone="red" value={unassigned?.length ?? 0} label="Unassigned Issues" onClick={() => navigate('/admin/issues?assignment=unassigned')} />
          <StatCard icon={Users} tone="purple" value={overview.total_users} label="Total Users" onClick={() => navigate('/admin/users')} />
          <StatCard icon={Building2} tone="slate" value={overview.total_departments} label="Departments" onClick={() => navigate('/admin/departments')} />
        </div>
      )}

      <div className="card mt-6 p-5">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Staff Coverage by Role</h2>
        </div>
        <p className="mb-3 text-xs text-slate-400">
          How many staff accounts currently hold each workflow role -- a role showing 0 is a staffing gap.
        </p>

        <DataTable columns={roleCountColumns} rows={roleCounts} rowKey={(row) => row.role} isLoading={isLoading} />
      </div>

      <div className="card mt-6 p-5">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Unassigned Issues by Role</h2>
        </div>
        <p className="mb-3 text-xs text-slate-400">
          Which role each unassigned issue is waiting on, and whether any staff member currently holds it.
        </p>

        {isLoading ? (
          <div className="space-y-2 pt-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        ) : roleBreakdown.length === 0 ? (
          <EmptyState
            icon={ListChecks}
            title="No Unassigned Issues"
            description="All issues currently have an assigned officer."
          />
        ) : (
          <div className="divide-y divide-slate-50">
            {roleBreakdown.map((row) => {
              const roleLabel = ROLE_LABELS[row.role]
              const isDeptScoped = DEPARTMENT_SCOPED_ROLES.includes(row.role)
              const hasOfficers = row.availableOfficers > 0

              return (
                <div key={row.role} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{roleLabel}</p>
                      <p className="text-xs text-slate-400">
                        {row.issues.length} unassigned {row.issues.length === 1 ? 'issue' : 'issues'}
                      </p>
                    </div>

                    {hasOfficers ? (
                      <span className="text-xs font-medium text-slate-500">
                        Available officers: {row.availableOfficers}
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs font-semibold text-red-600">
                        <UserX className="size-3.5" />
                        No {roleLabel}{isDeptScoped ? ' exists for the student’s department' : ' officer exists'}
                      </span>
                    )}
                  </div>

                  <ul className="mt-2 space-y-0.5 pl-1 text-xs text-slate-500">
                    {row.categoryCounts.map(({ category, count }) => (
                      <li key={category}>
                        &bull; {category} ({count})
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="card mt-6 p-5">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Issue Status Overview</h2>
        </div>
        <p className="mb-3 text-xs text-slate-400">System-wide distribution of issues across every status.</p>

        {isLoading || !overview ? (
          <div className="h-64 animate-pulse rounded-lg bg-slate-100" />
        ) : (
          <IssuesByStatusChart counts={overview.issues_by_status} />
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">Recent Issues</h2>
            <Link to="/staff/all-issues" className="text-xs font-semibold text-brand-600 hover:text-brand-700">
              View all
            </Link>
          </div>

          {!recent ? (
            <div className="space-y-2 pt-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <EmptyState title="No issues yet" />
          ) : (
            <div className="divide-y divide-slate-50">
              {recent.map((issue) => (
                <IssueCard key={issue.id} issue={issue} to={`/staff/issues/${issue.id}`} />
              ))}
            </div>
          )}
        </div>

        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-800">Quick Actions</h2>
          <div className="space-y-1.5">
            {QUICK_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="block rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
