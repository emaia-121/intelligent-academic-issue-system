import { format, formatDistanceToNow } from 'date-fns'

export function formatDateTime(iso: string): string {
  try {
    return format(new Date(iso), "MMM d, yyyy 'at' h:mm a")
  } catch {
    return iso
  }
}

export function formatDate(iso: string): string {
  try {
    return format(new Date(iso), 'MMM d, yyyy')
  } catch {
    return iso
  }
}

export function formatRelative(iso: string): string {
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true })
  } catch {
    return iso
  }
}

export function issueRef(id: number): string {
  return `#ISSUE-${new Date().getFullYear()}-${String(id).padStart(4, '0')}`
}

export function initials(name: string): string {
  return name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}
