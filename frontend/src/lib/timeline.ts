import type { IssueActivityRecord, IssueStatus } from '@/types'

export interface TimelineStep {
  key: IssueStatus
  label: string
  timestamp: string | null
  reached: boolean
}

// Matched against the real IssueActivity.action strings the backend
// actually writes (issues/workflow/service.py and
// issues/services/document_service.py -- verified directly against that
// code, not assumed). The previous "status changed to X" matchers for
// in_progress/resolved/closed didn't correspond to any action string the
// backend has ever produced (the real ones are "Issue Review Started",
// "Issue Resolved", "Issue Closed"), so those three steps highlighted
// correctly via STATUS_RANK below but never showed a timestamp.
const STEP_ORDER: { key: IssueStatus; label: string; matchers: RegExp[] }[] = [
  { key: 'pending', label: 'Issue Submitted', matchers: [/issue created/i] },
  { key: 'ready_for_review', label: 'Under Review', matchers: [/ready for review/i] },
  { key: 'in_progress', label: 'In Progress', matchers: [/issue review started/i] },
  { key: 'resolved', label: 'Resolved', matchers: [/issue resolved/i] },
  { key: 'closed', label: 'Closed', matchers: [/issue closed/i] },
]

const STATUS_RANK: Record<IssueStatus, number> = {
  pending: 0,
  ready_for_review: 1,
  in_progress: 2,
  resolved: 3,
  closed: 4,
}

/**
 * Builds the 5-step "Issue Submitted -> Under Review -> In Progress ->
 * Resolved -> Closed" stepper straight from the issue's real
 * `activity_history` + current `status` -- every timestamp shown is a real
 * activity record's `created_at`, never invented. Steps the issue hasn't
 * reached yet show no timestamp.
 */
export function buildStatusTimeline(
  activityHistory: IssueActivityRecord[],
  currentStatus: IssueStatus,
): TimelineStep[] {
  const currentRank = STATUS_RANK[currentStatus]

  return STEP_ORDER.map(({ key, label, matchers }) => {
    const match = activityHistory.find((a) => matchers.some((m) => m.test(a.action)))
    return {
      key,
      label,
      timestamp: match?.created_at ?? null,
      reached: STATUS_RANK[key] <= currentRank,
    }
  })
}
