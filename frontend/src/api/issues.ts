import { apiClient } from './client'
import type {
  ApiEnvelope,
  CreateIssueResponse,
  Issue,
  IssueDetail,
  IssueStatus,
  UploadDocumentResult,
} from '@/types'

/** GET /api/issues/ -- returns every issue in the system (no server-side
 * scoping by student/officer exists yet), so student/staff "my issues" views
 * filter this list client-side by the logged-in username. See AuthContext.
 *
 * `unassigned: true` adds `?unassigned=true`, which the backend
 * (IssueListAPIView) translates to `assigned_to__isnull=True` -- isolating
 * exactly the workflow exceptions the workflow engine's automatic
 * assignment could not resolve an officer for. Omitting the param (the
 * default) preserves the original unfiltered behaviour exactly. */
export async function listIssues(params?: { unassigned?: boolean }): Promise<Issue[]> {
  const res = await apiClient.get<ApiEnvelope<Issue[]>>('/issues/', {
    params: params?.unassigned ? { unassigned: true } : undefined,
  })
  return res.data.data ?? []
}

/** GET /api/issues/:id/ */
export async function getIssue(issueId: number): Promise<IssueDetail> {
  const res = await apiClient.get<ApiEnvelope<IssueDetail>>(`/issues/${issueId}/`)
  if (!res.data.data) throw new Error(res.data.message || 'Issue not found.')
  return res.data.data
}

/** POST /api/issues/create/
 *
 * `category_id` is optional. Omit it for a normal submission -- the
 * backend internally runs the ML classifier and either creates the issue
 * outright (high confidence) or returns a `CreateIssuePendingResult`
 * asking the student to confirm the guess or pick a category manually
 * (medium/low confidence). Supply `category_id` on the follow-up call
 * (confirming the suggestion, or after manual selection) to create the
 * issue with that category directly -- the classifier is not invoked
 * again. See CreateIssueAPIView on the backend for the full contract. */
export async function createIssue(payload: {
  title: string
  description: string
  category_id?: number
}): Promise<CreateIssueResponse> {
  const res = await apiClient.post<ApiEnvelope<CreateIssueResponse>>('/issues/create/', payload)
  if (!res.data.data) throw new Error(res.data.message || 'Could not create issue.')
  return res.data.data
}

