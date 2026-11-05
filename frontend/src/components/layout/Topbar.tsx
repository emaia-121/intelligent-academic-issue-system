import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, ChevronDown, LogOut, Menu, UserCircle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { ROLE_LABELS } from '@/types'
import { initials } from '@/lib/format'

export function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [menuOpen])

  const displayName = user
    ? [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email
    : ''

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center justify-between border-b border-slate-100 bg-white/80 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-lg p-2 text-slate-500 hover:bg-slate-50 lg:hidden"
        aria-label="Open menu"
      >
        <Menu className="size-5" />
      </button>

      <div className="hidden lg:block" />

      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          title="No live notifications yet"
          className="flex size-9 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-50 hover:text-slate-600"
          aria-label="Notifications"
        >
          <Bell className="size-4.5" />
        </button>

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg py-1.5 pl-1.5 pr-2 hover:bg-slate-50"
          >
            <div className="flex size-8 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
              {user ? initials(displayName || "") : <UserCircle className="size-4.5" />} 
            </div>
            <div className="hidden text-left sm:block">
              <p className="text-sm font-semibold leading-tight text-slate-800">{displayName}</p>
              <p className="text-xs leading-tight text-slate-400">
                {user ? ROLE_LABELS[user.role] : ''}
              </p>
            </div>
            <ChevronDown className="size-3.5 text-slate-400" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-slate-100 bg-white py-1.5 shadow-lg">
              <div className="border-b border-slate-100 px-3 pb-2">
                <p className="truncate text-sm font-semibold text-slate-800">{displayName}</p>
                <p className="truncate text-xs text-slate-400">{user?.email}</p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-1 flex w-full items-center gap-2 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
              >
                <LogOut className="size-4" />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
