import { Button } from '@/components/ui/Button'

export function Pagination({
  page,
  totalPages,
  onPrev,
  onNext,
}: {
  page: number
  totalPages: number
  onPrev: () => void
  onNext: () => void
}) {
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-sm text-slate-500">
      <span>
        Página {page} de {totalPages}
      </span>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={onPrev} disabled={page <= 1}>
          Anterior
        </Button>
        <Button variant="secondary" size="sm" onClick={onNext} disabled={page >= totalPages}>
          Próxima
        </Button>
      </div>
    </div>
  )
}
