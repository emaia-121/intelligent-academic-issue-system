import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  getStoredProfile,
  login as apiLogin,
  logout as apiLogout,
  patchStoredProfile,
  type LoginPayload,
} from '@/api/auth'
import { tokenStorage } from '@/api/client'
import type { RoleGroup, UserProfile } from '@/types'
import { roleGroup } from '@/types'

interface AuthContextValue {
  user: UserProfile | null
  roleGroup: RoleGroup | null
  isAuthenticated: boolean
  isBootstrapping: boolean
  /** True once logged in until the mandatory first-login password change is
   * completed -- see accounts.models.UserProfile.must_change_password. */
  mustChangePassword: boolean
  login: (payload: LoginPayload) => Promise<UserProfile>
  logout: () => void
  /** Call after a successful password change to clear the must-change flag
   * locally (there's no /me/ endpoint to re-fetch from). */
  markPasswordChanged: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [isBootstrapping, setIsBootstrapping] = useState(true)

  useEffect(() => {
    const access = tokenStorage.getAccess()
    const storedProfile = getStoredProfile()
    if (access && storedProfile) setUser(storedProfile)
    setIsBootstrapping(false)
  }, [])

  useEffect(() => {
    const onExpired = () => {
      apiLogout()
      setUser(null)
    }
    window.addEventListener('sims:session-expired', onExpired)
    return () => window.removeEventListener('sims:session-expired', onExpired)
  }, [])

  const login = useCallback(async (payload: LoginPayload) => {
    const { profile } = await apiLogin(payload)
    setUser(profile)
    return profile
  }, [])

  const logout = useCallback(() => {
    apiLogout()
    setUser(null)
  }, [])

  const markPasswordChanged = useCallback(() => {
    const updated = patchStoredProfile({ must_change_password: false })
    if (updated) setUser(updated)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      roleGroup: user ? roleGroup(user.role) : null,
      isAuthenticated: !!user,
      isBootstrapping,
      mustChangePassword: !!user?.must_change_password,
      login,
      logout,
      markPasswordChanged,
    }),
    [user, isBootstrapping, login, logout, markPasswordChanged],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
