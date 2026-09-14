import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { queryKeys } from '@/lib/queryClient'

interface PendingGroup {
  key: string
  icon: string
  title: (count: number) => string
  description: string
  href: string
}

const GROUPS: PendingGroup[] = [
  {
    key: 'expenses_without_document',
    icon: '⚠️',
    title: (n) => `${n} despesa${n === 1 ? '' : 's'} sem documento`,
    description: 'Anexe o comprovante correspondente a cada lançamento.',
    href: '/despesas?doc=PENDING',
  },
  {
    key: 'documents_human_review',
    icon: '⚠️',
    title: (n) => `${n} documento${n === 1 ? '' : 's'} precisa${n === 1 ? '' : 'm'} de revisão`,
    description: 'A leitura automática (OCR) teve baixa confiança e precisa de confirmação humana.',
    href: '/documentos?status=HUMAN_REVIEW',
  },
  {
    key: 'documents_duplicated',
    icon: '⚠️',
    title: (n) => `${n} documento${n === 1 ? '' : 's'} possivelmente duplicado${n === 1 ? '' : 's'}`,
    description: 'Confirme se não é um envio repetido do mesmo comprovante.',
    href: '/documentos?status=POSSIBLE_DUPLICATE',
  },
  {
    key: 'expenses_pending_information',
    icon: '⚠️',
    title: (n) => `${n} despesa${n === 1 ? '' : 's'} com informação incompleta`,
    description: 'Faltam dados como valor, data ou fornecedor.',
    href: '/despesas?status=PENDING_INFORMATION',
  },
  {
    key: 'revenues_pending_information',
    icon: '⚠️',
    title: (n) => `${n} receita${n === 1 ? '' : 's'} com informação incompleta`,
    description: 'Faltam dados como valor, data ou doador.',
    href: '/receitas?status=PENDING_INFORMATION',
  },
]

export function PendingPage() {
  const summaryQuery = useQuery({ queryKey: queryKeys.financeSummary(), queryFn: () => api.finance.summary() })
  const documentsQuery = useQuery({ queryKey: queryKeys.reportsDocuments(), queryFn: () => api.reports.documents() })

  if (summaryQuery.isLoading || documentsQuery.isLoading) return <LoadingState label="Carregando pendências…" />
  if (summaryQuery.isError || documentsQuery.isError || !summaryQuery.data || !documentsQuery.data) {
    return (
      <ErrorState
        message="Não foi possível carregar as pendências."
        onRetry={() => {
          summaryQuery.refetch()
          documentsQuery.refetch()
        }}
      />
    )
  }

  const counts: Record<string, number> = {
    expenses_without_document: summaryQuery.data.expenses_without_document,
    documents_human_review: documentsQuery.data.human_review,
    documents_duplicated: documentsQuery.data.duplicated,
    expenses_pending_information: summaryQuery.data.pending_information_expenses,
    revenues_pending_information: summaryQuery.data.pending_information_revenues,
  }

  const activeGroups = GROUPS.filter((g) => counts[g.key] > 0)

  return (
    <Card>
      <CardHeader title="Pendências" subtitle="Itens que precisam da sua atenção" />
      <CardBody className="p-0">
        {activeGroups.length === 0 ? (
          <EmptyState title="Nenhuma pendência" description="Tudo certo por aqui." icon="✅" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {activeGroups.map((group) => (
              <PendingRow key={group.key} icon={group.icon} title={group.title(counts[group.key])} href={group.href}>
                {group.description}
              </PendingRow>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}

function PendingRow({ icon, title, href, children }: { icon: string; title: string; href: string; children: ReactNode }) {
  return (
    <li className="flex items-center justify-between gap-4 px-5 py-4">
      <div className="flex items-start gap-3">
        <span className="text-lg" aria-hidden="true">
          {icon}
        </span>
        <div>
          <p className="text-sm font-medium text-slate-800">{title}</p>
          <p className="text-xs text-slate-500">{children}</p>
        </div>
      </div>
      <Link to={href}>
        <Button variant="secondary" size="sm">
          Resolver
        </Button>
      </Link>
    </li>
  )
}
