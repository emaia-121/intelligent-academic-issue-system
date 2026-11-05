import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Check, Copy, UserPlus } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { TextField, SelectField } from '@/components/ui/FormField'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Loading'
import { createStaffAccount, type CreateStaffResult } from '@/api/auth'
import { extractErrorMessage } from '@/api/client'
import { ACADEMIC_DEPARTMENTS, ROLE_LABELS, STAFF_ROLES, isDepartmentScopedRole, type Role } from '@/types'

const DEPARTMENT_OPTIONS = ACADEMIC_DEPARTMENTS.map((name) => ({ value: name, label: name }))

const emptyForm = {
  first_name: '',
  last_name: '',
  email: '',
  staff_id: '',
  department_name: '',
  phone_number: '',
  role: '' as Role | '',
}

/**
 * Admin-only. Wired to the real POST /api/accounts/staff/ endpoint
 * (IsSystemAdmin on the backend). The backend generates the temporary
 * password -- this screen only displays it once, in local component state,
 * and never persists it to context or localStorage.
 */
export function StaffCreate() {
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<CreateStaffResult | null>(null)
  const [copied, setCopied] = useState(false)

  const deptScoped = isDepartmentScopedRole(form.role)

  /**
   * Department-scoped roles (Course Adviser, HOD, Lecturer, Department
   * Admin, Dept Exam Officer) need a real academic department -- that's
   * what issues/workflow/roles.py's department-scoped lookup matches
   * against. Central roles (ICT Officer, Exams Officer, Student Affairs
   * Officer, Registry, Bursary, School Admin Office, Admin) are resolved
   * institution-wide with no department scoping at all, so an academic
   * department is meaningless for them and the picker is hidden entirely.
   *
   * accounts.serializers.StaffAccountCreationSerializer.department_name is
   * still a required, non-blank CharField on the backend (unchanged here),
   * so a central-role account still needs *some* non-blank value submitted
   * -- rather than inventing a fake academic department for e.g. an ICT
   * Officer, this uses that role's own office name (its existing
   * ROLE_LABELS entry, e.g. "Registry", "Bursary Office"), which is never
   * read by routing for central roles in the first place.
   */
  const handleRoleChange = (role: Role) => {
    setForm((f) => ({
      ...f,
      role,
      department_name: isDepartmentScopedRole(role) ? '' : ROLE_LABELS[role],
    }))
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!form.role) {
      setError('Select a role for this staff member.')
      return
    }

    if (deptScoped && !form.department_name) {
      setError('Select an academic department for this role.')
      return
    }

    setIsSubmitting(true)
    try {
      const created = await createStaffAccount({ ...form, role: form.role })
      setResult(created)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not create the staff account.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCopy = async () => {
    if (!result) return
    await navigator.clipboard.writeText(result.temporary_password)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCreateAnother = () => {
    setResult(null)
    setForm(emptyForm)
    setCopied(false)
  }

  if (result) {
    return (
      <div className="mx-auto max-w-lg">
        <PageHeader title="Staff Account Created" />

        <div className="card p-6">
          <div className="mb-5 flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
            <Check className="size-4.5 shrink-0" />
            {result.first_name} {result.last_name} can now sign in with the credentials below.
          </div>

          <dl className="space-y-4 text-sm">
            <div>
              <dt className="text-xs text-slate-400">Staff Name</dt>
              <dd className="mt-0.5 font-medium text-slate-800">
                {result.first_name} {result.last_name}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Email</dt>
              <dd className="mt-0.5 font-medium text-slate-800">{result.email}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Role</dt>
              <dd className="mt-0.5 font-medium text-slate-800">{ROLE_LABELS[result.role]}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Temporary Password</dt>
              <dd className="mt-1.5 flex items-center gap-2">
                <code className="flex-1 rounded-lg bg-slate-100 px-3 py-2 font-mono text-sm text-slate-800">
                  {result.temporary_password}
                </code>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex h-9 shrink-0 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-xs font-semibold text-white hover:bg-brand-700"
                >
                  {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </dd>
            </div>
          </dl>

          <p className="mt-5 text-xs text-slate-400">
            Share this password with {result.first_name} through a secure channel. They'll be required to set a
            new password the first time they sign in.
          </p>

          <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-5">
            <Link to="/admin/users" className="text-sm font-semibold text-slate-500 hover:text-slate-700">
              Back to Users
            </Link>
            <button
              type="button"
              onClick={handleCreateAnother}
              className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Create Another
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg">
      <PageHeader title="Create Staff Account" description="Only administrators can create staff accounts." />

      <form className="card space-y-4 p-6" onSubmit={handleSubmit}>
        {error && <Alert variant="error">{error}</Alert>}

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="First name"
            required
            value={form.first_name}
            onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
          />
          <TextField
            label="Last name"
            required
            value={form.last_name}
            onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
          />
        </div>

        <TextField
          label="Email Address"
          type="email"
          required
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          placeholder="Enter their email address"
        />

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Staff ID"
            required
            value={form.staff_id}
            onChange={(e) => setForm((f) => ({ ...f, staff_id: e.target.value }))}
          />
          <TextField
            label="Phone number"
            type="tel"
            required
            value={form.phone_number}
            onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))}
          />
        </div>

        <SelectField
          label="Role"
          required
          placeholder="Select role"
          value={form.role}
          onChange={(e) => handleRoleChange(e.target.value as Role)}
          options={STAFF_ROLES.map((r) => ({ value: r, label: ROLE_LABELS[r] }))}
        />

        {deptScoped && (
          <SelectField
            label="Department"
            required
            placeholder="Select department"
            value={form.department_name}
            onChange={(e) => setForm((f) => ({ ...f, department_name: e.target.value }))}
            options={DEPARTMENT_OPTIONS}
            hint="This role is department-scoped -- issues route to it based on the student's own department."
          />
        )}

        <div className="rounded-lg bg-slate-50 p-3.5 text-xs text-slate-500">
          A secure temporary password is generated automatically. There's nothing to set here -- it's shown once,
          right after the account is created.
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70"
        >
          {isSubmitting ? <Spinner className="size-4 text-white" /> : <UserPlus className="size-4" />}
          Create Staff Account
        </button>
      </form>
    </div>
  )
}
