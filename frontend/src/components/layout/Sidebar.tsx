import { NavLink } from 'react-router-dom'
import clsx from 'clsx'
import {
  LayoutDashboard,
  FilePlus2,
  ListChecks,
  Search,
  Bell,
  UserCircle,
  Inbox,
  BarChart3,
  Users,
  Building2,
  Tag,
  FileText,
  GraduationCap,
  UserPlus,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { RoleGroup } from '@/types'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

const NAV_BY_ROLE: Record<RoleGroup, NavItem[]> = {
  student: [
    { to: '/student/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/student/issues/new', label: 'Create Issue', icon: FilePlus2 },
    { to: '/student/issues', label: 'My Issues', icon: ListChecks },
    { to: '/student/track', label: 'Track Status', icon: Search },
    { to: '/student/notifications', label: 'Notifications', icon: Bell },
    { to: '/student/profile', label: 'Profile', icon: UserCircle },
  ],
  staff: [
    { to: '/staff/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/staff/issues', label: 'Assigned Issues', icon: Inbox },
    { to: '/staff/all-issues', label: 'All Issues', icon: ListChecks },
    { to: '/staff/reports', label: 'Reports', icon: BarChart3 },
    { to: '/staff/profile', label: 'Profile', icon: UserCircle },
  ],
  admin: [
    { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/admin/users', label: 'Users', icon: Users },
    { to: '/admin/staff/new', label: 'Add Staff', icon: UserPlus },
    { to: '/admin/departments', label: 'Departments', icon: Building2 },
    { to: '/admin/categories', label: 'Categories', icon: Tag },
    { to: '/admin/documents', label: 'Document Types', icon: FileText },
    { to: '/admin/reports', label: 'Reports', icon: BarChart3 },
    
  ],
}

export function Sidebar({
  roleGroup,
  isOpen,
  onClose,
}: {
  roleGroup: RoleGroup
  isOpen: boolean
  onClose: () => void
}) {
  const items = NAV_BY_ROLE[roleGroup]

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-slate-100 bg-white transition-transform lg:static lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 shrink-0 items-center justify-between px-5">
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <GraduationCap className="size-4.5" />
            </div>
            <span className="text-sm font-bold leading-tight text-slate-900">
              SIMS
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-50 lg:hidden"
            aria-label="Close menu"
          >
            <X className="size-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800',
                )
              }
            >
              <Icon className="size-4.5 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-100 px-5 py-4 text-[11px] text-slate-400">
          Student Issue Management System
        </div>
      </aside>
    </>
  )
}
