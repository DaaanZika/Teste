import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '@/api'
import { OcrConfidenceBadge } from '@/components/StatusBadges'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/state/ToastContext'
import type { DocumentRead } from '@/types/api'

interface FormState {
  extracted_date: string
  extracted_amount: string
  extracted_supplier_name: string
  extracted_razao_social: string
  extracted_cnpj: string
  extracted_cpf: string
  extracted_description: string
  extracted_document_number: string
  extracted_payment_method: string
}

function toFormState(doc: DocumentRead): FormState {
  return {
    extracted_date: doc.extracted_date ?? '',
    extracted_amount: doc.extracted_amount ?? '',
    extracted_supplier_name: doc.extracted_supplier_name ?? '',
    extracted_razao_social: doc.extracted_razao_social ?? '',
    extracted_cnpj: doc.extracted_cnpj ?? '',
    extracted_cpf: doc.extracted_cpf ?? '',
    extracted_description: doc.extracted_description ?? '',
    extracted_document_number: doc.extracted_document_number ?? '',
    extracted_payment_method: doc.extracted_payment_method ?? '',
  }
}

export function DocumentReviewPanel({
  document,
  onConfirmed,
}: {
  document: DocumentRead
  onConfirmed?: (document: DocumentRead) => void
}) {
  const [form, setForm] = useState<FormState>(() => toFormState(document))
  const { notify } = useToast()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      api.documents.correct(document.id, {
        extracted_date: form.extracted_date || null,
        extracted_amount: form.extracted_amount || null,
        extracted_supplier_name: form.extracted_supplier_name || null,
        extracted_razao_social: form.extracted_razao_social || null,
        extracted_cnpj: form.extracted_cnpj || null,
        extracted_cpf: form.extracted_cpf || null,
        extracted_description: form.extracted_description || null,
        extracted_document_number: form.extracted_document_number || null,
        extracted_payment_method: form.extracted_payment_method || null,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      notify('Dados confirmados.', 'success')
      onConfirmed?.(updated)
    },
    onError: (error: Error) => notify(error.message, 'error'),
  })

  const hasAnyValue = Object.values(form).some((v) => v.trim() !== '')
  const needsReview = document.status === 'HUMAN_REVIEW' || document.status === 'POSSIBLE_DUPLICATE'

  function update<K extends keyof FormState>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <OcrConfidenceBadge confidence={document.ocr_confidence} />
        {needsReview ? (
          <span className="text-xs font-medium text-warning">⚠️ Revisão necessária</span>
        ) : (
          <span className="text-xs font-medium text-revenue">Dados confirmados</span>
        )}
      </div>

      {document.processing_error ? <Alert tone="danger">{document.processing_error}</Alert> : null}

      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Data"
          type="date"
          value={form.extracted_date}
          onChange={(e) => update('extracted_date', e.target.value)}
        />
        <Input
          label="Valor"
          type="number"
          step="0.01"
          placeholder="R$ 0,00"
          value={form.extracted_amount}
          onChange={(e) => update('extracted_amount', e.target.value)}
        />
      </div>

      <Input
        label="Fornecedor"
        placeholder="Não identificado"
        value={form.extracted_supplier_name}
        onChange={(e) => update('extracted_supplier_name', e.target.value)}
      />
      <Input
        label="Razão social"
        placeholder="Não identificada"
        value={form.extracted_razao_social}
        onChange={(e) => update('extracted_razao_social', e.target.value)}
      />

      <div className="grid grid-cols-2 gap-3">
        <Input
          label="CNPJ"
          placeholder="Não identificado"
          value={form.extracted_cnpj}
          onChange={(e) => update('extracted_cnpj', e.target.value)}
        />
        <Input
          label="CPF"
          placeholder="Não identificado"
          value={form.extracted_cpf}
          onChange={(e) => update('extracted_cpf', e.target.value)}
        />
      </div>

      <Input
        label="Descrição"
        placeholder="Não identificada"
        value={form.extracted_description}
        onChange={(e) => update('extracted_description', e.target.value)}
      />

      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Número"
          placeholder="Não identificado"
          value={form.extracted_document_number}
          onChange={(e) => update('extracted_document_number', e.target.value)}
        />
        <Input
          label="Forma de pagamento"
          placeholder="Não identificada"
          value={form.extracted_payment_method}
          onChange={(e) => update('extracted_payment_method', e.target.value)}
        />
      </div>

      {!hasAnyValue ? (
        <Alert tone="warning" title="Nenhum campo foi identificado automaticamente">
          Preencha manualmente os campos que você conseguir confirmar no documento.
        </Alert>
      ) : null}

      <Button onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!hasAnyValue}>
        Confirmar dados
      </Button>
    </div>
  )
}
