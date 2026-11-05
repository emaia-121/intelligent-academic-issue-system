import type { ReactNode } from 'react'
import { EmptyState } from './EmptyState'
import { TableSkeleton } from './Loading'

export interface DataTableColumn<T> {
  key: string
  header: string
  render: (row: T) => ReactNode
  className?: string
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading,
  emptyTitle = 'Nothing here yet',
  emptyDescription,
  onRowClick,
}: {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  isLoading?: boolean
  emptyTitle?: string
  emptyDescription?: string
  onRowClick?: (row: T) => void
}) {
  if (isLoading) {
    return (
      <div className="card overflow-hidden">
        <TableSkeleton />
      </div>
    )
  }

  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[1000px] table-auto text-left text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            {columns.map((col) => (
              <th
                key={col.key}
                className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-50">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={onRowClick ? 'cursor-pointer hover:bg-slate-50' : undefined}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={
                    col.className ??
                    'px-4 py-3.5 text-slate-700 align-top'
                  }
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
} 