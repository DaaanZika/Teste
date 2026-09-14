import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { CheckIcon } from '@/components/icons'
import { Badge } from '@/components/ui/Badge'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Input'
import { api } from '@/api'
import { formatCurrency, formatDate } from '@/lib/format'
import { invalidateFinanceRelated } from '@/lib/queryClient'
import { useToast } from '@/state/ToastContext'
import type { ExpenseRead } from '@/types/api'

const EXAMPLES = ['R$ 850 gráfica ABC', 'Gasolina 230 reais ontem', 'Aluguel comitê 3500 dia 10', 'Uber 86,40']

export function QuickAddForm({ onCreated, onEdit }: { onCreated?: () => void; onEdit?: (expense: ExpenseRead) => void }) {
  const [text, setText] = useState('')
  const [result, setResult] = useState<ExpenseRead | null>(null)
  const { notify } = useToast()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (value: string) => api.expenses.quick(value),
    onSuccess: (expense) => {
      setResult(expense)
      setText('')
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      invalidateFinanceRelated()
      notify('Gasto adicionado com sucesso.', 'success')
      onCreated?.()
    },
    onError: (error: Error) => notify(error.message, 'error'),
  })

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!text.trim() || mutation.isPending) return
    mutation.mutate(text.trim())
  }

  const missing = result?.missing_fields
    ? result.missing_fields.split(',').map((f) => f.trim())
    : []

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <Textarea
          name="quick-expense-text"
          label="Digite o gasto…"
          placeholder='Ex: "R$ 850 gráfica ABC"'
          rows={2}
          value={text}
          onChange={(event) => setText(event.target.value)}
          autoFocus
        />
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setText(example)}
              className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:border-brand-300 hover:text-brand-600"
            >
              {example}
            </button>
          ))}
        </div>
        <Button type="submit" loading={mutation.isPending} disabled={!text.trim()}>
          Adicionar gasto
        </Button>
      </form>

      {result ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
            <CheckIcon className="h-4 w-4 text-revenue" />
            Gasto registrado
          </div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <Field label="Descrição" value={result.description ?? '—'} span />
            <Field label="Valor" value={formatCurrency(result.amount)} />
            <Field label="Data" value={formatDate(result.date)} />
            <Field label="Fornecedor" value={result.supplier_name ?? '—'} span />
            <Field label="Categoria" value={result.category ?? '—'} />
          </dl>

          {missing.length > 0 ? (
            <Alert tone="warning" title="Informações pendentes" className="mt-3">
              Faltam: {missing.join(', ')}. Você pode completar depois em Despesas.
            </Alert>
          ) : null}

          <div className="mt-3 flex items-center gap-2">
            <Badge tone={result.status === 'COMPLETE' ? 'success' : 'warning'}>
              {result.status === 'COMPLETE' ? 'Completo' : 'Informação pendente'}
            </Badge>
            {result.document_status === 'PENDING' ? <Badge tone="warning">⚠️ Documento pendente</Badge> : null}
          </div>

          <div className="mt-4 flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => onEdit?.(result)}>
              Editar detalhes
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setResult(null)}>
              Adicionar outro
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function Field({ label, value, span }: { label: string; value: string; span?: boolean }) {
  return (
    <div className={span ? 'col-span-2' : undefined}>
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  )
}
