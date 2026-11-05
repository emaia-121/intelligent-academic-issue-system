import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText } from 'lucide-react'
import clsx from 'clsx'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatusStepper } from '@/components/ui/StatusStepper'
import { ActivityTimeline } from '@/components/ui/ActivityTimeline'
import { DocumentUploadWidget, type RequiredDocSlot } from '@/components/ui/DocumentUploadWidget'
import { Alert } from '@/components/ui/Alert'
import { PageLoader } from '@/components/ui/Loading'
import { TextAreaField, SelectField } from '@/components/ui/FormField'
import {
  confirmResolution,
  forwardIssue,
  getIssue,
  manuallyAssignIssue,
  rejectResolution,
  requestMoreInformation,
  resolveIssue,
  sendBackIssue,
  startReview,
  uploadIssueDocument,
  submitAdditionalInformation,
} from '@/api/issues'
import { getStaffDirectory, type StaffDirectoryEntry } from '@/api/auth'
import { buildDocumentChecklist } from '@/lib/documentChecklist'
import { buildStatusTimeline } from '@/lib/timeline'
import { extractErrorMessage } from '@/api/client'
import { formatDateTime, issueRef } from '@/lib/format'
import { useAuth } from '@/context/AuthContext'
import { ISSUE_STATUS_LABELS, ROLE_LABELS, STAFF_ROLES, type IssueDetail, type IssueStatus } from '@/types'

/**
 * Assignment status is deliberately separate from workflow status (StatusBadge
 * above) -- Pending/In Progress/etc. describe where the issue is in the
 * workflow; Assigned/Unassigned describes whether the workflow engine's
 * automatic routing was able to find an officer to assign it to (see
 * Administrative Assignment Management on the backend). An issue can be
 * Pending and Assigned, or Pending and Unassigned -- the two are independent.
 */
function AssignmentBadge({ assignedTo }: { assignedTo: string | null }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold',
        assignedTo ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700',
      )}
    >
      {assignedTo ? 'Assigned' : 'Unassigned'}
    </span>
  )
}

