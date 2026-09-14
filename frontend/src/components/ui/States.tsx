import type { ReactNode } from 'react'
import { Button } from '@/components/ui/Button'

/**
 * The four states every backend-dependent view must handle explicitly
 * (PROMPT 2 §26) — nothing renders a blank screen while waiting, finding
 * nothing, or failing.
 */

export function LoadingState({ label = 'Carregando…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-slate-500">
      <svg className="h-6 w-6 animate-spin text-brand-500" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
  icon = '📭',
}: {
  title: string
  description?: ReactNode
  action?: ReactNode
  icon?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center text-slate-500">
      <span className="text-3xl" aria-hidden="true">
        {icon}
      </span>
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description ? <p className="max-w-sm text-sm text-slate-500">{description}</p> : null}
      {action}
    </div>
  )
}

export function ErrorState({
  message = 'Não foi possível carregar os dados.',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <span className="text-3xl" aria-hidden="true">
        ⚠️
      </span>
      <p className="max-w-sm text-sm text-slate-600">{message}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Tentar novamente
        </Button>
      ) : null}
    </div>
  )
}
