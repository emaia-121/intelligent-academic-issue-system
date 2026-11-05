import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { AuthLayout } from './AuthLayout'
import { PasswordField } from '@/components/ui/FormField'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Loading'
import { changePassword } from '@/api/auth'
import { extractErrorMessage } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { homeFor } from '@/routes/ProtectedRoute'

/**
 * Mandatory first-login password change. Reached automatically whenever
 * must_change_password is true (see ProtectedRoute + Login's post-login
 * redirect) -- there is no way to navigate to a dashboard from here until
 * this succeeds.
 */
export function ChangePassword() {
  const { isAuthenticated, isBootstrapping, mustChangePassword, roleGroup, markPasswordChanged, logout } = useAuth()
  const navigate = useNavigate()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (isBootstrapping) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!mustChangePassword) return <Navigate to={homeFor(roleGroup ?? 'student')} replace />

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters.')
      return
    }
    if (newPassword === currentPassword) {
      setError('New password must be different from your current password.')
      return
    }

    setIsSubmitting(true)
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      })
      markPasswordChanged()
      navigate(homeFor(roleGroup ?? 'student'), { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not change your password. Please try again.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Set a new password" subtitle="Update your temporary password to secure your account.">
      <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <ShieldAlert className="mt-0.5 size-4.5 shrink-0 text-amber-500" />
        <p>This is your first login. You must change your temporary password before continuing.</p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        {error && <Alert variant="error">{error}</Alert>}

        <PasswordField
          label="Current (temporary) password"
          required
          autoComplete="current-password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
        />

        <PasswordField
          label="New password"
          required
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          hint="At least 8 characters."
        />

        <PasswordField
          label="Confirm new password"
          required
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70"
        >
          {isSubmitting && <Spinner className="size-4 text-white" />}
          Change Password
        </button>
      </form>

      <button
        type="button"
        onClick={() => {
          logout()
          navigate('/login', { replace: true })
        }}
        className="mt-6 w-full text-center text-sm font-medium text-slate-400 hover:text-slate-600"
      >
        Not you? Log out
      </button>
    </AuthLayout>
  )
}
