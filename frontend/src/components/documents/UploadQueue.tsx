import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { api, toAppError } from '@/api'
import { DocumentReviewPanel } from '@/components/documents/DocumentReviewPanel'
import { CheckIcon } from '@/components/icons'
import { DocumentStatusBadge } from '@/components/StatusBadges'
import { Card, CardBody } from '@/components/ui/Card'
import type { DocumentRead } from '@/types/api'

type Stage = 'uploading' | 'processing' | 'review' | 'done' | 'error'

interface QueueItem {
  id: string
  fileName: string
  stage: Stage
  document?: DocumentRead
  error?: string
  possibleDuplicate?: boolean
}

const STAGE_LABELS: Record<Stage, string> = {
  uploading: 'Enviando…',
  processing: 'Processando (OCR e extração de dados)…',
  review: 'Extração concluída — revise os dados',
  done: 'Concluído',
  error: 'Falhou',
}

let nextId = 1

/**
 * Drives the real upload -> process pipeline (PROMPT 2 §9) for one or more
 * files and renders each file's progress + the OCR review step inline.
 * There is no fake intermediate step: "Enviando" and "Processando" map to
 * the two real backend calls (POST /documents/upload, POST
 * /documents/{id}/process) — nothing here simulates data.
 */
export function useUploadQueue(onDocumentReady?: (doc: DocumentRead) => void): {
  handleFiles: (files: File[]) => void
  queueNode: ReactNode
} {
  const [items, setItems] = useState<QueueItem[]>([])
  const queryClient = useQueryClient()

  function updateItem(id: string, patch: Partial<QueueItem>) {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)))
  }

  async function enqueue(file: File) {
    const id = String(nextId++)
    setItems((prev) => [{ id, fileName: file.name, stage: 'uploading' }, ...prev])

    try {
      const uploadResult = await api.documents.upload(file)
      queryClient.invalidateQueries({ queryKey: ['documents'] })

      if (uploadResult.possible_duplicate) {
        updateItem(id, { stage: 'done', document: uploadResult.document, possibleDuplicate: true })
        return
      }

      updateItem(id, { stage: 'processing', document: uploadResult.document })
      const processed = await api.documents.process(uploadResult.document.id)
      queryClient.invalidateQueries({ queryKey: ['documents'] })

      updateItem(id, { stage: 'review', document: processed })
      onDocumentReady?.(processed)
    } catch (error) {
      updateItem(id, { stage: 'error', error: toAppError(error).message })
    }
  }

  function handleFiles(files: File[]) {
    files.forEach((file) => void enqueue(file))
  }

  function markReviewed(itemId: string, document: DocumentRead) {
    updateItem(itemId, { stage: 'done', document })
  }

  function dismiss(itemId: string) {
    setItems((prev) => prev.filter((item) => item.id !== itemId))
  }

  const queueNode =
    items.length > 0 ? (
      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <Card key={item.id}>
            <CardBody>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{item.fileName}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{STAGE_LABELS[item.stage]}</p>
                </div>
                {item.document ? <DocumentStatusBadge status={item.document.status} /> : null}
              </div>

              {item.stage === 'uploading' || item.stage === 'processing' ? (
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full w-1/2 animate-pulse rounded-full bg-brand-500" />
                </div>
              ) : null}

              {item.stage === 'done' && item.possibleDuplicate ? (
                <p className="mt-2 text-xs text-warning">
                  ⚠️ Este arquivo é idêntico a um documento já enviado. Nenhum novo documento foi criado.
                </p>
              ) : null}

              {item.stage === 'error' ? <p className="mt-2 text-xs text-expense">{item.error}</p> : null}

              {item.stage === 'review' && item.document ? (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <DocumentReviewPanel document={item.document} onConfirmed={(doc) => markReviewed(item.id, doc)} />
                </div>
              ) : null}

              {item.stage === 'done' && !item.possibleDuplicate ? (
                <div className="mt-2 flex items-center gap-1.5 text-xs text-revenue">
                  <CheckIcon className="h-3.5 w-3.5" /> Documento processado e confirmado
                </div>
              ) : null}

              {item.stage === 'done' ? (
                <button
                  type="button"
                  onClick={() => dismiss(item.id)}
                  className="mt-2 text-xs text-slate-400 hover:text-slate-600"
                >
                  Dispensar
                </button>
              ) : null}
            </CardBody>
          </Card>
        ))}
      </div>
    ) : null

  return { handleFiles, queueNode }
}
