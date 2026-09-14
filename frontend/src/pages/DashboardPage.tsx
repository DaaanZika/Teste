import { useQuery } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { formatCurrency } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'

// recharts is the single heaviest dependency in the bundle; it is only
// needed on this page, so it is code-split instead of shipped up front.
const FinanceChart = lazy(() => import('@/components/dashboard/FinanceChart').then((m) => ({ default: m.FinanceChart })))

export function DashboardPage() {
  const summaryQuery = useQuery({ queryKey: queryKeys.financeSummary(), queryFn: () => api.finance.summary() })
  const documentsQuery = useQuery({ queryKey: queryKeys.reportsDocuments(), queryFn: () => api.reports.documents() })
  const alertsQuery = useQuery({
    queryKey: queryKeys.complianceAlerts({ status: 'OPEN' }),
    queryFn: () => api.compliance.alerts({ status: 'OPEN' }),
  })

  const isLoading = summaryQuery.isLoading || documentsQuery.isLoading || alertsQuery.isLoading
  const isError = summaryQuery.isError || documentsQuery.isError || alertsQuery.isError

  if (isLoading) return <LoadingState label="Carregando dashboard…" />
  if (isError || !summaryQuery.data || !documentsQuery.data || !alertsQuery.data) {
    return (
      <ErrorState
        message="Não foi possível carregar os dados do dashboard."
        onRetry={() => {
          summaryQuery.refetch()
          documentsQuery.refetch()
          alertsQuery.refetch()
        }}
      />
    )
  }

  const summary = summaryQuery.data
  const documents = documentsQuery.data
  const alerts = alertsQuery.data

  const pendingCount =
    summary.expenses_without_document +
    summary.pending_information_expenses +
    summary.pending_information_revenues +
    documents.human_review +
    documents.duplicated

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <DashboardCard label="Receitas" value={formatCurrency(summary.total_revenues)} tone="success" />
        <DashboardCard label="Despesas" value={formatCurrency(summary.total_expenses)} tone="danger" />
        <DashboardCard
          label="Saldo"
          value={formatCurrency(summary.balance)}
          tone={Number(summary.balance) >= 0 ? 'brand' : 'danger'}
        />
        <DashboardCard label="Documentos" value={documents.total} />
        <Link to="/pendencias" className="rounded-xl">
          <DashboardCard label="Pendências" value={pendingCount} tone={pendingCount > 0 ? 'warning' : 'neutral'} />
        </Link>
        <Link to="/conformidade" className="rounded-xl">
          <DashboardCard label="Alertas" value={alerts.length} tone={alerts.length > 0 ? 'warning' : 'neutral'} />
        </Link>
      </div>

      <Card>
        <CardHeader title="Evolução financeira" subtitle="Receitas e despesas ao longo do período selecionado" />
        <CardBody>
          <Suspense fallback={<LoadingState label="Carregando gráfico…" />}>
            <FinanceChart />
          </Suspense>
        </CardBody>
      </Card>
    </div>
  )
}
