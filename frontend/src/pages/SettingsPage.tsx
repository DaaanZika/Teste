import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '@/api'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { useAuthStatus, useLogout } from '@/hooks/useAuthStatus'
import { http } from '@/lib/http'
import type { IntegrationStatus } from '@/types/api'

export function SettingsPage() {
  const authQuery = useAuthStatus()
  const integrationsQuery = useQuery({
    queryKey: ['integrations', 'status'],
    queryFn: () => api.integrations.status(),
    staleTime: 30_000,
  })
  const logout = useLogout()
  const queryClient = useQueryClient()
  const [disconnecting, setDisconnecting] = useState(false)

  const isAdmin = authQuery.data?.user?.role === 'ADMIN'

  async function handleDisconnectDrive() {
    setDisconnecting(true)
    try {
      await api.integrations.disconnectGoogleDrive()
      await queryClient.invalidateQueries({ queryKey: ['integrations', 'status'] })
    } finally {
      setDisconnecting(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Conexão" subtitle="Endereço do backend usado por este frontend" />
        <CardBody>
          <p className="rounded-lg bg-slate-50 px-3 py-2 font-mono text-sm text-slate-700">{http.defaults.baseURL}</p>
          <p className="mt-2 text-xs text-slate-500">
            Configurado via <code className="font-mono">VITE_API_BASE_URL</code>. Nenhuma senha, chave de API ou
            token é armazenado neste aplicativo.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Autenticação" subtitle="Estado real, lido de /auth/status" />
        <CardBody>
          {authQuery.isLoading ? <LoadingState /> : null}
          {authQuery.isError ? <ErrorState onRetry={() => authQuery.refetch()} /> : null}
          {authQuery.data ? (
            authQuery.data.auth_provider === 'local' ? (
              <p className="text-sm text-slate-600">
                Modo local: um único operador sem login, com todas as permissões liberadas. Defina{' '}
                <code className="font-mono">AUTH_PROVIDER=google</code> no backend para ativar login real via Google.
              </p>
            ) : (
              <div className="flex flex-col gap-2 text-sm text-slate-600">
                <p>Login via Google OAuth ativo.</p>
                {authQuery.data.authenticated && authQuery.data.user ? (
                  <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
                    <div>
                      <p className="font-medium text-slate-800">{authQuery.data.user.name}</p>
                      <p className="text-xs text-slate-500">
                        {authQuery.data.user.email} · papel {authQuery.data.user.role}
                      </p>
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => void logout()}>
                      Sair
                    </Button>
                  </div>
                ) : (
                  <Alert tone="info">Nenhuma sessão ativa nesta aba.</Alert>
                )}
              </div>
            )
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Integrações" subtitle="Estado real, lido de /integrations/status — nunca assumido" />
        <CardBody className="flex flex-col gap-4">
          {integrationsQuery.isLoading ? <LoadingState /> : null}
          {integrationsQuery.isError ? <ErrorState onRetry={() => integrationsQuery.refetch()} /> : null}
          {integrationsQuery.data ? (
            <>
              <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <IntegrationRow status={integrationsQuery.data.database} />
                <IntegrationRow status={integrationsQuery.data.ocr} />
                <IntegrationRow status={integrationsQuery.data.google_oauth} />
                <IntegrationRow status={integrationsQuery.data.google_drive} />
                <IntegrationRow status={integrationsQuery.data.gmail} />
                <IntegrationRow status={integrationsQuery.data.backup} />
              </ul>

              {isAdmin ? (
                <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
                  {integrationsQuery.data.google_drive.connected ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={disconnecting}
                      onClick={() => void handleDisconnectDrive()}
                    >
                      Desconectar Google Drive
                    </Button>
                  ) : integrationsQuery.data.google_oauth.connected ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        window.location.href = api.integrations.connectGoogleDriveUrl()
                      }}
                    >
                      Conectar Google Drive
                    </Button>
                  ) : (
                    <Alert tone="info" className="w-full">
                      Configure <code className="font-mono">GOOGLE_CLIENT_ID</code>/
                      <code className="font-mono">GOOGLE_CLIENT_SECRET</code> no backend para poder conectar o Google
                      Drive.
                    </Alert>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-500">Apenas administradores podem conectar ou desconectar integrações.</p>
              )}

              <Alert tone="info">
                Gmail ainda não está implementado. Este sistema não é o CONTA+JE e não envia nem simula o envio de
                dados ao TSE — nenhuma exportação aqui é uma prestação de contas oficial.
              </Alert>
            </>
          ) : null}
        </CardBody>
      </Card>
    </div>
  )
}

function IntegrationRow({ status }: { status: IntegrationStatus }) {
  return (
    <li className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
      <span className="font-medium text-slate-700">{status.name}</span>
      <span className="flex items-center gap-2">
        {status.detail ? <span className="text-xs text-slate-400">{status.detail}</span> : null}
        <Badge tone={status.connected ? 'success' : 'neutral'}>{status.connected ? 'Conectado' : 'Não conectado'}</Badge>
      </span>
    </li>
  )
}
