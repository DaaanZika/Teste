import { useState } from 'react'
import type { FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import { Alert, Badge, Button, Card, CardBody, CardHeader, Input } from '@/components/ui'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { ROLE_LABELS } from '@/lib/roles'
import type { Organization, OrganizationStatus, UserRead } from '@/types/api'

/**
 * "👑 Administração da Plataforma" — exclusive to SUPER_ADMIN, invisible
 * to every other role (see useCanAccessPlatformAdmin below and the /admin
 * routes, gated backend-side by a plain role check, never a permission).
 * Every number shown here is a real query against the database at request
 * time — never fabricated or simulated data.
 */
type Tab = 'visao-geral' | 'organizacoes' | 'usuarios' | 'atividade'

const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'visao-geral', label: 'Visão Geral' },
  { key: 'organizacoes', label: 'Organizações' },
  { key: 'usuarios', label: 'Usuários' },
  { key: 'atividade', label: 'Atividade' },
]

export function PlatformAdminPage() {
  const [tab, setTab] = useState<Tab>('visao-geral')

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">👑 Administração da Plataforma</h1>
        <p className="text-sm text-slate-500">Visão global de todas as organizações — dados reais, nunca simulados.</p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className={
              'px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ' +
              (tab === item.key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-700')
            }
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'visao-geral' && <VisaoGeralTab />}
      {tab === 'organizacoes' && <OrganizacoesTab />}
      {tab === 'usuarios' && <UsuariosTab />}
      {tab === 'atividade' && <AtividadeTab />}
    </div>
  )
}

