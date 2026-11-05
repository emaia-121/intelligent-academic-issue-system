import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Alert } from '@/components/ui/Alert'
import { NotTracked } from '@/components/ui/StatusBadge'
import { useAuth } from '@/context/AuthContext'
import { ROLE_LABELS, type Role } from '@/types'
import { initials } from '@/lib/format'
import {
  getCurrentUserProfile,
  type CurrentUserProfileResult,
} from '@/api/auth'
import { extractErrorMessage } from '@/api/client'

export function Profile() {
  const { user } = useAuth()

  const [detail, setDetail] = useState<CurrentUserProfileResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    getCurrentUserProfile()
      .then((data) => {
        if (!cancelled) {
          setDetail(data)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            extractErrorMessage(
              err,
              'Could not load full profile details.'
            )
          )
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (!user) return null

  const profile = detail ?? user

  const displayName =
    [profile.first_name, profile.last_name]
      .filter(Boolean)
      .join(' ') || profile.email

  const role = profile.role as Role

  const rows: { label: string; value: string | null | undefined }[] = [
    { label: 'Email', value: profile.email },
    { label: 'Role', value: ROLE_LABELS[role] },
    { label: 'Department', value: profile.department_name },
    ...(role === 'student'
      ? [
          {
            label: 'Matriculation Number',
            value: detail?.matric_number ?? user.matric_number,
          },
          {
            label: 'Level',
            value: detail?.level ?? user.level,
          },
        ]
      : [
          {
            label: 'Staff ID',
            value: detail?.staff_id ?? user.staff_id,
          },
        ]),
  ]

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Profile"
        description="Your account details."
      />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      <div className="card p-6">
        <div className="flex items-center gap-4 border-b border-slate-100 pb-5">
          <div className="flex size-14 items-center justify-center rounded-full bg-brand-100 text-lg font-bold text-brand-700">
            {initials(displayName)}
          </div>

          <div>
            <p className="text-base font-semibold text-slate-900">
              {displayName}
            </p>
            <p className="text-sm text-slate-500">
              {ROLE_LABELS[role]}
            </p>
          </div>
        </div>

        <dl className="mt-5 space-y-4">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex items-center justify-between gap-4 text-sm"
            >
              <dt className="shrink-0 text-slate-500">
                {row.label}
              </dt>

              <dd className="min-w-0 text-right font-medium text-slate-800">
                {row.value ? (
                  row.value
                ) : (
                  <NotTracked
                    label={`${row.label} not available yet`}
                  />
                )}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}