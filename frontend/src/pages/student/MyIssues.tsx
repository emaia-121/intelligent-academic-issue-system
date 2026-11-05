import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
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
import type { Issue } from '@/types' 

const PAGE_SIZE = 8


export function MyIssues() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [issues, setIssues] = useState<Issue[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') ?? 'all'
  const [page, setPage] = useState(1)

  useEffect(() => {
    let cancelled = false
    listIssues()
      .then((all) => !cancelled && setIssues(all.filter((i) => i.student === user?.email)))
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load your issues.')))
    return () => {
      cancelled = true
    }
  }, [user?.email])

  const filtered = useMemo(() => {
    return (issues ?? [])
      .filter((issue) => {
        if (status === 'all') return true

        if (status === 'open') {
          return issue.status === 'pending' || issue.status === 'ready_for_review'
        }

        if (status === 'resolved_closed') {
          return issue.status === 'resolved' || issue.status === 'closed'
        }

        return issue.status === status
      })
      .filter((issue) =>
        issue.title.toLowerCase().includes(search.toLowerCase()),
      )
      .sort((a, b) => b.id - a.id)
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
    { key: 'category', header: 'Category', render: (issue) => issue.category },
    { key: 'department', header: 'Department', render: (issue) => issue.department },
    { key: 'status', header: 'Status', render: (issue) => <StatusBadge status={issue.status} /> },
    {
      key: 'created_at',
      header: 'Submitted',
      render: (issue) => <span className="text-slate-500">{formatDate(issue.created_at)}</span>,
    },
  ]

  return (
    <div>
      <PageHeader
        title="My Issues"
        description="All issues you've submitted."
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
          options={[
            { value: 'all', label: 'All statuses' },
            { value: 'open', label: 'Open' },
            { value: 'in_progress', label: 'In Progress' },
            { value: 'resolved_closed', label: 'Resolved / Closed' },
          ]}
          label="Filter by status"
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={pageRows}
        rowKey={(issue) => issue.id}
        isLoading={issues === null}
        emptyTitle="No issues found"
        emptyDescription={search || status !== 'all' ? 'Try adjusting your filters.' : 'Create your first issue to get started.'}
        onRowClick={(issue) => navigate(`/student/issues/${issue.id}`)}
      />

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  )
}
