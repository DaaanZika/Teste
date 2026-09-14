import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api'
import { DocumentLinkBadge, ExpenseStatusBadge, RevenueStatusBadge } from '@/components/StatusBadges'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import type { Column } from '@/components/ui/Table'
import { cn } from '@/lib/cn'
import { formatCurrency, formatDate, formatDateTime } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'
import type { AuditLogRead, DocumentsReportSummary, ExpenseReportRow, FinanceSummary, RevenueReportRow } from '@/types/api'

type Tab = 'summary' | 'expenses' | 'revenues' | 'documents' | 'audit'

const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'summary', label: 'Resumo financeiro' },
  { key: 'expenses', label: 'Despesas' },
  { key: 'revenues', label: 'Receitas' },
  { key: 'documents', label: 'Documentos' },
  { key: 'audit', label: 'Auditoria' },
]

export function ReportsPage() {
  const [tab, setTab] = useState<Tab>('summary')

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors',
              tab === t.key ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50',
            )}
          >
            {t.label}
          </button>
        ))}
        <Link to="/pendencias" className="rounded-full bg-white px-3.5 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50">
          Pendências →
        </Link>
        <Link to="/conformidade" className="rounded-full bg-white px-3.5 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50">
          Conformidade →
        </Link>
      </div>

      {tab === 'summary' && <SummaryReport />}
      {tab === 'expenses' && <ExpensesReport />}
      {tab === 'revenues' && <RevenuesReport />}
      {tab === 'documents' && <DocumentsReport />}
      {tab === 'audit' && <AuditReport />}
    </div>
  )
}

function SummaryReport() {
  const query = useQuery({ queryKey: queryKeys.reportsSummary(), queryFn: () => api.reports.summary() })
  return (
    <Card>
      <CardHeader title="Resumo financeiro" />
      <CardBody>
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError || !query.data ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : (
          <SummaryGrid summary={query.data} />
        )}
      </CardBody>
    </Card>
  )
}

function SummaryGrid({ summary }: { summary: FinanceSummary }) {
  return (
    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      <SummaryItem label="Total de receitas" value={formatCurrency(summary.total_revenues)} />
      <SummaryItem label="Total de despesas" value={formatCurrency(summary.total_expenses)} />
      <SummaryItem label="Saldo" value={formatCurrency(summary.balance)} />
      <SummaryItem label="Despesas sem documento" value={String(summary.expenses_without_document)} />
      <SummaryItem label="Despesas incompletas" value={String(summary.pending_information_expenses)} />
      <SummaryItem label="Receitas incompletas" value={String(summary.pending_information_revenues)} />
    </dl>
  )
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="tnum mt-1 text-lg font-semibold text-slate-800">{value}</dd>
    </div>
  )
}

function ExpensesReport() {
  const query = useQuery({ queryKey: queryKeys.reportsExpenses(), queryFn: () => api.reports.expenses() })
  const columns: Column<ExpenseReportRow>[] = [
    { key: 'date', header: 'Data', render: (r) => formatDate(r.date) },
    { key: 'supplier', header: 'Fornecedor', render: (r) => r.supplier_name ?? '—' },
    { key: 'category', header: 'Categoria', render: (r) => r.category ?? '—' },
    { key: 'amount', header: 'Valor', align: 'right', render: (r) => <span className="tnum">{formatCurrency(r.amount)}</span> },
    { key: 'document', header: 'Documento', render: (r) => <DocumentLinkBadge status={r.document_status} /> },
    { key: 'status', header: 'Status', render: (r) => <ExpenseStatusBadge status={r.status} /> },
  ]
  return (
    <Card>
      <CardHeader title="Relatório de despesas" />
      <CardBody className="p-0">
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState title="Nenhuma despesa cadastrada" icon="💸" />
        ) : (
          <Table columns={columns} rows={query.data} rowKey={(r) => r.id} />
        )}
      </CardBody>
    </Card>
  )
}

function RevenuesReport() {
  const query = useQuery({ queryKey: queryKeys.reportsRevenues(), queryFn: () => api.reports.revenues() })
  const columns: Column<RevenueReportRow>[] = [
    { key: 'date', header: 'Data', render: (r) => formatDate(r.date) },
    { key: 'source', header: 'Origem', render: (r) => r.source_type ?? '—' },
    { key: 'amount', header: 'Valor', align: 'right', render: (r) => <span className="tnum">{formatCurrency(r.amount)}</span> },
    { key: 'document', header: 'Documento', render: (r) => <DocumentLinkBadge status={r.document_status} /> },
    { key: 'status', header: 'Status', render: (r) => <RevenueStatusBadge status={r.status} /> },
  ]
  return (
    <Card>
      <CardHeader title="Relatório de receitas" />
      <CardBody className="p-0">
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState title="Nenhuma receita cadastrada" icon="💰" />
        ) : (
          <Table columns={columns} rows={query.data} rowKey={(r) => r.id} />
        )}
      </CardBody>
    </Card>
  )
}

function DocumentsReport() {
  const query = useQuery({ queryKey: queryKeys.reportsDocuments(), queryFn: () => api.reports.documents() })
  return (
    <Card>
      <CardHeader title="Relatório de documentos" />
      <CardBody>
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError || !query.data ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : (
          <DocumentsGrid summary={query.data} />
        )}
      </CardBody>
    </Card>
  )
}

function DocumentsGrid({ summary }: { summary: DocumentsReportSummary }) {
  return (
    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      <SummaryItem label="Total" value={String(summary.total)} />
      <SummaryItem label="Processados" value={String(summary.processed)} />
      <SummaryItem label="Pendentes" value={String(summary.pending)} />
      <SummaryItem label="Revisão necessária" value={String(summary.human_review)} />
      <SummaryItem label="Possíveis duplicados" value={String(summary.duplicated)} />
      <SummaryItem label="Falhas" value={String(summary.failed)} />
    </dl>
  )
}

function AuditReport() {
  const query = useQuery({ queryKey: queryKeys.audit(), queryFn: () => api.audit.list() })
  const columns: Column<AuditLogRead>[] = [
    { key: 'timestamp', header: 'Quando', render: (r) => formatDateTime(r.timestamp) },
    { key: 'entity', header: 'Registro', render: (r) => `${r.entity} · ${r.entity_id.slice(0, 8)}` },
    { key: 'action', header: 'Ação', render: (r) => r.action },
  ]
  return (
    <Card>
      <CardHeader title="Auditoria" subtitle="Histórico completo de alterações (nunca apagado)" />
      <CardBody className="p-0">
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState title="Nenhum registro de auditoria ainda" icon="🧾" />
        ) : (
          <Table columns={columns} rows={query.data.slice(0, 100)} rowKey={(r) => r.id} />
        )}
      </CardBody>
    </Card>
  )
}
