import { getIssue, listIssues } from '@/api/issues'
import type { IssueActivityRecord } from '@/types'

export interface NotificationEntry extends IssueActivityRecord {
  issueId: number
  issueTitle: string
}

/**
 * There is no notifications endpoint on the backend. Rather than fabricate
 * one, this builds a real activity feed by fetching a student's own issues
 * (real GET /api/issues/ + GET /api/issues/:id/ data) and flattening their
 * `activity_history` into one chronological list -- every entry is a
 * genuine activity record from the server.
 *
 * Originally lived inline in pages/student/Notifications.tsx; extracted
 * here so the Student Dashboard's compact "Recent Activity" widget can
 * reuse the exact same fetch instead of duplicating it.
 */
export async function getStudentActivityFeed(studentEmail: string | undefined): Promise<NotificationEntry[]> {
  const all = await listIssues()
  const mine = all.filter((i) => i.student === studentEmail)
  const details = await Promise.all(mine.map((i) => getIssue(i.id)))

  const flattened = details.flatMap((d) =>
    d.activity_history.map((a) => ({ ...a, issueId: d.id, issueTitle: d.title })),
  )
  flattened.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  return flattened
}
