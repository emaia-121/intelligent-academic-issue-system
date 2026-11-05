import type { LucideIcon } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'

/**
 * These nav items appear in the reference mockups but have zero specification
 * in the written blueprint and no backing backend model or endpoint. Rather
 * than invent behavior for them, they render as an honest "coming soon" state.
 */
export function ComingSoon({ title, icon }: { title: string; icon: LucideIcon }) {
  return (
    <div>
      <PageHeader title={title} />
      <EmptyState
        icon={icon}
        title="Coming soon"
        description="This section isn't backed by a spec or API yet. Check back once it's defined."
      />
    </div>
  )
}
