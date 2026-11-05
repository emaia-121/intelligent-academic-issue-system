import { useEffect, useMemo, useState } from 'react'
import { PageHeader } from '@/components/ui/PageHeader'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { FilterBar, SearchInput, SelectFilter } from '@/components/ui/Filters'
import { Alert } from '@/components/ui/Alert'
import { listDepartments } from '@/api/departments'
import type { Department } from '@/types'

const KIND_OPTIONS = [
  { value: 'all', label: 'All types' },
  { value: 'academic', label: 'Academic' },
  { value: 'administrative', label: 'Administrative' },
]

export function AdminDepartments() {
  const [departments, setDepartments] = useState<Department[] | null>(null)
  const [search, setSearch] = useState('')
  const [kindFilter, setKindFilter] = useState('all')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    listDepartments()
      .then((data: Department[]) => {
        if (!cancelled) {
          setDepartments(data)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load departments.'
          )
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo(() => {
    return (departments ?? [])
      .filter(
        (department) =>
          kindFilter === 'all' || department.kind === kindFilter
      )
      .filter((department) =>
        `${department.name} ${department.description ?? ''}`
          .toLowerCase()
          .includes(search.toLowerCase())
      )
  }, [departments, search, kindFilter])

  const columns: DataTableColumn<Department>[] = [
    {
      key: 'name',
      header: 'Department',
      render: (department) => (
        <div>
          <p className="font-semibold text-slate-800">
            {department.name}
          </p>

          {department.description && (
            <p className="mt-0.5 text-xs text-slate-400">
              {department.description}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'kind',
      header: 'Type',
      render: (department) => (
        <span className="font-medium text-slate-600">
          {department.kind === 'academic'
            ? 'Academic'
            : 'Administrative'}
        </span>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Academic departments and administrative units in the system."
      />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search departments..."
        />

        <SelectFilter
          value={kindFilter}
          onChange={setKindFilter}
          options={KIND_OPTIONS}
          label="Filter by type"
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={filtered}
        rowKey={(department) => department.id}
        isLoading={departments === null}
        emptyTitle="No departments found"
        emptyDescription="No departments match the current filters."
      />
    </div>
  )
}