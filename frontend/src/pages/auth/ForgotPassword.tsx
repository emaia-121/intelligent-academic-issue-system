import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck } from 'lucide-react'
import { AuthLayout } from './AuthLayout'
import { TextField } from '@/components/ui/FormField'
import { Spinner } from '@/components/ui/Loading'

/**
 * MOCK ONLY: the backend has no password-reset endpoint yet (only
 * /api/token/ and /api/token/refresh/ exist). This screen simulates the
 * request/acknowledgement step of the flow so the UI is complete and ready
 * to wire up the moment a real endpoint ships -- it never claims an email
 * was actually sent by a server.
 */
export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    await new Promise((r) => setTimeout(r, 500))
    setIsSubmitting(false)
    setSent(true)
  }

  if (sent) {
    return (
      <AuthLayout title="Check your email" subtitle="If an account matches, reset instructions are on the way.">
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-5 text-center">
          <MailCheck className="mx-auto size-8 text-blue-500" />
          <p className="mt-3 text-sm font-semibold text-blue-800">Request submitted for {email}</p>
          <p className="mt-1.5 text-sm text-blue-700">
            Password reset delivery is not yet connected to a live email service. Contact your
            department administrator if you need immediate access.
          </p>
        </div>
        <Link
          to="/login"
          className="mt-6 flex h-11 w-full items-center justify-center rounded-lg bg-brand-600 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Back to sign in
        </Link>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your email and we'll help you reset it.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <TextField
          label="Email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@student.edu"
        />

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70"
        >
          {isSubmitting && <Spinner className="size-4 text-white" />}
          Send reset instructions
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Remembered your password?{' '}
        <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
