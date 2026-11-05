import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { FilterBar, SearchInput, SelectFilter } from '@/components/ui/Filters'
import { Pagination } from '@/components/ui/Pagination'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Alert } from '@/components/ui/Alert'
import { listIssues } from '@/api/issues'
import { useAuth } from '@/context/AuthContext'
import { extractErrorMessage } from '@/api/client'
import { formatDate, issueRef } from '@/lib/format'
import { ISSUE_STATUS_LABELS, type Issue, type IssueStatus } from '@/types'

const PAGE_SIZE = 8

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  ...(Object.keys(ISSUE_STATUS_LABELS) as IssueStatus[]).map((s) => ({ value: s, label: ISSUE_STATUS_LABELS[s] })),
]

export function AssignedIssues() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [issues, setIssues] = useState<Issue[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)

  useEffect(() => {
    let cancelled = false
    listIssues()
      .then((all) => !cancelled && setIssues(all.filter((i) => i.assigned_to === user?.email)))
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load assigned issues.')))
    return () => {
      cancelled = true
    }
  }, [user?.email])

  const filtered = useMemo(() => {
    return (issues ?? [])
      .filter((i) => status === 'all' || i.status === status)
      .filter((i) => i.title.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => a.id - b.id)
  }, [issues, search, status])

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
    { key: 'student', header: 'Student', render: (issue) => issue.student },
    { key: 'category', header: 'Category', render: (issue) => issue.category },
    { key: 'status', header: 'Status', render: (issue) => <StatusBadge status={issue.status} /> },
    {
      key: 'created_at',
      header: 'Submitted',
      render: (issue) => <span className="text-slate-500">{formatDate(issue.created_at)}</span>,
    },
  ]

  return (
    <div>
      <PageHeader title="Assigned Issues" description="Issues currently assigned to you." />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      <FilterBar>
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Search by title…" />
        <SelectFilter value={status} onChange={(v) => { setStatus(v); setPage(1) }} options={STATUS_OPTIONS} label="Filter by status" />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={pageRows}
        rowKey={(issue) => issue.id}
        isLoading={issues === null}
        emptyTitle="No assigned issues"
        emptyDescription={search || status !== 'all' ? 'Try adjusting your filters.' : 'Issues assigned to you will appear here.'}
        onRowClick={(issue) => navigate(`/staff/issues/${issue.id}`)}
      />

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  )
}
