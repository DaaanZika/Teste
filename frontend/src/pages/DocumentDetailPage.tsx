import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '@/api'
import { DocumentStatusBadge } from '@/components/StatusBadges'
import { DocumentReviewPanel } from '@/components/documents/DocumentReviewPanel'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { formatCurrency, formatDate, formatDateTime, formatDocument, formatFileSize } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'
import { http } from '@/lib/http'

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const query = useQuery({
    queryKey: queryKeys.document(id!),
    queryFn: () => api.documents.get(id!),
    enabled: Boolean(id),
  })

  if (query.isLoading) return <LoadingState label="Carregando documento…" />
  if (query.isError || !query.data) {
    return <ErrorState message="Não foi possível carregar este documento." onRetry={() => query.refetch()} />
  }

  const document = query.data
  const fileUrl = `${http.defaults.baseURL}/documents/${document.id}/file`
  const isImage = document.mime_type.startsWith('image/')
  const isPdf = document.mime_type === 'application/pdf'

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-700">
          ← Voltar
        </button>
        <DocumentStatusBadge status={document.status} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Arquivo" subtitle={`${document.original_filename} · ${formatFileSize(document.file_size_bytes)}`} />
          <CardBody>
            {isImage ? (
              <img src={fileUrl} alt={document.original_filename} className="w-full rounded-lg border border-slate-200 object-contain" />
            ) : isPdf ? (
              <iframe src={fileUrl} title={document.original_filename} className="h-[480px] w-full rounded-lg border border-slate-200" />
            ) : (
              <a href={fileUrl} target="_blank" rel="noreferrer" className="text-sm text-brand-600 underline">
                Abrir arquivo original
              </a>
            )}

            {document.possible_duplicate_of_id ? (
              <div className="mt-3">
                <Badge tone="warning">Possível duplicata</Badge>{' '}
                <Link to={`/documentos/${document.possible_duplicate_of_id}`} className="text-xs text-brand-600 underline">
                  ver documento original
                </Link>
              </div>
            ) : null}
          </CardBody>
        </Card>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Dados extraídos" subtitle="Revise e corrija se necessário" />
            <CardBody>
              <DocumentReviewPanel document={document} onConfirmed={() => query.refetch()} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Resumo" />
            <CardBody>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <SummaryField label="Valor" value={formatCurrency(document.extracted_amount)} />
                <SummaryField label="Data" value={formatDate(document.extracted_date)} />
                <SummaryField label="Fornecedor" value={document.extracted_supplier_name ?? '—'} />
                <SummaryField label="Nº do documento" value={document.extracted_document_number ?? '—'} />
                <SummaryField label="CNPJ" value={formatDocument(document.extracted_cnpj)} />
                <SummaryField label="CPF" value={formatDocument(document.extracted_cpf)} />
                <SummaryField label="Enviado em" value={formatDateTime(document.created_at)} />
                <SummaryField label="Hash (SHA-256)" value={document.sha256_hash.slice(0, 16) + '…'} />
              </dl>
            </CardBody>
          </Card>

          {document.ocr_text ? (
            <Card>
              <CardHeader title="OCR original" subtitle="Texto bruto extraído do documento" />
              <CardBody>
                <pre className="max-h-64 overflow-auto rounded-lg bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-600">
                  {document.ocr_text}
                </pre>
              </CardBody>
            </Card>
          ) : null}

          {document.status === 'UPLOADED' ? (
            <Card>
              <CardBody>
                <p className="mb-3 text-sm text-slate-600">Este documento ainda não foi processado.</p>
                <ReprocessButton documentId={document.id} onDone={() => query.refetch()} />
              </CardBody>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function SummaryField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  )
}

function ReprocessButton({ documentId, onDone }: { documentId: string; onDone: () => void }) {
  return (
    <Button
      onClick={async () => {
        await api.documents.process(documentId)
        onDone()
      }}
    >
      Processar documento (OCR)
    </Button>
  )
}
