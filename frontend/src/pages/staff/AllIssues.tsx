import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { FilterBar, SearchInput, SelectFilter } from '@/components/ui/Filters'
import { Pagination } from '@/components/ui/Pagination'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Alert } from '@/components/ui/Alert'
import { listIssues } from '@/api/issues'
import { extractErrorMessage } from '@/api/client'
import { formatDate, issueRef } from '@/lib/format'
import { ISSUE_STATUS_LABELS, type Issue, type IssueStatus } from '@/types'
import { useAuth } from '@/context/AuthContext'

const PAGE_SIZE = 10

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  ...(Object.keys(ISSUE_STATUS_LABELS) as IssueStatus[]).map((s) => ({
    value: s,
    label: ISSUE_STATUS_LABELS[s],
  })),
  { value: 'resolved_closed', label: 'Resolved / Closed' },
]

const ASSIGNMENT_OPTIONS = [
  { value: 'all', label: 'All issues' },
  { value: 'mine', label: 'Assigned to me' },
  { value: 'unassigned', label: 'Unassigned only' },
] 

/**
 * The backend has no server-side scoping by department/officer, so "All
 * Issues" genuinely shows every issue in the system -- useful for staff who
 * need visibility beyond their own assignment queue.
 *
 * The "Unassigned only" filter is the one dimension that isn't filtered
 * client-side like status/department/search below -- it re-fetches from
 * the backend with ?unassigned=true (see api/issues.ts), which is the
 * authoritative assigned_to IS NULL check (Administrative Assignment
 * Management). This is how administrators discover workflow exceptions
 * the workflow engine's automatic assignment couldn't resolve.
 */
export function AllIssues() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') ?? 'all'
  const categoryFilter = searchParams.get('category') ?? 'all' 
  const assignmentFilter = searchParams.get('assignment') ?? 'all'
  const [issues, setIssues] = useState<Issue[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  
  const [departmentFilter, setDepartmentFilter] = useState('all')
  
  const [page, setPage] = useState(1)
  

  useEffect(() => {
    let cancelled = false
    setIssues(null)
    listIssues({ unassigned: assignmentFilter === 'unassigned' })
      .then((all) => !cancelled && setIssues(all))
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load issues.')))
    return () => {
      cancelled = true
    }
  }, [assignmentFilter])

  const departmentOptions = useMemo(() => {
    const names = Array.from(new Set((issues ?? []).map((i) => i.department))).sort()
    return [{ value: 'all', label: 'All departments' }, ...names.map((n) => ({ value: n, label: n }))]
  }, [issues])

  const categoryOptions = useMemo(() => {
    const names = Array.from(new Set((issues ?? []).map((i) => i.category))).sort()

    return [
      { value: 'all', label: 'All categories' },
      ...names.map((name) => ({
        value: name,
        label: name,
      })),
    ]
  }, [issues])

  const filtered = useMemo(() => {
    return (issues ?? [])
      .filter((i) => {
        if (status === 'all') return true

        if (status === 'open') {
          return (
            i.status === 'pending' ||
            i.status === 'ready_for_review' ||
            i.status === 'in_progress'
          )
        }

        if (status === 'resolved_closed') {
          return i.status === 'resolved' || i.status === 'closed'
        }

        return i.status === status
      })
      .filter((i) => categoryFilter === 'all' || i.category === categoryFilter) 
      .filter((i) => {
        if (assignmentFilter === 'all') return true
        if (assignmentFilter === 'mine') return i.assigned_to === user?.email
        return i.assigned_to === null
      })
      .filter((i) => departmentFilter === 'all' || i.department === departmentFilter)
      .filter((i) => i.title.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => b.id - a.id)
  }, [issues, search, status, categoryFilter, departmentFilter, assignmentFilter, user?.email])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const columns: DataTableColumn<Issue>[] = [
    {
      key: 'title',
      header: 'Issue',
      render: (issue) => (
        <div>
          <p className="font-semibold text-slate-800">{issue.title}</p>
          <p className="text-xs text-slate-400">{issueRef(issue.id)}</p>
        </div>
      ),
    },
    {
      key: 'student',
      header: 'Student',
      className: 'w-[190px] px-4 py-3.5 text-slate-700 align-top',
      render: (issue) => (
        <span className="block break-all">
          {issue.student}
        </span>
      ),
    },

    {
      key: 'department',
      header: 'Department',
      className: 'w-[190px] px-4 py-3.5 text-slate-700 align-top',
      render: (issue) => (
        <span className="block whitespace-normal break-words">
          {issue.department}
        </span>
      ),
    },
    {
      key: 'assigned_to',
      header: 'Assigned To',
      className: 'w-[190px] px-4 py-3.5 text-slate-700 align-top',
      render: (issue) =>
        issue.assigned_to ? (
          <span className="block break-all">
            {issue.assigned_to}
          </span>
        ) : (
          <span className="font-medium text-amber-600">Unassigned</span>
        )
    },
    { key: 'status', header: 'Status', render: (issue) => <StatusBadge status={issue.status} /> },
    {
      key: 'created_at',
      header: 'Submitted',
      render: (issue) => <span className="text-slate-500">{formatDate(issue.created_at)}</span>,
    },
  ]

  return (
    <div>
      <PageHeader title="All Issues" description="Every issue currently in the system." />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      <FilterBar>
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Search by title…" />
        <SelectFilter
          value={status}
          onChange={(value) => {
            const params = new URLSearchParams(searchParams)

            if (value === 'all') {
              params.delete('status')
            } else {
              params.set('status', value)
            }

            setSearchParams(params)
            setPage(1)
          }}
          options={STATUS_OPTIONS}
          label="Filter by status"
        />
        
        <SelectFilter
          value={categoryFilter}
          onChange={(value) => {
            const params = new URLSearchParams(searchParams)

            if (value === 'all') {
              params.delete('category')
            } else {
              params.set('category', value)
            }

            setSearchParams(params)
            setPage(1)
          }}
          options={categoryOptions}
          label="Filter by category"
        />

        <SelectFilter value={departmentFilter} onChange={(v) => { setDepartmentFilter(v); setPage(1) }} options={departmentOptions} label="Filter by department" />
        <SelectFilter
          value={assignmentFilter}
          onChange={(value) => {
            const params = new URLSearchParams(searchParams)

            if (value === 'all') {
              params.delete('assignment')
            } else {
              params.set('assignment', value)
            }

            setSearchParams(params)
            setPage(1)
          }}
          options={ASSIGNMENT_OPTIONS}
          label="Filter by assignment"
        />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={pageRows}
        rowKey={(issue) => issue.id}
        isLoading={issues === null}
        emptyTitle="No issues found"
        emptyDescription="Try adjusting your filters."
        onRowClick={(issue) => {
          const basePath = location.pathname.startsWith('/admin/')
            ? '/admin/issues'
            : '/staff/issues'

          navigate(`${basePath}/${issue.id}`)
        }}
      />

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  )
}
