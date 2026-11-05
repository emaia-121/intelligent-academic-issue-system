import { useEffect, useMemo, useState } from 'react'
import { PageHeader } from '@/components/ui/PageHeader'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { FilterBar, SearchInput } from '@/components/ui/Filters'
import { Alert } from '@/components/ui/Alert'
import { listCategories } from '@/api/categories'
import type { CategoryOption } from '@/types'

export function AdminCategories() {
  const [categories, setCategories] = useState<CategoryOption[] | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    listCategories()
      .then((data: CategoryOption[]) => {
        if (!cancelled) {
          setCategories(data)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load categories.'
          )
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo(() => {
    return (categories ?? []).filter((category) =>
      `${category.name} ${category.department}`
        .toLowerCase()
        .includes(search.toLowerCase())
    )
  }, [categories, search])

  const columns: DataTableColumn<CategoryOption>[] = [
    {
      key: 'name',
      header: 'Category',
      render: (category) => (
        <span className="font-semibold text-slate-800">
          {category.name}
        </span>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (category) => (
        <span className="text-slate-600">
          {category.department}
        </span>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Categories"
        description="Issue categories and their designated handling departments."
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
          placeholder="Search categories..."
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={filtered}
        rowKey={(category) => category.id}
        isLoading={categories === null}
        emptyTitle="No categories found"
        emptyDescription="No categories match your search."
      />
    </div>
  )
}