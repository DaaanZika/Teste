import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '@/api'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import type { Column } from '@/components/ui/Table'
import { cn } from '@/lib/cn'
import { formatCurrency } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'
import type { CategoryTotal, SupplierTotal } from '@/types/api'

type CategoryType = 'EXPENSE' | 'REVENUE'

export function FinancePage() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [categoryType, setCategoryType] = useState<CategoryType>('EXPENSE')

  const dateQuery = { start_date: startDate || undefined, end_date: endDate || undefined }

  const summaryQuery = useQuery({
    queryKey: queryKeys.financeSummary(dateQuery),
    queryFn: () => api.finance.summary(dateQuery),
  })

  const categoryQuery = useQuery({
    queryKey: queryKeys.financeTotalsCategory(undefined, categoryType),
    queryFn: () => api.finance.totalsByCategory(undefined, categoryType),
  })

  const supplierQuery = useQuery({
    queryKey: queryKeys.financeTotalsSupplier(),
    queryFn: () => api.finance.totalsBySupplier(),
  })

  const categoryColumns: Column<CategoryTotal>[] = [
    { key: 'category', header: 'Categoria', render: (r) => r.category },
    { key: 'total', header: 'Total', align: 'right', render: (r) => <span className="tnum">{formatCurrency(r.total)}</span> },
    { key: 'pct', header: '% do total', align: 'right', render: (r) => `${r.percentage_of_total}%` },
  ]

  const supplierColumns: Column<SupplierTotal>[] = [
    { key: 'supplier', header: 'Fornecedor', render: (r) => r.supplier_name },
    { key: 'total', header: 'Total', align: 'right', render: (r) => <span className="tnum">{formatCurrency(r.total)}</span> },
    { key: 'pct', header: '% do total', align: 'right', render: (r) => `${r.percentage_of_total}%` },
  ]

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader
          title="Filtrar por período"
          action={
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="rounded-md border border-slate-300 px-2 py-1.5"
              />
              <span>até</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="rounded-md border border-slate-300 px-2 py-1.5"
              />
              {(startDate || endDate) && (
                <button
                  onClick={() => {
                    setStartDate('')
                    setEndDate('')
                  }}
                  className="text-brand-600 hover:underline"
                >
                  Limpar
                </button>
              )}
            </div>
          }
        />
        <CardBody>
          {summaryQuery.isLoading ? (
            <LoadingState label="Carregando totais…" />
          ) : summaryQuery.isError || !summaryQuery.data ? (
            <ErrorState message="Não foi possível carregar os totais financeiros." onRetry={() => summaryQuery.refetch()} />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <DashboardCard label="Total Receitas" value={formatCurrency(summaryQuery.data.total_revenues)} tone="success" />
              <DashboardCard label="Total Despesas" value={formatCurrency(summaryQuery.data.total_expenses)} tone="danger" />
              <DashboardCard
                label="Saldo"
                value={formatCurrency(summaryQuery.data.balance)}
                tone={Number(summaryQuery.data.balance) >= 0 ? 'brand' : 'danger'}
              />
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Por categoria"
          action={
            <div className="flex gap-1 rounded-lg bg-slate-100 p-1 text-xs">
              <button
                onClick={() => setCategoryType('EXPENSE')}
                className={cn('rounded-md px-3 py-1 font-medium', categoryType === 'EXPENSE' ? 'bg-white shadow-sm' : 'text-slate-500')}
              >
                Despesas
              </button>
              <button
                onClick={() => setCategoryType('REVENUE')}
                className={cn('rounded-md px-3 py-1 font-medium', categoryType === 'REVENUE' ? 'bg-white shadow-sm' : 'text-slate-500')}
              >
                Receitas
              </button>
            </div>
          }
        />
        <CardBody className="p-0">
          {categoryQuery.isLoading ? (
            <LoadingState label="Carregando categorias…" />
          ) : categoryQuery.isError ? (
            <ErrorState message="Não foi possível carregar as categorias." onRetry={() => categoryQuery.refetch()} />
          ) : !categoryQuery.data || categoryQuery.data.length === 0 ? (
            <EmptyState title="Sem dados por categoria" description="Cadastre lançamentos com categoria para ver esta análise." icon="🏷️" />
          ) : (
            <Table columns={categoryColumns} rows={categoryQuery.data} rowKey={(r) => r.category} />
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Por fornecedor" subtitle="Despesas agrupadas por fornecedor" />
        <CardBody className="p-0">
          {supplierQuery.isLoading ? (
            <LoadingState label="Carregando fornecedores…" />
          ) : supplierQuery.isError ? (
            <ErrorState message="Não foi possível carregar os fornecedores." onRetry={() => supplierQuery.refetch()} />
          ) : !supplierQuery.data || supplierQuery.data.length === 0 ? (
            <EmptyState title="Sem dados por fornecedor" description="Cadastre despesas com fornecedor para ver esta análise." icon="🏢" />
          ) : (
            <Table columns={supplierColumns} rows={supplierQuery.data} rowKey={(r) => r.supplier_name} />
          )}
        </CardBody>
      </Card>
    </div>
  )
}
