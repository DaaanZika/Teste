import { Alert } from '@/components/ui/Alert'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { http } from '@/lib/http'

export function SettingsPage() {
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
        <CardHeader title="Autenticação" subtitle="V1 local" />
        <CardBody>
          <p className="text-sm text-slate-600">
            Esta versão roda localmente com um único operador, sem login. O backend já expõe a estrutura para
            autenticação futura; quando um provedor real for adicionado, esta tela passará a mostrar a conta
            conectada.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Integrações futuras" subtitle="Ainda não implementadas nesta versão" />
        <CardBody className="flex flex-col gap-3">
          <Alert tone="info">
            Google Drive, Gmail, Google OAuth e exportação para o TSE fazem parte da arquitetura planejada, mas não
            estão ativos na V1 — tudo funciona localmente por enquanto.
          </Alert>
          <ul className="grid grid-cols-2 gap-2 text-sm text-slate-500 sm:grid-cols-4">
            <IntegrationBadge label="Google Drive" />
            <IntegrationBadge label="Gmail" />
            <IntegrationBadge label="Google OAuth" />
            <IntegrationBadge label="Exportação TSE" />
          </ul>
        </CardBody>
      </Card>
    </div>
  )
}

function IntegrationBadge({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 px-3 py-2 text-center text-xs text-slate-400">
      {label}
      <div className="mt-1 font-medium text-slate-500">Em breve</div>
    </div>
  )
}
