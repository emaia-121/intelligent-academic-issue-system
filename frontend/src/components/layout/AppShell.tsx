import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useAuth } from '@/context/AuthContext'

/**
 * The authenticated application shell: role-aware sidebar + topbar wrapping
 * a routed <Outlet />. Mounted once per role group in App.tsx so `roleGroup`
 * is always defined here (RoleRoute guards against a null one upstream).
 */
export function AppShell() {
  const { roleGroup } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (!roleGroup) return null

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar roleGroup={roleGroup} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
