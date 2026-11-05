import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import type { RoleGroup } from '@/types'

/** Redirects to /login when not authenticated. Wrap the whole authenticated
 * tree in this. Also enforces the mandatory first-login password change:
 * while `must_change_password` is true, every route in this tree redirects
 * to /change-password instead of rendering -- dashboards stay unreachable
 * until the password is changed. */
export function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping, mustChangePassword } = useAuth()
  const location = useLocation()

  if (isBootstrapping) return null
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />
  if (mustChangePassword) return <Navigate to="/change-password" replace />

  return <Outlet />
}

/** Wrap a role's route subtree in this to keep e.g. a student out of /admin/*. */
export function RoleRoute({ allow }: { allow: RoleGroup[] }) {
  const { roleGroup } = useAuth()

  if (!roleGroup) return <Navigate to="/login" replace />
  if (!allow.includes(roleGroup)) return <Navigate to={homeFor(roleGroup)} replace />

  return <Outlet />
}

/** Wrap public-only routes (login, register) in this so an already
 * authenticated user is bounced to their dashboard instead of seeing the
 * login/register form again. */
export function GuestRoute() {
  const { isAuthenticated, isBootstrapping, mustChangePassword, roleGroup } = useAuth()

  if (isBootstrapping) return null
  if (isAuthenticated) {
    return <Navigate to={mustChangePassword ? '/change-password' : homeFor(roleGroup ?? 'student')} replace />
  }

  return <Outlet />
}

export function homeFor(group: RoleGroup): string {
  if (group === 'student') return '/student/dashboard'
  if (group === 'admin') return '/admin/dashboard'
  return '/staff/dashboard'
}
