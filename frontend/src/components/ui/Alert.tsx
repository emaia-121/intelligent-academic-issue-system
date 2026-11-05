import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'
import clsx from 'clsx'
import type { ReactNode } from 'react'

type Variant = 'success' | 'error' | 'info'

const CONFIG: Record<Variant, { icon: typeof Info; classes: string; iconClasses: string }> = {
  success: {
    icon: CheckCircle2,
    classes: 'bg-emerald-50 text-emerald-800 border-emerald-100',
    iconClasses: 'text-emerald-500',
  },
  error: {
    icon: AlertCircle,
    classes: 'bg-red-50 text-red-800 border-red-100',
    iconClasses: 'text-red-500',
  },
  info: {
    icon: Info,
    classes: 'bg-blue-50 text-blue-800 border-blue-100',
    iconClasses: 'text-blue-500',
  },
}

export function Alert({
  variant = 'info',
  title,
  children,
  onDismiss,
}: {
  variant?: Variant
  title?: string
  children?: ReactNode
  onDismiss?: () => void
}) {
  const { icon: Icon, classes, iconClasses } = CONFIG[variant]
  return (
    <div className={clsx('flex items-start gap-3 rounded-xl border px-4 py-3 text-sm', classes)}>
      <Icon className={clsx('mt-0.5 size-4 shrink-0', iconClasses)} />
      <div className="flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={clsx(title && 'mt-0.5')}>{children}</div>}
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="shrink-0 text-current/60 hover:text-current" aria-label="Dismiss">
          <X className="size-4" />
        </button>
      )}
    </div>
  )
}
