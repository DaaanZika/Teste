import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'neutral' | 'success' | 'danger' | 'warning' | 'brand'

const toneClasses: Record<Tone, string> = {
  neutral: 'text-slate-900',
  success: 'text-revenue',
  danger: 'text-expense',
  warning: 'text-warning',
  brand: 'text-brand-600',
}

export function DashboardCard({
  label,
  value,
  tone = 'neutral',
  icon,
  hint,
}: {
  label: string
  value: ReactNode
  tone?: Tone
  icon?: ReactNode
  hint?: string
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
        {icon ? (
          <span className="text-slate-400" aria-hidden="true">
            {icon}
          </span>
        ) : null}
      </div>
      <p className={cn('tnum mt-2 text-xl font-semibold whitespace-nowrap sm:text-2xl lg:text-3xl', toneClasses[tone])}>
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-slate-400">{hint}</p> : null}
    </div>
  )
}