/** POST /api/issues/:id/upload-document/ (multipart) */
export async function uploadIssueDocument(
  issueId: number,
  documentId: number,
  file: File,
): Promise<UploadDocumentResult> {
  const form = new FormData()
  form.append('document_id', String(documentId))
  form.append('file', file)

  const res = await apiClient.post<ApiEnvelope<UploadDocumentResult>>(
    `/issues/${issueId}/upload-document/`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  if (!res.data.data) throw new Error(res.data.message || 'Upload failed.')
  return res.data.data
}

// --- Workflow engine actions -----------------------------------------------
// One function per dedicated workflow endpoint (issues/workflow/service.py,
// via issues/views.py's IssueStartReviewAPIView / IssueForwardAPIView /
// IssueSendBackAPIView / IssueRequestInfoAPIView / IssueResolveAPIView).
// These replace the legacy `PATCH /issues/:id/status/` endpoint as the
// primary way an officer moves an issue through the workflow -- that
// endpoint only ever supported in_progress/resolved/closed and could never
// express Forward, Send Back, or Request More Information. It still exists
// on the backend (untouched) but nothing in the UI calls it anymore.

export interface WorkflowActionResult {
  status: IssueStatus
  assigned_to: string | null
}

export interface ResolveIssueResult {
  status: IssueStatus
  resolution_notes: string
}

/** POST /api/issues/:id/start/ -- ready_for_review -> in_progress. The
 * assigned officer (or admin) begins working the issue. No notes. */
export async function startReview(issueId: number): Promise<WorkflowActionResult> {
  const res = await apiClient.post<ApiEnvelope<WorkflowActionResult>>(`/issues/${issueId}/start/`)
  if (!res.data.data) throw new Error(res.data.message || 'Could not start review.')
  return res.data.data
}

/** POST /api/issues/:id/forward/ -- in_progress -> ready_for_review,
 * reassigned to the next role in the category's fixed forward chain.
 * `target_role` is only meaningful (and only accepted by the backend) when
 * the issue's category is "Other" -- WorkflowDefinition.dynamic_forward --
 * every other category determines its destination entirely from
 * `forward_chain` and rejects the call if a target_role is supplied. */
export async function forwardIssue(
  issueId: number,
  payload: { notes?: string; target_role?: string } = {},
): Promise<WorkflowActionResult> {
  const res = await apiClient.post<ApiEnvelope<WorkflowActionResult>>(`/issues/${issueId}/forward/`, payload)
  if (!res.data.data) throw new Error(res.data.message || 'Could not forward this issue.')
  return res.data.data
}

/** POST /api/issues/:id/send-back/ -- in_progress -> ready_for_review,
 * reassigned to the previous role per the category's explicit backward
 * transitions. `notes` is optional on the backend
 * (WorkflowSendBackSerializer does not mark it required, and
 * send_back_issue() never raises MissingExplanationError for a missing
 * one) so it is not enforced as mandatory here either. */
export async function sendBackIssue(issueId: number, notes?: string): Promise<WorkflowActionResult> {
  const res = await apiClient.post<ApiEnvelope<WorkflowActionResult>>(`/issues/${issueId}/send-back/`, { notes })
  if (!res.data.data) throw new Error(res.data.message || 'Could not send this issue back.')
  return res.data.data
}

/** POST /api/issues/:id/request-info/ -- in_progress -> pending. Ownership
 * does not change. `notes` is mandatory on the backend
 * (request_more_information raises MissingExplanationError without one). */
export async function requestMoreInformation(issueId: number, notes: string): Promise<WorkflowActionResult> {
  const res = await apiClient.post<ApiEnvelope<WorkflowActionResult>>(`/issues/${issueId}/request-info/`, { notes })
  if (!res.data.data) throw new Error(res.data.message || 'Could not request more information.')
  return res.data.data
}


export async function submitAdditionalInformation(
  issueId: number,
  response: string,
): Promise<WorkflowActionResult> {
  const res = await apiClient.post<ApiEnvelope<WorkflowActionResult>>(
    `/issues/${issueId}/submit-info/`,
    { response },
  )
  if (!res.data.data) throw new Error(res.data.message || 'Could not submit additional information.')
  return res.data.data
}

/** POST /api/issues/:id/resolve/ -- in_progress -> resolved.
 * Only the assigned officer (or admin) may resolve an issue.
 * Resolution notes are required by the backend.
 */
export async function resolveIssue(
  issueId: number,
  resolutionNotes: string,
): Promise<ResolveIssueResult> {
  const res = await apiClient.post<ApiEnvelope<ResolveIssueResult>>(
    `/issues/${issueId}/resolve/`,
    { notes: resolutionNotes, },
  )

  if (!res.data.data) {
    throw new Error(res.data.message || 'Could not resolve this issue.')
  }

  return res.data.data
}

// --- Student confirmation / rejection ---------------------------------------
// The final stage of the issue lifecycle: an officer's resolve_issue() call
// only moves an issue to 'resolved', never 'closed' -- only the issue's own
// student (or an admin) can complete the workflow from there, via
// confirm_resolution() or reject_resolution() in issues/workflow/service.py.

export interface ConfirmResolutionResult {
  status: IssueStatus
}

/** POST /api/issues/:id/confirm/ -- resolved -> closed. Only the issue's
 * own student (or an admin) may confirm; no explanation required. */
export async function confirmResolution(issueId: number): Promise<ConfirmResolutionResult> {
  const res = await apiClient.post<ApiEnvelope<ConfirmResolutionResult>>(`/issues/${issueId}/confirm/`)
  if (!res.data.data) throw new Error(res.data.message || 'Could not confirm this resolution.')
  return res.data.data
}

/** POST /api/issues/:id/reject/ -- resolved -> pending. Only the issue's
 * own student (or an admin) may reject; `explanation` is mandatory
 * (reject_resolution raises MissingExplanationError without one). The
 * assigned officer and required documents are unchanged -- the issue does
 * not restart, it just goes back to waiting on the student. */
export async function rejectResolution(issueId: number, explanation: string): Promise<WorkflowActionResult> {
  const res = await apiClient.post<ApiEnvelope<WorkflowActionResult>>(`/issues/${issueId}/reject/`, { explanation })
  if (!res.data.data) throw new Error(res.data.message || 'Could not reject this resolution.')
  return res.data.data
}

/** POST /api/issues/:id/assign/ -- Administrative Assignment Management,
 * admin-only (backend: IsSystemAdmin). Manually assigns an officer to an
 * issue automatic assignment could not resolve -- see
 * issues.workflow.service.manual_assign_officer on the backend, the only
 * place (alongside perform_initial_assignment/forward_issue/send_back_issue)
 * that ever writes Issue.assigned_to. Not a general reassignment tool: the
 * backend rejects this call if the issue already has an assignee. */
export interface ManualAssignResult {
  issue_id: number
  status: IssueStatus
  assigned_to: string
}

export async function manuallyAssignIssue(
  issueId: number,
  officerId: number,
  notes?: string,
): Promise<ManualAssignResult> {
  const res = await apiClient.post<ApiEnvelope<ManualAssignResult>>(`/issues/${issueId}/assign/`, {
    officer_id: officerId,
    notes,
  })
  if (!res.data.data) throw new Error(res.data.message || 'Could not assign issue.')
  return res.data.data
}
