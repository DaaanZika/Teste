import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'neutral' | 'success' | 'danger' | 'warning' | 'info'

const toneClasses: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700',
  success: 'bg-revenue-bg text-revenue',
  danger: 'bg-expense-bg text-expense',
  warning: 'bg-warning-bg text-warning',
  info: 'bg-brand-100 text-brand-700',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap',
        toneClasses[tone],
      )}
    >
      {children}
    </span>
  )
}
