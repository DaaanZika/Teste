import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PlusIcon, SearchIcon } from '@/components/icons'
import { DocumentLinkBadge, RevenueStatusBadge } from '@/components/StatusBadges'
import { RevenueForm } from '@/components/revenues/RevenueForm'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Select } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import type { Column } from '@/components/ui/Table'
import { usePagination } from '@/hooks/usePagination'
import { api } from '@/api'
import { formatCurrency, formatDate, formatDocument } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'
import type { RevenueRead, RevenueStatus } from '@/types/api'

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'COMPLETE', label: 'Completo' },
  { value: 'PENDING_INFORMATION', label: 'Informação pendente' },
]

export function RevenuesPage() {
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get('status') ?? '')
  const [modalOpen, setModalOpen] = useState(false)

  const query = useQuery({
    queryKey: queryKeys.revenues({ status: statusFilter || undefined }),
    queryFn: () => api.revenues.list({ status: (statusFilter || undefined) as RevenueStatus | undefined }),
  })

  const filtered = useMemo(() => {
    const rows = query.data ?? []
    const term = search.trim().toLowerCase()
    if (!term) return rows
    return rows.filter((r) =>
      [r.donor_name, r.source_type, r.donor_document, r.description].filter(Boolean).some((f) => f!.toLowerCase().includes(term)),
    )
  }, [query.data, search])

  const { pageRows, page, totalPages, nextPage, prevPage, setPage } = usePagination(filtered, 10)

  const columns: Column<RevenueRead>[] = [
    { key: 'date', header: 'Data', render: (r) => formatDate(r.date) },
    { key: 'donor', header: 'Doador', render: (r) => r.donor_name ?? '—' },
    { key: 'document', header: 'CPF/CNPJ', render: (r) => formatDocument(r.donor_document) },
    { key: 'source', header: 'Origem', render: (r) => r.source_type ?? '—' },
    { key: 'amount', header: 'Valor', align: 'right', render: (r) => <span className="tnum">{formatCurrency(r.amount)}</span> },
    { key: 'doc', header: 'Documento', render: (r) => <DocumentLinkBadge status={r.document_status} /> },
    { key: 'status', header: 'Status', render: (r) => <RevenueStatusBadge status={r.status} /> },
  ]

  return (
    <>
      <Card>
        <CardHeader
          title="Receitas"
          subtitle={query.data ? `${query.data.length} lançamento(s)` : undefined}
          action={
            <div className="flex flex-wrap items-center gap-2">
              <label className="relative">
                <span className="sr-only">Pesquisar receitas</span>
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
              <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} onClick={() => setModalOpen(true)}>
                Nova receita
              </Button>
            </div>
          }
        />
        <CardBody className="p-0">
          {query.isLoading ? (
            <LoadingState label="Carregando receitas…" />
          ) : query.isError ? (
            <ErrorState message="Não foi possível carregar as receitas." onRetry={() => query.refetch()} />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="Nenhuma receita cadastrada"
              description="Registre a primeira receita da campanha."
              icon="💰"
              action={
                <button onClick={() => setModalOpen(true)} className="text-sm font-medium text-brand-600 hover:underline">
                  + Nova receita
                </button>
              }
            />
          ) : (
            <>
              <Table columns={columns} rows={pageRows} rowKey={(r) => r.id} />
              <Pagination page={page} totalPages={totalPages} onPrev={prevPage} onNext={nextPage} />
            </>
          )}
        </CardBody>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nova receita">
        <RevenueForm onSuccess={() => setModalOpen(false)} />
      </Modal>
    </>
  )
}