export function IssueDetailPage() {
  const { id } = useParams<{ id: string }>()
  const issueId = Number(id)
  const navigate = useNavigate()
  const { user, roleGroup } = useAuth()

  const [issue, setIssue] = useState<IssueDetail | null>(null)
  const [docSlots, setDocSlots] = useState<RequiredDocSlot[]>([])
  const [error, setError] = useState<string | null>(null)
  const [uploadingId, setUploadingId] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await getIssue(issueId)
      setIssue(data)
      setDocSlots(buildDocumentChecklist(data.required_documents, data.documents))
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not load this issue.'))
    }
  }, [issueId])

  useEffect(() => {
    load()
  }, [load])

  if (error && !issue) {
    return (
      <div className="mx-auto max-w-3xl">
        <Alert variant="error">{error}</Alert>
      </div>
    )
  }

  if (!issue) return <PageLoader label="Loading issue…" />

  // issue.student / issue.assigned_to are IssueSerializer's `student.username`
  // / `assigned_to.username` (see issues/serializers.py) -- accounts/services.py
  // sets Django's User.username equal to the account's email for every account
  // created through registration/staff-creation, so comparing against the
  // logged-in user's email (the only identifier the login response returns)
  // is the correct match.
  const isOwner = roleGroup === 'student' && issue.student === user?.email
  const canManage = roleGroup !== 'student' && (issue.assigned_to === user?.email || user?.role === 'admin')
  const timeline = buildStatusTimeline(issue.activity_history, issue.status)

  const handleUpload = async (documentId: number, file: File) => {
    setError(null)
    setUploadingId(documentId)
    try {
      await uploadIssueDocument(issueId, documentId, file)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, 'Upload failed.'))
    } finally {
      setUploadingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="mb-3 flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="size-4" />
        Back
      </button>

      <PageHeader
        title={issue.title}
        description={`${issueRef(issue.id)} · Submitted ${formatDateTime(issue.created_at)}`}
        actions={
          <div className="flex items-center gap-2">
            <AssignmentBadge assignedTo={issue.assigned_to} />
            <StatusBadge status={issue.status} className="text-sm" />
          </div>
        }
      />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      <div className="grid min-w-0 gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <section className="card min-w-0 overflow-hidden p-6">
            <h2 className="text-sm font-semibold text-slate-800">Description</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">{issue.description}</p>

            <dl className="mt-5 grid min-w-0 grid-cols-1 gap-4 border-t border-slate-100 pt-5 text-sm">
              <div className="min-w-0">
                <dt className="text-xs text-slate-400">Category</dt>
                <dd className="mt-0.5 min-w-0 font-medium text-slate-700">
                  {issue.category}
                </dd>
              </div>

              <div className="min-w-0">
                <dt className="text-xs text-slate-400">Department</dt>
                <dd className="mt-0.5 min-w-0 font-medium text-slate-700">
                  {issue.department}
                </dd>
              </div>

              <div className="min-w-0">
                <dt className="text-xs text-slate-400">Student</dt>
                <dd
                  className="mt-0.5 min-w-0 max-w-full font-medium text-slate-700"
                  style={{
                    overflowWrap: 'anywhere',
                    wordBreak: 'break-word',
                  }}
                >
                  {issue.student}
                </dd>
              </div>

              <div className="min-w-0">
                <dt className="text-xs text-slate-400">Assigned to</dt>
                <dd
                  className="mt-0.5 min-w-0 max-w-full font-medium text-slate-700"
                  style={{
                    overflowWrap: 'anywhere',
                    wordBreak: 'break-word',
                  }}
                >
                  {issue.assigned_to ?? (
                    <span className="text-amber-600">Unassigned</span>
                  )}
                </dd>
              </div>
            </dl>

          </section>
        
          {isOwner && issue.status === 'pending' && issue.information_request && (
            <SubmitAdditionalInformationForm
              issue={issue}
              onDone={load}
            />
          )}

          <section className="card p-6">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800">
              <FileText className="size-4 text-slate-400" />
              Documents
            </h2>
            {docSlots.length === 0 ? (
              <p className="text-sm text-slate-400">No documents are required for this issue's category.</p>
            ) : isOwner && issue.status === 'pending' ? (
              <DocumentUploadWidget slots={docSlots} onUpload={handleUpload} uploadingId={uploadingId} />
            ) : (
              <ul className="divide-y divide-slate-50">
                {docSlots.map((slot) => (
                  <li key={slot.document_id} className="flex items-center justify-between py-2.5 text-sm">
                    <span className="text-slate-600">{slot.document_name}</span>
                    {slot.uploaded ? (
                      <a
                        href={slot.uploaded.file}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold text-brand-600 hover:text-brand-700"
                      >
                        View file
                      </a>
                    ) : (
                      <span className="text-slate-400">Not uploaded</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-800">Activity</h2>
            <ActivityTimeline activities={issue.activity_history} />
          </section>
        </div>

        <div className="min-w-0 space-y-6">
          <section className="card p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-800">Status Timeline</h2>
            <StatusStepper steps={timeline} />
          </section>

          {user?.role === 'admin' && !issue.assigned_to && (
            <ManualAssignPanel issue={issue} onAssigned={load} />
          )}

          {canManage && (
            <WorkflowActionsPanel
              issue={issue}
              onUpdated={load}
            />
          )}

          {issue.resolution_notes && (
            <section className="card p-6">
              <h2 className="mb-2 text-sm font-semibold text-slate-800">Resolution Notes</h2>
              <p className="text-sm leading-relaxed text-slate-600">{issue.resolution_notes}</p>
            </section>
          )}

          {issue.status === 'resolved' && (isOwner || user?.role === 'admin') && (
            <ResolutionResponsePanel issue={issue} onUpdated={load} />
          )}
        </div>
      </div>

      <Link
        to={roleGroup === 'student' ? '/student/issues' : '/staff/issues'}
        className="mt-6 inline-block text-sm font-medium text-slate-500 hover:text-slate-700"
      >
        ← Back to issue list
      </Link>
    </div>
  )
}

/**
 * Final stage of the issue lifecycle: an officer's Resolve action
 * (resolve_issue()) only ever moves an issue to 'resolved', never
 * 'closed' -- only the issue's own student (or an admin) can complete the
 * workflow from there, via confirm_resolution() / reject_resolution().
 * Officers have no path to 'closed' anywhere in the UI; it is only ever
 * reached through this panel's Confirm action.
 */
function ResolutionResponsePanel({ issue, onUpdated }: { issue: IssueDetail; onUpdated: () => void }) {
  const [isRejecting, setIsRejecting] = useState(false)
  const [explanation, setExplanation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleConfirm = async () => {
    setError(null)
    setIsSubmitting(true)
    try {
      await confirmResolution(issue.id)
      onUpdated()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not confirm this resolution.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReject = async () => {
    setError(null)
    if (!explanation.trim()) {
      setError('Explain why this resolution is not accepted before rejecting it.')
      return
    }
    setIsSubmitting(true)
    try {
      await rejectResolution(issue.id, explanation)
      setExplanation('')
      setIsRejecting(false)
      onUpdated()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not reject this resolution.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="card space-y-4 p-6">
      <div>
        <h2 className="text-sm font-semibold text-slate-800">Review Resolution</h2>
        <p className="mt-1 text-xs text-slate-400">
          Confirm if this resolves your issue, or reject it and explain what's still needed.
        </p>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {isRejecting ? (
        <div className="space-y-3">
          <TextAreaField
            label="Why isn't this resolved?"
            required
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Required: explain what still needs to be addressed."
            rows={3}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              className="flex h-10 flex-1 items-center justify-center rounded-lg bg-red-600 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-70"
            >
              Submit Rejection
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRejecting(false)
                setExplanation('')
                setError(null)
              }}
              disabled={isSubmitting}
              className="flex h-10 flex-1 items-center justify-center rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-70"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="flex h-10 flex-1 items-center justify-center rounded-lg bg-brand-600 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-70"
          >
            Confirm Resolution
          </button>
          <button
            type="button"
            onClick={() => setIsRejecting(true)}
            disabled={isSubmitting}
            className="flex h-10 flex-1 items-center justify-center rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-70"
          >
            Reject Resolution
          </button>
        </div>
      )}
    </section>
  )
}

/**
 * Administrative Assignment Management: manual assignment is only ever
 * offered for issues the workflow engine's automatic routing left
 * unassigned (assigned_to is null) -- it is not a general reassignment
 * tool. Submitting calls POST /issues/:id/assign/ (admin-only on the
 * backend), which delegates to workflow.service.manual_assign_officer --
 * the only other place besides perform_initial_assignment/forward_issue/
 * send_back_issue that ever writes Issue.assigned_to. Once assigned, this
 * panel disappears (issue.assigned_to is no longer null) and the issue
 * follows the normal workflow like any other assigned issue.
 */
function ManualAssignPanel({ issue, onAssigned }: { issue: IssueDetail; onAssigned: () => void }) {
  const [staff, setStaff] = useState<StaffDirectoryEntry[] | null>(null)
  const [officerId, setOfficerId] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    getStaffDirectory()
      .then((entries) => !cancelled && setStaff(entries))
      .catch((err) => !cancelled && setError(extractErrorMessage(err, 'Could not load staff directory.')))
    return () => {
      cancelled = true
    }
  }, [])

  const handleSubmit = async () => {
    setError(null)
    if (!officerId) {
      setError('Select an officer to assign this issue to.')
      return
    }
    setIsSubmitting(true)
    try {
      await manuallyAssignIssue(issue.id, Number(officerId), notes || undefined)
      setNotes('')
      setOfficerId('')
      onAssigned()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not assign this issue.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="card space-y-4 p-6">
      <div>
        <h2 className="text-sm font-semibold text-slate-800">Manual Assignment</h2>
        <p className="mt-1 text-xs text-slate-400">
          Automatic assignment could not find an officer for this issue. Assign one manually to bring it
          into the normal workflow.
        </p>
      </div>
      {error && <Alert variant="error">{error}</Alert>}

      <SelectField
        label="Officer"
        placeholder={staff === null ? 'Loading staff…' : 'Select an officer'}
        value={officerId}
        onChange={(e) => setOfficerId(e.target.value)}
        disabled={staff === null}
        options={(staff ?? []).map((s) => ({
          value: String(s.id),
          label: `${s.first_name} ${s.last_name} — ${s.role}${s.department_name ? ` · ${s.department_name}` : ''}`,
        }))}
      />

      <TextAreaField
        label="Reason (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional note explaining why this issue is being manually assigned."
        rows={3}
      />

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isSubmitting || staff === null}
        className="flex h-10 w-full items-center justify-center rounded-lg bg-brand-600 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-70"
      >
        Assign Issue
      </button>
    </section>
  )
}

type WorkflowAction = 'start' | 'forward' | 'send_back' | 'request_info' | 'resolve'

// Which officer-triggerable workflow actions are legal from each status --
// mirrors issues/workflow/service.py's own transitions exactly:
//   ready_for_review -> in_progress            (start_review)
//   in_progress -> ready_for_review (next role)  (forward_issue)
//   in_progress -> ready_for_review (prev role)  (send_back_issue)
//   in_progress -> pending                       (request_more_information)
//   in_progress -> resolved                      (resolve_issue)
// 'pending' (waiting on the student), 'resolved' (waiting on the student to
// confirm/reject -- a separate, not-yet-built flow) and 'closed' have no
// officer-triggerable action here, so they map to an empty list.
const ACTIONS_FOR_STATUS: Partial<Record<IssueStatus, { value: WorkflowAction; label: string }[]>> = {
  ready_for_review: [{ value: 'start', label: 'Start Review' }],
  in_progress: [
    { value: 'forward', label: 'Forward' },
    { value: 'send_back', label: 'Send Back' },
    { value: 'request_info', label: 'Request More Information' },
    { value: 'resolve', label: 'Resolve' },
  ],
}

// Valid dynamic-forward destinations for the "Other" category, mirroring
// workflow_service.forward_issue()'s own `valid_roles` set exactly: every
// staff role except admin. STAFF_ROLES is the same shared role vocabulary
// StaffCreate.tsx uses, so it already includes the six roles added for the
// 12-category workflow engine (department_admin, lecturer, bursary,
// registry, school_admin_office, dept_exam_officer) -- nothing is
// hardcoded separately here.
const FORWARD_TARGET_ROLES = STAFF_ROLES.filter((role) => role !== 'admin')

const ACTION_BUTTON_CLASS =
  'flex h-10 w-full items-center justify-center rounded-lg bg-brand-600 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-70'

/**
 * Replaces the legacy status-value panel. Rather than picking a target
 * *status*, the officer now picks a workflow *action* -- Start Review,
 * Forward, Send Back, Request More Information, or Resolve -- and each
 * action calls its own dedicated workflow endpoint directly
 * (issues/workflow/service.py), exactly reflecting what the backend
 * actually supports instead of the three-status subset the old
 * `PATCH /issues/:id/status/` endpoint could express.
 */
function WorkflowActionsPanel({ issue, onUpdated }: { issue: IssueDetail; onUpdated: () => void }) {
  const availableActions = ACTIONS_FOR_STATUS[issue.status] ?? []
  const [action, setAction] = useState<WorkflowAction | ''>(availableActions[0]?.value ?? '')

  useEffect(() => {
    setAction(availableActions[0]?.value ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issue.status])

  if (availableActions.length === 0) {
    return (
      <section className="card p-6">
        <h2 className="text-sm font-semibold text-slate-800">Workflow Actions</h2>
        <p className="mt-2 text-sm text-slate-400">
          This issue is {ISSUE_STATUS_LABELS[issue.status].toLowerCase()} and has no officer actions available right
          now.
        </p>
      </section>
    )
  }

  return (
    <section className="card space-y-4 p-6">
      <h2 className="text-sm font-semibold text-slate-800">Workflow Actions</h2>

      {availableActions.length > 1 && (
        <SelectField
          label="Action"
          value={action}
          onChange={(e) => setAction(e.target.value as WorkflowAction)}
          options={availableActions.map((a) => ({ value: a.value, label: a.label }))}
        />
      )}

      {action === 'start' && <StartReviewForm issue={issue} onDone={onUpdated} />}
      {action === 'forward' && <ForwardForm issue={issue} onDone={onUpdated} />}
      {action === 'send_back' && <SendBackForm issue={issue} onDone={onUpdated} />}
      {action === 'request_info' && <RequestInfoForm issue={issue} onDone={onUpdated} />}
      {action === 'resolve' && <ResolveForm issue={issue} onDone={onUpdated} />}
    </section>
  )
}

/** Start Review -- ready_for_review -> in_progress. No notes: start_review()
 * takes none and IssueStartReviewAPIView accepts no request body. */
function StartReviewForm({ issue, onDone }: { issue: IssueDetail; onDone: () => void }) {
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setError(null)
    setIsSubmitting(true)
    try {
      await startReview(issue.id)
      onDone()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not start review.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}
      <p className="text-sm text-slate-500">Begin working on this issue.</p>
      <button type="button" onClick={handleSubmit} disabled={isSubmitting} className={ACTION_BUTTON_CLASS}>
        Start Review
      </button>
    </div>
  )
}

/** Forward -- in_progress -> ready_for_review, next role in the category's
 * forward chain. `target_role` only applies (and only appears) when the
 * category is "Other" -- every other category is routed entirely by
 * WorkflowDefinition.forward_chain and the backend rejects a target_role
 * for those. Notes are optional (WorkflowForwardSerializer.notes is not
 * required). */
function ForwardForm({ issue, onDone }: { issue: IssueDetail; onDone: () => void }) {
  const isOther = issue.category === 'Other'
  const [notes, setNotes] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setError(null)
    if (isOther && !targetRole) {
      setError('Select which role or office to forward this issue to.')
      return
    }
    setIsSubmitting(true)
    try {
      await forwardIssue(issue.id, {
        notes: notes.trim() || undefined,
        target_role: isOther ? targetRole : undefined,
      })
      setNotes('')
      setTargetRole('')
      onDone()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not forward this issue.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}

      {isOther && (
        <SelectField
          label="Forward to"
          required
          placeholder="Select a role or office"
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          options={FORWARD_TARGET_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }))}
        />
      )}

      <TextAreaField
        label="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional notes for the next officer."
        rows={3}
      />

      <button type="button" onClick={handleSubmit} disabled={isSubmitting} className={ACTION_BUTTON_CLASS}>
        Forward
      </button>
    </div>
  )
}

/** Send Back -- in_progress -> ready_for_review, previous role per the
 * category's explicit backward transitions. Notes are optional: the
 * backend does not require them (WorkflowSendBackSerializer.notes is not
 * required, and send_back_issue() never raises MissingExplanationError). */
function SendBackForm({ issue, onDone }: { issue: IssueDetail; onDone: () => void }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setError(null)
    setIsSubmitting(true)
    try {
      await sendBackIssue(issue.id, notes.trim() || undefined)
      setNotes('')
      onDone()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not send this issue back.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}

      <TextAreaField
        label="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional notes explaining why this issue is being sent back."
        rows={3}
      />

      <button type="button" onClick={handleSubmit} disabled={isSubmitting} className={ACTION_BUTTON_CLASS}>
        Send Back
      </button>
    </div>
  )
}

/** Request More Information -- in_progress -> pending. Ownership doesn't
 * change. Notes are mandatory: request_more_information() raises
 * MissingExplanationError without one. */
function RequestInfoForm({ issue, onDone }: { issue: IssueDetail; onDone: () => void }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setError(null)
    if (!notes.trim()) {
      setError('Explain what information is needed from the student.')
      return
    }
    setIsSubmitting(true)
    try {
      await requestMoreInformation(issue.id, notes)
      setNotes('')
      onDone()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not request more information.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}

      <TextAreaField
        label="What's needed from the student"
        required
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Required: explain what information or documents the student needs to provide."
        rows={3}
      />

      <button type="button" onClick={handleSubmit} disabled={isSubmitting} className={ACTION_BUTTON_CLASS}>
        Request More Information
      </button>
    </div>
  )
}

