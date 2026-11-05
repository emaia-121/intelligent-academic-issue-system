import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { AuthLayout } from './AuthLayout'
import { TextField, PasswordField, SelectField } from '@/components/ui/FormField'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Loading'
import { registerStudent } from '@/api/auth'
import { extractErrorMessage } from '@/api/client'
import { ACADEMIC_DEPARTMENTS } from '@/types'

const LEVEL_OPTIONS = ['100', '200', '300', '400', '500'].map((l) => ({ value: l, label: `${l} Level` }))
const DEPARTMENT_OPTIONS = ACADEMIC_DEPARTMENTS.map((name) => ({ value: name, label: name }))

export function Register() {
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    matric_number: '',
    department_name: '',
    level: '',
    phone_number: '',
    password: '',
    confirm_password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const update = (field: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await registerStudent(form)
      setDone(true)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not create your account.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (done) {
    return (
      <AuthLayout title="Account created" subtitle="You're all set.">
        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-5 text-center">
          <CheckCircle2 className="mx-auto size-8 text-emerald-500" />
          <p className="mt-3 text-sm font-semibold text-emerald-800">Your account was created successfully.</p>
          <p className="mt-1.5 text-sm text-emerald-700">You can now sign in with your email and password.</p>
        </div>
        <Link
          to="/login"
          className="mt-6 flex h-11 w-full items-center justify-center rounded-lg bg-brand-600 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Go to sign in
        </Link>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Create your account" subtitle="Register as a student to start submitting issues.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        {error && <Alert variant="error">{error}</Alert>}

        <div className="grid grid-cols-2 gap-3">
          <TextField label="First name" required value={form.first_name} onChange={update('first_name')} />
          <TextField label="Last name" required value={form.last_name} onChange={update('last_name')} />
        </div>

        <TextField
          label="Email Address"
          type="email"
          required
          value={form.email}
          onChange={update('email')}
          placeholder="Enter your email address"
        />

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Matriculation number"
            required
            value={form.matric_number}
            onChange={update('matric_number')}
            placeholder="e.g. 2021001234"
          />
          <TextField
            label="Phone number"
            type="tel"
            required
            value={form.phone_number}
            onChange={update('phone_number')}
            placeholder="e.g. 08012345678"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label="Department"
            required
            placeholder="Select department"
            value={form.department_name}
            onChange={update('department_name')}
            options={DEPARTMENT_OPTIONS}
          />
          <SelectField
            label="Level"
            required
            placeholder="Select level"
            value={form.level}
            onChange={update('level')}
            options={LEVEL_OPTIONS}
          />
        </div>

        <PasswordField
          label="Password"
          required
          value={form.password}
          onChange={update('password')}
          hint="At least 8 characters."
        />

        <PasswordField label="Confirm password" required value={form.confirm_password} onChange={update('confirm_password')} />

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70"
        >
          {isSubmitting && <Spinner className="size-4 text-white" />}
          Create account
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
