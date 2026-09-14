import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'info' | 'warning' | 'danger' | 'success'

const toneClasses: Record<Tone, string> = {
  info: 'border-brand-200 bg-brand-50 text-brand-700',
  warning: 'border-warning/30 bg-warning-bg text-warning',
  danger: 'border-expense/30 bg-expense-bg text-expense',
  success: 'border-revenue/30 bg-revenue-bg text-revenue',
}

const icons: Record<Tone, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  danger: '⛔',
  success: '✅',
}

export function Alert({
  tone = 'info',
  title,
  children,
  action,
  className,
}: {
  tone?: Tone
  title?: ReactNode
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cn('flex items-start gap-3 rounded-lg border px-4 py-3 text-sm', toneClasses[tone], className)}
    >
      <span aria-hidden="true">{icons[tone]}</span>
      <div className="flex-1">
        {title ? <p className="font-medium">{title}</p> : null}
        {children ? <div className="mt-0.5 text-[13px] opacity-90">{children}</div> : null}
      </div>
      {action}
    </div>
  )
}
