import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { IssueStatus } from '@/types'

/**
 * The "Issues by Status" bar chart -- extracted from pages/reports/Reports.tsx
 * so Reports, the Admin Dashboard, and the Staff Dashboard all render the
 * exact same chart configuration (axes, colors, tooltip, bar radius) from
 * one place instead of copying the Recharts JSX three times.
 *
 * This component only renders -- it does not fetch or aggregate anything.
 * Callers supply pre-computed counts:
 *   - Reports.tsx / Admin Dashboard: overview.issues_by_status, from
 *     api/mock/reports.ts::getAdminOverview() (system-wide).
 *   - Staff Dashboard: api/mock/reports.ts::computeStatusCounts() run on
 *     that officer's own already-filtered issues (officer-scoped, never
 *     system-wide).
 * Both callers go through the same computeStatusCounts() function, so the
 * counting logic itself is never duplicated either -- only the input
 * issues[] differs.
 */
export function IssuesByStatusChart({
  counts,
  height = 260,
}: {
  counts: Record<IssueStatus, number>
  height?: number
}) {
  const data = Object.entries(counts).map(([status, count]) => ({ status, count }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="status" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
