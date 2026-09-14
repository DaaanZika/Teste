import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api'
import { AlertTypeBadge } from '@/components/StatusBadges'
import { Alert } from '@/components/ui/Alert'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { formatDateTime } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'

const ENTITY_ROUTES: Record<string, string> = {
  document: '/documentos',
  expense: '/despesas',
  revenue: '/receitas',
}

export function CompliancePage() {
  const alertsQuery = useQuery({ queryKey: queryKeys.complianceAlerts(), queryFn: () => api.compliance.alerts() })
  const rulesQuery = useQuery({ queryKey: queryKeys.complianceRules(), queryFn: () => api.compliance.rules() })

  return (
    <div className="flex flex-col gap-6">
      <Alert tone="info" title="Sobre as regras de conformidade">
        As regras eleitorais desta versão ainda não foram cadastradas — nenhum valor, prazo ou limite legal é
        aplicado sem confirmação em fonte oficial do TSE. Os alertas abaixo vêm da validação automática de
        documentos e lançamentos (duplicidade, dados incompletos, revisão de OCR), não de uma infração confirmada.
      </Alert>

      <Card>
        <CardHeader title="Alertas" subtitle={alertsQuery.data ? `${alertsQuery.data.length} alerta(s)` : undefined} />
        <CardBody className="p-0">
          {alertsQuery.isLoading ? (
            <LoadingState label="Carregando alertas…" />
          ) : alertsQuery.isError ? (
            <ErrorState message="Não foi possível carregar os alertas." onRetry={() => alertsQuery.refetch()} />
          ) : !alertsQuery.data || alertsQuery.data.length === 0 ? (
            <EmptyState title="Nenhum alerta no momento" icon="✅" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {alertsQuery.data.map((alert) => {
                const rule = rulesQuery.data?.find((r) => r.id === alert.rule_id)
                const entityHref = alert.entity && alert.entity_id ? `${ENTITY_ROUTES[alert.entity] ?? ''}/${alert.entity_id}` : null

                return (
                  <li key={alert.id} className="flex flex-col gap-2 px-5 py-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-slate-800">{alert.title}</p>
                      <AlertTypeBadge type={alert.type} />
                    </div>
                    <p className="text-sm text-slate-600">{alert.message}</p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                      <span>{formatDateTime(alert.created_at)}</span>
                      {entityHref ? (
                        <Link to={entityHref} className="text-brand-600 hover:underline">
                          Ver registro afetado
                        </Link>
                      ) : null}
                      <span>
                        Regra: {rule ? `${rule.rule_name} (${rule.legal_source ?? 'fonte não informada'})` : 'nenhuma regra formal associada'}
                      </span>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Regras cadastradas" subtitle="Base de regras eleitorais (por fonte oficial do TSE)" />
        <CardBody className="p-0">
          {rulesQuery.isLoading ? (
            <LoadingState label="Carregando regras…" />
          ) : rulesQuery.isError ? (
            <ErrorState message="Não foi possível carregar as regras." onRetry={() => rulesQuery.refetch()} />
          ) : !rulesQuery.data || rulesQuery.data.length === 0 ? (
            <EmptyState
              title="Nenhuma regra cadastrada"
              description="Nesta versão, nenhuma regra eleitoral foi registrada sem confirmação de fonte oficial."
              icon="📖"
            />
          ) : (
            <ul className="divide-y divide-slate-100">
              {rulesQuery.data.map((rule) => (
                <li key={rule.id} className="px-5 py-4">
                  <p className="text-sm font-medium text-slate-800">{rule.rule_name}</p>
                  <p className="text-xs text-slate-500">{rule.description}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    Fonte: {rule.legal_source ?? '—'} {rule.article ? `· Art. ${rule.article}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
