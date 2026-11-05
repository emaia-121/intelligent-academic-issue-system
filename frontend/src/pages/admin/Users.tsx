import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { FilterBar, SearchInput, SelectFilter } from '@/components/ui/Filters'


import { getStaffDirectory, type StaffDirectoryEntry } from '@/api/auth'
import { ROLE_LABELS, type Role } from '@/types'



export function AdminUsers() {
  const [staff, setStaff] = useState<StaffDirectoryEntry[] | null>(null)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [error, setError] = useState<string | null>(null)

  const refresh = () =>
    getStaffDirectory()
      .then(setStaff)
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Could not load staff accounts.')
      })

  useEffect(() => {
    refresh()
  }, [])

  const filtered = useMemo(() => {
    return (staff ?? [])
      .filter((u) => roleFilter === 'all' || u.role === roleFilter)
      .filter((u) =>
        `${u.first_name ?? ''} ${u.last_name ?? ''} ${u.email}`
          .toLowerCase()
          .includes(search.toLowerCase())
      )
  }, [staff, search, roleFilter])


  

  const ROLE_OPTIONS = Array.from(
  new Set((staff ?? []).map((u) => u.role))
)
  .sort()
  .map((role) => ({
    value: role,
    label: ROLE_LABELS[role],
  }))

  const columns: DataTableColumn<StaffDirectoryEntry>[] = [
    {
      key: 'name',
      header: 'Name',
      render: (u) => (
        <div>
          <p className="font-semibold text-slate-800">
            {[u.first_name, u.last_name].filter(Boolean).join(' ') || u.email}
          </p>
          <p className="text-xs text-slate-400">{u.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (u) => ROLE_LABELS[u.role],
    },
    {
      key: 'department',
      header: 'Department',
      render: (u) => u.department_name || '—',
    },
  ]
  

  return (
    <div>
      <PageHeader
        title="Staff Accounts"
        description="View staff accounts and their assigned workflow roles."
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/admin/staff/new"
              className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <UserPlus className="size-4" />
              Create Staff Account
            </Link>
            
          </div>
        }
      />

    

      <FilterBar>
        <SearchInput value={search} onChange={setSearch} placeholder="Search by name or email…" />
        <SelectFilter
          value={roleFilter}
          onChange={setRoleFilter}
          options={[{ value: 'all', label: 'All roles' }, ...ROLE_OPTIONS]}
          label="Filter by role"
        />
      </FilterBar>

      <DataTable columns={columns} rows={filtered} rowKey={(u) => u.id} isLoading={staff === null} emptyTitle="No staff accounts found" emptyDescription="Try adjusting your filters." />

      
    </div>
  )
}
