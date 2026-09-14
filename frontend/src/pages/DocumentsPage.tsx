import { useQuery } from '@tanstack/react-query'
import { useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/api'
import { DocumentStatusBadge } from '@/components/StatusBadges'
import { FileDropzone } from '@/components/documents/FileDropzone'
import { useUploadQueue } from '@/components/documents/UploadQueue'
import { CameraIcon, SearchIcon } from '@/components/icons'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Select } from '@/components/ui/Input'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { Table } from '@/components/ui/Table'
import type { Column } from '@/components/ui/Table'
import { formatDate, formatFileSize } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'
import type { DocumentRead, DocumentStatus } from '@/types/api'

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Todos os status' },
  { value: 'UPLOADED', label: 'Enviado' },
  { value: 'PROCESSING', label: 'Processando' },
  { value: 'PROCESSED', label: 'Processado' },
  { value: 'HUMAN_REVIEW', label: 'Revisão necessária' },
  { value: 'POSSIBLE_DUPLICATE', label: 'Possível duplicidade' },
  { value: 'FAILED', label: 'Falha' },
]

export function DocumentsPage() {
  const [searchParams] = useSearchParams()
  const capture = searchParams.get('capturar') === '1'
  const navigate = useNavigate()

  const [statusFilter, setStatusFilter] = useState(() => searchParams.get('status') ?? '')
  const [search, setSearch] = useState('')
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const query = useQuery({
    queryKey: queryKeys.documents({ status: statusFilter || undefined }),
    queryFn: () => api.documents.list({ status: (statusFilter || undefined) as DocumentStatus | undefined }),
  })

  const { handleFiles, queueNode } = useUploadQueue()

  const filtered = useMemo(() => {
    if (!query.data) return []
    const term = search.trim().toLowerCase()
    if (!term) return query.data
    return query.data.filter((doc) =>
      [
        doc.original_filename,
        doc.extracted_supplier_name,
        doc.extracted_cnpj,
        doc.extracted_cpf,
        doc.extracted_document_number,
        doc.extracted_description,
      ]
        .filter(Boolean)
        .some((field) => field!.toLowerCase().includes(term)),
    )
  }, [query.data, search])

  const columns: Column<DocumentRead>[] = [
    { key: 'filename', header: 'Arquivo', render: (d) => <span className="font-medium text-slate-800">{d.original_filename}</span> },
    { key: 'date', header: 'Data', render: (d) => formatDate(d.extracted_date) },
    { key: 'supplier', header: 'Fornecedor', render: (d) => d.extracted_supplier_name ?? '—' },
    { key: 'size', header: 'Tamanho', render: (d) => formatFileSize(d.file_size_bytes) },
    { key: 'status', header: 'Status', render: (d) => <DocumentStatusBadge status={d.status} /> },
  ]

  return (
    <div className="flex flex-col gap-6">
      {capture ? (
        <Card className="border-brand-200 bg-brand-50">
          <CardBody>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-brand-700">
                <CameraIcon className="h-5 w-5" />
                Toque para abrir a câmera e fotografar um documento.
              </div>
              <button
                type="button"
                onClick={() => cameraInputRef.current?.click()}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Abrir câmera
              </button>
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(event) => {
                  if (event.target.files) handleFiles(Array.from(event.target.files))
                  event.target.value = ''
                }}
              />
            </div>
          </CardBody>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Enviar documento" subtitle="Notas fiscais, cupons, recibos e comprovantes" />
        <CardBody>
          <FileDropzone onFiles={handleFiles} />
        </CardBody>
      </Card>

      {queueNode}

      <Card>
        <CardHeader
          title="Documentos"
          action={
            <div className="flex flex-wrap items-center gap-2">
              <label className="relative">
                <span className="sr-only">Pesquisar documentos</span>
                <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Pesquisar…"
                  className="w-40 rounded-md border border-slate-300 py-1.5 pr-2 pl-8 text-xs outline-none focus:border-brand-500 sm:w-56"
                />
              </label>
              <Select
                options={STATUS_OPTIONS}
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="py-1.5 text-xs"
              />
            </div>
          }
        />
        <CardBody className="p-0">
          {query.isLoading ? (
            <LoadingState label="Carregando documentos…" />
          ) : query.isError ? (
            <ErrorState message="Não foi possível carregar os documentos." onRetry={() => query.refetch()} />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="Nenhum documento encontrado"
              description={search || statusFilter ? 'Ajuste os filtros ou envie um novo documento.' : 'Envie o primeiro documento para começar.'}
              icon="🗂️"
            />
          ) : (
            <Table columns={columns} rows={filtered} rowKey={(d) => d.id} onRowClick={(d) => navigate(`/documentos/${d.id}`)} />
          )}
        </CardBody>
      </Card>
    </div>
  )
}
