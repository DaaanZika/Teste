import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '@/api'
import { DocumentStatusBadge, ExpenseStatusBadge, RevenueStatusBadge } from '@/components/StatusBadges'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { formatCurrency, formatDate } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'

export function SearchPage() {
  const [searchParams] = useSearchParams()
  const term = (searchParams.get('q') ?? '').trim().toLowerCase()

  const documentsQuery = useQuery({ queryKey: queryKeys.documents(), queryFn: () => api.documents.list() })
  const expensesQuery = useQuery({ queryKey: queryKeys.expenses(), queryFn: () => api.expenses.list() })
  const revenuesQuery = useQuery({ queryKey: queryKeys.revenues(), queryFn: () => api.revenues.list() })

  const isLoading = documentsQuery.isLoading || expensesQuery.isLoading || revenuesQuery.isLoading
  const isError = documentsQuery.isError || expensesQuery.isError || revenuesQuery.isError

  const documents = useMemo(
    () =>
      (documentsQuery.data ?? []).filter((d) =>
        [d.original_filename, d.extracted_supplier_name, d.extracted_cnpj, d.extracted_cpf, d.extracted_document_number, d.extracted_description, d.extracted_amount]
          .filter(Boolean)
          .some((f) => String(f).toLowerCase().includes(term)),
      ),
    [documentsQuery.data, term],
  )

  const expenses = useMemo(
    () =>
      (expensesQuery.data ?? []).filter((e) =>
        [e.description, e.supplier_name, e.supplier_document, e.category, e.amount]
          .filter(Boolean)
          .some((f) => String(f).toLowerCase().includes(term)),
      ),
    [expensesQuery.data, term],
  )

  const revenues = useMemo(
    () =>
      (revenuesQuery.data ?? []).filter((r) =>
        [r.donor_name, r.donor_document, r.source_type, r.description, r.amount]
          .filter(Boolean)
          .some((f) => String(f).toLowerCase().includes(term)),
      ),
    [revenuesQuery.data, term],
  )

  if (!term) {
    return <EmptyState title="Digite algo para buscar" description="Fornecedor, valor, CNPJ, número da nota, descrição ou data." icon="🔍" />
  }

  if (isLoading) return <LoadingState label="Buscando…" />
  if (isError) return <ErrorState message="Não foi possível concluir a busca." />

  const totalResults = documents.length + expenses.length + revenues.length

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-slate-500">
        {totalResults} resultado(s) para <span className="font-medium text-slate-700">"{searchParams.get('q')}"</span>
      </p>

      {totalResults === 0 ? (
        <EmptyState title="Nenhum resultado encontrado" icon="🔍" />
      ) : (
        <>
          {documents.length > 0 ? (
            <Card>
              <CardHeader title={`Documentos (${documents.length})`} />
              <CardBody className="flex flex-col gap-2 p-0">
                {documents.map((d) => (
                  <Link key={d.id} to={`/documentos/${d.id}`} className="flex items-center justify-between border-b border-slate-50 px-5 py-3 last:border-0 hover:bg-slate-50">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{d.original_filename}</p>
                      <p className="text-xs text-slate-500">
                        {d.extracted_supplier_name ?? '—'} · {formatDate(d.extracted_date)} · {formatCurrency(d.extracted_amount)}
                      </p>
                    </div>
                    <DocumentStatusBadge status={d.status} />
                  </Link>
                ))}
              </CardBody>
            </Card>
          ) : null}

          {expenses.length > 0 ? (
            <Card>
              <CardHeader title={`Despesas (${expenses.length})`} />
              <CardBody className="flex flex-col gap-2 p-0">
                {expenses.map((e) => (
                  <Link key={e.id} to={`/despesas/${e.id}`} className="flex items-center justify-between border-b border-slate-50 px-5 py-3 last:border-0 hover:bg-slate-50">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{e.description ?? e.supplier_name ?? 'Despesa'}</p>
                      <p className="text-xs text-slate-500">
                        {formatDate(e.date)} · {formatCurrency(e.amount)}
                      </p>
                    </div>
                    <ExpenseStatusBadge status={e.status} />
                  </Link>
                ))}
              </CardBody>
            </Card>
          ) : null}

          {revenues.length > 0 ? (
            <Card>
              <CardHeader title={`Receitas (${revenues.length})`} />
              <CardBody className="flex flex-col gap-2 p-0">
                {revenues.map((r) => (
                  <div key={r.id} className="flex items-center justify-between border-b border-slate-50 px-5 py-3 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{r.donor_name ?? r.source_type ?? 'Receita'}</p>
                      <p className="text-xs text-slate-500">
                        {formatDate(r.date)} · {formatCurrency(r.amount)}
                      </p>
                    </div>
                    <RevenueStatusBadge status={r.status} />
                  </div>
                ))}
              </CardBody>
            </Card>
          ) : null}
        </>
      )}
    </div>
  )
}
