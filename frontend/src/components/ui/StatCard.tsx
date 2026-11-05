import type { LucideIcon } from 'lucide-react'
import clsx from 'clsx'

type Tone = 'blue' | 'orange' | 'green' | 'slate' | 'red' | 'purple'

const TONE_CLASSES: Record<Tone, string> = {
  blue: 'bg-blue-50 text-blue-600',
  orange: 'bg-orange-50 text-orange-600',
  green: 'bg-emerald-50 text-emerald-600',
  slate: 'bg-slate-100 text-slate-600',
  red: 'bg-red-50 text-red-600',
  purple: 'bg-violet-50 text-violet-600',
}

export function StatCard({
  icon: Icon,
  tone = 'blue',
  value,
  label,
  sublabel,
  onClick,
}: {
  icon: LucideIcon
  tone?: Tone
  value: string | number
  label: string
  sublabel?: string
  onClick?: () => void
}) {
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick()
              }
            }
          : undefined
      }
      className={clsx(
        'card flex items-center gap-4 p-5',
        onClick && 'cursor-pointer transition hover:-translate-y-0.5 hover:shadow-md',
      )}
    >
      <div className={clsx('flex size-11 shrink-0 items-center justify-center rounded-xl', TONE_CLASSES[tone])}>
        <Icon className="size-5" />
      </div>

      <div className="min-w-0">
        <p className="text-2xl font-bold leading-tight text-slate-900">{value}</p>
        <p className="truncate text-sm font-medium text-slate-700">{label}</p>
        {sublabel && <p className="truncate text-xs text-slate-400">{sublabel}</p>}
      </div>
    </div>
  )
}