import clsx from 'clsx'
import type { TimelineStep } from '@/lib/timeline'
import { formatDateTime } from '@/lib/format'

export function StatusStepper({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="space-y-0">
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1
        return (
          <li key={step.key} className="relative flex gap-3 pb-6 last:pb-0">
            {!isLast && (
              <span
                className={clsx(
                  'absolute left-[5px] top-3 h-full w-px',
                  step.reached ? 'bg-brand-200' : 'bg-slate-200',
                )}
              />
            )}
            <span
              className={clsx(
                'relative mt-1 size-2.5 shrink-0 rounded-full ring-4',
                step.reached ? 'bg-brand-600 ring-brand-100' : 'bg-slate-300 ring-slate-100',
              )}
            />
            <div className="min-w-0 pb-0.5">
              <p className={clsx('text-sm font-medium', step.reached ? 'text-slate-800' : 'text-slate-400')}>
                {step.label}
              </p>
              <p className="text-xs text-slate-400">{step.timestamp ? formatDateTime(step.timestamp) : '—'}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
