import { useState } from 'react'
import type { FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import { Alert, Badge, Button, Card, CardBody, CardHeader, Input, Select } from '@/components/ui'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { ROLE_LABELS } from '@/lib/roles'
import type { Role, UserRead } from '@/types/api'

/**
 * Org "⚙️ Administração" tab — strictly scoped to the caller's own
 * organization (the backend derives that from the session; nothing here
 * can reach another organization's data). Visão Geral / Usuários /
 * Organização / Atividade.
 */
const ORG_ROLE_OPTIONS: Role[] = ['OWNER', 'FINANCEIRO', 'OPERACIONAL', 'VISUALIZADOR']

type Tab = 'visao-geral' | 'usuarios' | 'organizacao' | 'atividade'

const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'visao-geral', label: 'Visão Geral' },
  { key: 'usuarios', label: 'Usuários' },
  { key: 'organizacao', label: 'Organização' },
  { key: 'atividade', label: 'Atividade' },
]

export function AdministracaoPage() {
  const [tab, setTab] = useState<Tab>('visao-geral')

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Administração</h1>
        <p className="text-sm text-slate-500">Usuários, permissões e dados da sua organização.</p>
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
      {tab === 'usuarios' && <UsuariosTab />}
      {tab === 'organizacao' && <OrganizacaoTab />}
      {tab === 'atividade' && <AtividadeTab />}
    </div>
  )
}

function VisaoGeralTab() {
  const usageQuery = useQuery({ queryKey: ['organization', 'usage'], queryFn: () => api.organization.usage() })

  if (usageQuery.isLoading) return <LoadingState />
  if (usageQuery.isError || !usageQuery.data) return <ErrorState onRetry={() => usageQuery.refetch()} />

  const usage = usageQuery.data
  const cards: Array<{ label: string; value: number }> = [
    { label: 'Campanhas', value: usage.campaigns_count },
    { label: 'Usuários', value: usage.users_count },
    { label: 'Usuários ativos', value: usage.active_users_count },
    { label: 'Documentos', value: usage.documents_count },
    { label: 'Documentos processados', value: usage.documents_processed_count },
    { label: 'Despesas', value: usage.expenses_count },
    { label: 'Receitas', value: usage.revenues_count },
  ]

  return (
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
  )
}

function UsuariosTab() {
  const queryClient = useQueryClient()
  const usersQuery = useQuery({ queryKey: ['users'], queryFn: () => api.users.list() })
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('VISUALIZADOR')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await api.users.create({ name, email, password, role })
      setShowForm(false)
      setName('')
      setEmail('')
      setPassword('')
      setRole('VISUALIZADOR')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível criar o usuário.')
    } finally {
      setSubmitting(false)
    }
  }

  async function toggleActive(user: UserRead) {
    await api.users.update(user.id, { active: !user.active })
    await refresh()
  }

  async function handleResetPassword(user: UserRead) {
    await api.users.resetPassword(user.id)
  }

  if (usersQuery.isLoading) return <LoadingState />
  if (usersQuery.isError || !usersQuery.data) return <ErrorState onRetry={() => usersQuery.refetch()} />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancelar' : '+ Novo Usuário'}
        </Button>
      </div>

      {showForm ? (
        <Card>
          <CardHeader title="Novo usuário" />
          <CardBody>
            {error ? (
              <Alert tone="danger" className="mb-4">
                {error}
              </Alert>
            ) : null}
            <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
              <Input label="Nome" required value={name} onChange={(e) => setName(e.target.value)} />
              <Input
                label="E-mail"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Input
                label="Senha inicial"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <Select
                label="Perfil"
                required
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
                options={ORG_ROLE_OPTIONS.map((r) => ({ value: r, label: ROLE_LABELS[r] }))}
              />
              <div className="sm:col-span-2">
                <Button type="submit" loading={submitting}>
                  Criar usuário
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      ) : null}

      {usersQuery.data.length === 0 ? (
        <EmptyState title="Nenhum usuário cadastrado" icon="👤" />
      ) : (
        <Card>
          <Table<UserRead>
            rowKey={(u) => u.id}
            columns={[
              { key: 'name', header: 'Nome', render: (u) => u.name },
              { key: 'email', header: 'E-mail', render: (u) => u.email ?? '—' },
              { key: 'role', header: 'Perfil', render: (u) => ROLE_LABELS[u.role] ?? u.role },
              {
                key: 'active',
                header: 'Status',
                render: (u) => (
                  <Badge tone={u.active ? 'success' : 'neutral'}>{u.active ? 'Ativo' : 'Desativado'}</Badge>
                ),
              },
              {
                key: 'actions',
                header: '',
                align: 'right',
                render: (u) => (
                  <div className="flex justify-end gap-2">
                    <Button variant="secondary" size="sm" onClick={() => void handleResetPassword(u)}>
                      Redefinir senha
                    </Button>
                    <Button
                      variant={u.active ? 'danger' : 'secondary'}
                      size="sm"
                      onClick={() => void toggleActive(u)}
                    >
                      {u.active ? 'Desativar' : 'Ativar'}
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={usersQuery.data}
          />
        </Card>
      )}
    </div>
  )
}

function OrganizacaoTab() {
  const queryClient = useQueryClient()
  const orgQuery = useQuery({ queryKey: ['organization'], queryFn: () => api.organization.get() })
  const [name, setName] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)

  if (orgQuery.isLoading) return <LoadingState />
  if (orgQuery.isError || !orgQuery.data) return <ErrorState onRetry={() => orgQuery.refetch()} />

  const org = orgQuery.data

  async function handleSave(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      await api.organization.update(name)
      await queryClient.invalidateQueries({ queryKey: ['organization'] })
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Dados da organização" />
      <CardBody>
        {editing ? (
          <form onSubmit={handleSave} className="flex max-w-sm flex-col gap-3">
            <Input label="Nome" required defaultValue={org.name} onChange={(e) => setName(e.target.value)} />
            <div className="flex gap-2">
              <Button type="submit" size="sm" loading={saving}>
                Salvar
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => setEditing(false)}>
                Cancelar
              </Button>
            </div>
          </form>
        ) : (
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-slate-500">Nome</dt>
              <dd className="text-sm text-slate-900">{org.name}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">Identificador</dt>
              <dd className="text-sm text-slate-900">{org.slug}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">Status</dt>
              <dd>
                <Badge tone={org.status === 'ACTIVE' ? 'success' : 'warning'}>{org.status}</Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">Plano</dt>
              <dd className="text-sm text-slate-900">{org.plan}</dd>
            </div>
            <div className="sm:col-span-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setName(org.name)
                  setEditing(true)
                }}
              >
                Editar nome
              </Button>
            </div>
          </dl>
        )}
      </CardBody>
    </Card>
  )
}

function AtividadeTab() {
  const activityQuery = useQuery({ queryKey: ['audit', 'org'], queryFn: () => api.audit.list() })

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
        ]}
        rows={activityQuery.data}
      />
    </Card>
  )
}

/** Guard used by App.tsx — never renders the page for a role without
 * access, matching the "menus never render for unauthorized users" rule.
 * `isLoading` lets the caller avoid redirecting away during the initial
 * /auth/status fetch, when the role isn't known yet. */
export function useCanAccessAdministracao(): { allowed: boolean; isLoading: boolean } {
  const { data, isLoading } = useAuthStatus()
  const role = data?.user?.role
  return { allowed: role === 'OWNER' || role === 'ADMIN', isLoading }
}
