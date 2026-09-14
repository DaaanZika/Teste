import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/api'
import { DocumentLinkBadge, ExpenseStatusBadge } from '@/components/StatusBadges'
import { SearchIcon } from '@/components/icons'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Select } from '@/components/ui/Input'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import type { Column } from '@/components/ui/Table'
import { usePagination } from '@/hooks/usePagination'
import { formatCurrency, formatDate } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'
import { useQuickAdd } from '@/state/QuickAddContext'
import type { ExpenseRead, ExpenseStatus } from '@/types/api'

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'COMPLETE', label: 'Completo' },
  { value: 'PENDING_INFORMATION', label: 'Informação pendente' },
]

const DOCUMENT_OPTIONS = [
  { value: '', label: 'Todos os documentos' },
  { value: 'ATTACHED', label: 'Com documento' },
  { value: 'PENDING', label: 'Sem documento' },
]

type SortKey = 'date' | 'amount' | 'supplier_name'

export function ExpensesPage() {
  const navigate = useNavigate()
  const { openQuickAdd } = useQuickAdd()
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get('status') ?? '')
  const [docFilter, setDocFilter] = useState(() => searchParams.get('doc') ?? '')
  const [sortKey, setSortKey] = useState<SortKey>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  const query = useQuery({
    queryKey: queryKeys.expenses({ status: statusFilter || undefined }),
    queryFn: () => api.expenses.list({ status: (statusFilter || undefined) as ExpenseStatus | undefined }),
  })

  const filtered = useMemo(() => {
    const rows = query.data ?? []
    const term = search.trim().toLowerCase()
    const searched = term
      ? rows.filter((e) =>
          [e.description, e.supplier_name, e.category, e.supplier_document]
            .filter(Boolean)
            .some((field) => field!.toLowerCase().includes(term)),
        )
      : rows

    const byDocument = docFilter ? searched.filter((e) => e.document_status === docFilter) : searched

    const sorted = [...byDocument].sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1
      if (sortKey === 'amount') return (Number(a.amount ?? 0) - Number(b.amount ?? 0)) * dir
      if (sortKey === 'supplier_name') return (a.supplier_name ?? '').localeCompare(b.supplier_name ?? '') * dir
      return ((a.date ?? '') < (b.date ?? '') ? -1 : 1) * dir
    })
    return sorted
  }, [query.data, search, docFilter, sortKey, sortDirection])

  const { pageRows, page, totalPages, nextPage, prevPage, setPage } = usePagination(filtered, 10)

  function handleSort(key: string) {
    if (key === sortKey) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key as SortKey)
      setSortDirection('desc')
    }
    setPage(1)
  }

  const columns: Column<ExpenseRead>[] = [
    { key: 'date', header: 'Data', sortable: true, render: (e) => formatDate(e.date) },
    { key: 'description', header: 'Descrição', render: (e) => e.description ?? '—' },
    { key: 'supplier_name', header: 'Fornecedor', sortable: true, render: (e) => e.supplier_name ?? '—' },
    { key: 'category', header: 'Categoria', render: (e) => e.category ?? '—' },
    {
      key: 'amount',
      header: 'Valor',
      sortable: true,
      align: 'right',
      render: (e) => <span className="tnum">{formatCurrency(e.amount)}</span>,
    },
    { key: 'document', header: 'Documento', render: (e) => <DocumentLinkBadge status={e.document_status} /> },
    { key: 'status', header: 'Status', render: (e) => <ExpenseStatusBadge status={e.status} /> },
  ]

  return (
    <Card>
      <CardHeader
        title="Despesas"
        subtitle={query.data ? `${query.data.length} lançamento(s)` : undefined}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative">
              <span className="sr-only">Pesquisar despesas</span>
              <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setPage(1)
                }}
                placeholder="Pesquisar…"
                className="w-40 rounded-md border border-slate-300 py-1.5 pr-2 pl-8 text-xs outline-none focus:border-brand-500 sm:w-56"
              />
            </label>
            <Select
              options={STATUS_OPTIONS}
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value)
                setPage(1)
              }}
              className="py-1.5 text-xs"
            />
            <Select
              options={DOCUMENT_OPTIONS}
              value={docFilter}
              onChange={(event) => {
                setDocFilter(event.target.value)
                setPage(1)
              }}
              className="py-1.5 text-xs"
            />
          </div>
        }
      />
      <CardBody className="p-0">
        {query.isLoading ? (
          <LoadingState label="Carregando despesas…" />
        ) : query.isError ? (
          <ErrorState message="Não foi possível carregar as despesas." onRetry={() => query.refetch()} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="Nenhuma despesa cadastrada"
            description="Use o botão Adicionar Gasto para registrar a primeira despesa."
            icon="💸"
            action={
              <button onClick={openQuickAdd} className="text-sm font-medium text-brand-600 hover:underline">
                + Adicionar gasto
              </button>
            }
          />
        ) : (
          <>
            <Table
              columns={columns}
              rows={pageRows}
              rowKey={(e) => e.id}
              onRowClick={(e) => navigate(`/despesas/${e.id}`)}
              sortKey={sortKey}
              sortDirection={sortDirection}
              onSort={handleSort}
            />
            <Pagination page={page} totalPages={totalPages} onPrev={prevPage} onNext={nextPage} />
          </>
        )}
      </CardBody>
    </Card>
  )
}