function VisaoGeralTab() {
  const metricsQuery = useQuery({ queryKey: ['admin', 'metrics'], queryFn: () => api.admin.metrics() })

  if (metricsQuery.isLoading) return <LoadingState />
  if (metricsQuery.isError || !metricsQuery.data) return <ErrorState onRetry={() => metricsQuery.refetch()} />

  const m = metricsQuery.data
  const cards: Array<{ label: string; value: number | string }> = [
    { label: 'Organizações (total)', value: m.organizations_total },
    { label: 'Organizações ativas', value: m.organizations_active },
    { label: 'Organizações suspensas', value: m.organizations_suspended },
    { label: 'Organizações bloqueadas', value: m.organizations_blocked },
    { label: 'Usuários (total)', value: m.users_total },
    { label: 'Usuários ativos', value: m.users_active },
    { label: 'Documentos processados', value: m.documents_processed },
    { label: 'Documentos com falha', value: m.documents_failed },
    { label: 'Despesas registradas', value: m.expenses_total },
    { label: 'Receitas registradas', value: m.revenues_total },
    { label: 'Armazenamento usado', value: formatBytes(m.storage_used_bytes) },
    { label: 'Eventos de auditoria (24h)', value: m.recent_audit_events },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <Badge tone={m.database_healthy ? 'success' : 'danger'}>
          Banco de dados: {m.database_healthy ? 'saudável' : 'com problema'}
        </Badge>
        <Badge tone={m.ocr_available ? 'success' : 'warning'}>OCR: {m.ocr_available ? 'disponível' : 'indisponível'}</Badge>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardBody>
              <p className="text-xs font-medium text-slate-500">{card.label}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{card.value}</p>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return `${value.toFixed(1)} ${units[i]}`
}

const STATUS_TONE: Record<OrganizationStatus, 'success' | 'warning' | 'danger'> = {
  ACTIVE: 'success',
  SUSPENDED: 'warning',
  BLOCKED: 'danger',
}

function OrganizacoesTab() {
  const queryClient = useQueryClient()
  const orgsQuery = useQuery({ queryKey: ['admin', 'organizations'], queryFn: () => api.admin.organizations() })
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', slug: '', owner_name: '', owner_email: '', owner_password: '' })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ['admin', 'organizations'] })
    await queryClient.invalidateQueries({ queryKey: ['admin', 'metrics'] })
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await api.admin.createOrganization(form)
      setShowForm(false)
      setForm({ name: '', slug: '', owner_name: '', owner_email: '', owner_password: '' })
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível criar a organização.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleStatusChange(org: Organization, status: OrganizationStatus) {
    await api.admin.setOrganizationStatus(org.id, status)
    await refresh()
  }

  if (orgsQuery.isLoading) return <LoadingState />
  if (orgsQuery.isError || !orgsQuery.data) return <ErrorState onRetry={() => orgsQuery.refetch()} />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancelar' : '+ Nova Organização'}
        </Button>
      </div>

      {showForm ? (
        <Card>
          <CardHeader title="Nova organização" subtitle="Cria a organização e seu primeiro usuário OWNER." />
          <CardBody>
            {error ? (
              <Alert tone="danger" className="mb-4">
                {error}
              </Alert>
            ) : null}
            <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Nome da organização"
                name="org_name"
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
              <Input
                label="Identificador (slug)"
                name="org_slug"
                required
                pattern="[a-z0-9]+(-[a-z0-9]+)*"
                placeholder="minha-campanha"
                value={form.slug}
                onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
              />
              <Input
                label="Nome do responsável (OWNER)"
                name="owner_name"
                required
                value={form.owner_name}
                onChange={(e) => setForm((f) => ({ ...f, owner_name: e.target.value }))}
              />
              <Input
                label="E-mail do responsável"
                name="owner_email"
                type="email"
                required
                value={form.owner_email}
                onChange={(e) => setForm((f) => ({ ...f, owner_email: e.target.value }))}
              />
              <Input
                label="Senha inicial"
                name="owner_password"
                type="password"
                minLength={8}
                required
                value={form.owner_password}
                onChange={(e) => setForm((f) => ({ ...f, owner_password: e.target.value }))}
              />
              <div className="sm:col-span-2">
                <Button type="submit" loading={submitting}>
                  Criar organização
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      ) : null}

      {orgsQuery.data.length === 0 ? (
        <EmptyState title="Nenhuma organização cadastrada" icon="🏢" />
      ) : (
        <Card>
          <Table<Organization>
            rowKey={(o) => o.id}
            columns={[
              { key: 'name', header: 'Nome', render: (o) => o.name },
              { key: 'slug', header: 'Identificador', render: (o) => o.slug },
              { key: 'plan', header: 'Plano', render: (o) => o.plan },
              {
                key: 'status',
                header: 'Status',
                render: (o) => <Badge tone={STATUS_TONE[o.status]}>{o.status}</Badge>,
              },
              {
                key: 'actions',
                header: '',
                align: 'right',
                render: (o) => (
                  <div className="flex justify-end gap-2">
                    {o.status !== 'ACTIVE' && (
                      <Button size="sm" variant="secondary" onClick={() => void handleStatusChange(o, 'ACTIVE')}>
                        Ativar
                      </Button>
                    )}
                    {o.status !== 'SUSPENDED' && (
                      <Button size="sm" variant="secondary" onClick={() => void handleStatusChange(o, 'SUSPENDED')}>
                        Suspender
                      </Button>
                    )}
                    {o.status !== 'BLOCKED' && (
                      <Button size="sm" variant="danger" onClick={() => void handleStatusChange(o, 'BLOCKED')}>
                        Bloquear
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
            rows={orgsQuery.data}
          />
        </Card>
      )}
    </div>
  )
}

function UsuariosTab() {
  const usersQuery = useQuery({ queryKey: ['admin', 'users'], queryFn: () => api.admin.allUsers() })

  if (usersQuery.isLoading) return <LoadingState />
  if (usersQuery.isError || !usersQuery.data) return <ErrorState onRetry={() => usersQuery.refetch()} />
  if (usersQuery.data.length === 0) return <EmptyState title="Nenhum usuário cadastrado" icon="👤" />

  return (
    <Card>
      <Table<UserRead>
        rowKey={(u) => u.id}
        columns={[
          { key: 'name', header: 'Nome', render: (u) => u.name },
          { key: 'email', header: 'E-mail', render: (u) => u.email ?? '—' },
          { key: 'role', header: 'Perfil', render: (u) => ROLE_LABELS[u.role] ?? u.role },
          { key: 'org', header: 'Organização', render: (u) => u.organization_id?.slice(0, 8) ?? '— (plataforma)' },
          {
            key: 'active',
            header: 'Status',
            render: (u) => <Badge tone={u.active ? 'success' : 'neutral'}>{u.active ? 'Ativo' : 'Desativado'}</Badge>,
          },
        ]}
        rows={usersQuery.data}
      />
    </Card>
  )
}

function AtividadeTab() {
  const activityQuery = useQuery({ queryKey: ['admin', 'activity'], queryFn: () => api.admin.activity() })

  if (activityQuery.isLoading) return <LoadingState />
  if (activityQuery.isError || !activityQuery.data) return <ErrorState onRetry={() => activityQuery.refetch()} />
  if (activityQuery.data.length === 0) return <EmptyState title="Nenhuma atividade registrada ainda" icon="📋" />

  return (
    <Card>
      <Table
        rowKey={(row) => row.id}
        columns={[
          { key: 'timestamp', header: 'Quando', render: (row) => new Date(row.timestamp).toLocaleString('pt-BR') },
          { key: 'action', header: 'Ação', render: (row) => row.action },
          { key: 'entity', header: 'Entidade', render: (row) => `${row.entity} (${row.entity_id.slice(0, 8)})` },
          { key: 'org', header: 'Organização', render: (row) => row.organization_id?.slice(0, 8) ?? '—' },
        ]}
        rows={activityQuery.data}
      />
    </Card>
  )
}

/** Guard used by App.tsx/nav — never renders for anyone but SUPER_ADMIN.
 * `isLoading` lets the caller avoid redirecting away during the initial
 * /auth/status fetch, when the role isn't known yet. */
export function useCanAccessPlatformAdmin(): { allowed: boolean; isLoading: boolean } {
  const { data, isLoading } = useAuthStatus()
  return { allowed: data?.user?.role === 'SUPER_ADMIN', isLoading }
}
