import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '@/api'
import { DocumentLinkBadge, ExpenseStatusBadge } from '@/components/StatusBadges'
import { ExpenseForm } from '@/components/expenses/ExpenseForm'
import { Alert } from '@/components/ui/Alert'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { queryKeys } from '@/lib/queryClient'

export function ExpenseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const query = useQuery({
    queryKey: queryKeys.expense(id!),
    queryFn: () => api.expenses.get(id!),
    enabled: Boolean(id),
  })

  if (query.isLoading) return <LoadingState label="Carregando despesa…" />
  if (query.isError || !query.data) {
    return <ErrorState message="Não foi possível carregar esta despesa." onRetry={() => query.refetch()} />
  }

  const expense = query.data
  const missing = expense.missing_fields ? expense.missing_fields.split(',').map((f) => f.trim()) : []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-700">
          ← Voltar
        </button>
        <div className="flex gap-2">
          <ExpenseStatusBadge status={expense.status} />
          <DocumentLinkBadge status={expense.document_status} />
        </div>
      </div>

      {missing.length > 0 ? (
        <Alert tone="warning" title="Informações pendentes">
          Faltam: {missing.join(', ')}.
        </Alert>
      ) : null}

      {expense.source_text ? (
        <Alert tone="info" title="Criado a partir de lançamento rápido">
          “{expense.source_text}”
        </Alert>
      ) : null}

      <Card>
        <CardHeader
          title="Detalhes da despesa"
          action={
            expense.document_id ? (
              <Link to={`/documentos/${expense.document_id}`} className="text-sm text-brand-600 underline">
                Ver documento vinculado
              </Link>
            ) : null
          }
        />
        <CardBody>
          <ExpenseForm initial={expense} onSuccess={() => query.refetch()} />
        </CardBody>
      </Card>
    </div>
  )
}