function SubmitAdditionalInformationForm({
  issue,
  onDone,
}: {
  issue: IssueDetail
  onDone: () => void
}) {
  const [response, setResponse] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setError(null)

    if (!response.trim()) {
      setError('Provide the requested information before submitting.')
      return
    }

    setIsSubmitting(true)

    try {
      await submitAdditionalInformation(issue.id, response)
      setResponse('')
      onDone()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not submit additional information.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="card space-y-4 p-6"> 
      {error && <Alert variant="error">{error}</Alert>}

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <h3 className="text-sm font-semibold text-amber-900">
          Additional Information Requested
        </h3>

        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-amber-800">
          {issue.information_request}
        </p>
      </div>

      <TextAreaField
        label="Your response"
        required
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        placeholder="Provide the additional information requested by the officer."
        rows={4}
      />

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isSubmitting}
        className={ACTION_BUTTON_CLASS}
      >
        {isSubmitting ? 'Submitting…' : 'Submit Additional Information'}
      </button>
    </section>
  )
}

/** Resolve -- in_progress -> resolved. Only a final authority role for the
 * category may resolve. Notes are mandatory: resolve_issue() raises
 * MissingExplanationError without one -- the same validation the old
 * status panel enforced for this same transition. */
function ResolveForm({ issue, onDone }: { issue: IssueDetail; onDone: () => void }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setError(null)
    if (!notes.trim()) {
      setError('Resolution notes are required before resolving an issue.')
      return
    }
    setIsSubmitting(true)
    try {
      await resolveIssue(issue.id, notes)
      setNotes('')
      onDone()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not resolve this issue.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}

      <TextAreaField
        label="Resolution notes"
        required
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Required: describe how this issue was resolved."
        rows={4}
      />

      <button type="button" onClick={handleSubmit} disabled={isSubmitting} className={ACTION_BUTTON_CLASS}>
        Resolve
      </button>
    </div>
  )
}
