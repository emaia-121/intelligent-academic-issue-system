import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from './AuthLayout'
import { TextField, PasswordField } from '@/components/ui/FormField'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Loading'
import { useAuth } from '@/context/AuthContext'
import { extractErrorMessage } from '@/api/client'
import { roleGroup } from '@/types'
import { homeFor } from '@/routes/ProtectedRoute'

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      const profile = await login({ email, password })

      if (profile.must_change_password) {
        navigate('/change-password', { replace: true })
        return
      }

      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname
      navigate(from || homeFor(roleGroup(profile.role)), { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err, 'Incorrect email or password.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to continue to your dashboard.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        {error && <Alert variant="error">{error}</Alert>}

        <TextField
          label="Email Address"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email address"
        />

        <PasswordField
          label="Password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />

        <div className="flex items-center justify-end">
          <Link to="/forgot-password" className="text-sm font-medium text-brand-600 hover:text-brand-700">
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70"
        >
          {isSubmitting && <Spinner className="size-4 text-white" />}
          Sign in
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="font-semibold text-brand-600 hover:text-brand-700">
          Create one
        </Link>
      </p>
    </AuthLayout>
  )
}
