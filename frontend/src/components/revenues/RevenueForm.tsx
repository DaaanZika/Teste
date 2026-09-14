import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { api } from '@/api'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input, Select, Textarea } from '@/components/ui/Input'
import { invalidateFinanceRelated, queryKeys } from '@/lib/queryClient'
import { useToast } from '@/state/ToastContext'
import type { RevenueCreateInput, RevenueRead } from '@/types/api'

const PAYMENT_METHODS = [
  { value: 'PIX', label: 'PIX' },
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'CARTAO_CREDITO', label: 'Cartão de crédito' },
  { value: 'CARTAO_DEBITO', label: 'Cartão de débito' },
  { value: 'BOLETO', label: 'Boleto' },
  { value: 'TRANSFERENCIA', label: 'Transferência' },
  { value: 'CHEQUE', label: 'Cheque' },
]

export function RevenueForm({ onSuccess }: { onSuccess?: (revenue: RevenueRead) => void }) {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [amount, setAmount] = useState('')
  const [date, setDate] = useState('')
  const [donorName, setDonorName] = useState('')
  const [donorDocument, setDonorDocument] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [description, setDescription] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [amountError, setAmountError] = useState<string>()

  const documentsQuery = useQuery({ queryKey: queryKeys.documents(), queryFn: () => api.documents.list() })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.documents.upload(file),
    onSuccess: ({ document }) => {
      setDocumentId(document.id)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      notify('Documento anexado.', 'success')
    },
    onError: (error: Error) => notify(error.message, 'error'),
  })

  const saveMutation = useMutation({
    mutationFn: (input: RevenueCreateInput) => api.revenues.create(input),
    onSuccess: (revenue) => {
      queryClient.invalidateQueries({ queryKey: ['revenues'] })
      invalidateFinanceRelated()
      notify('Receita registrada.', 'success')
      onSuccess?.(revenue)
    },
    onError: (error: Error) => notify(error.message, 'error'),
  })

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setAmountError(undefined)
    if (amount && Number(amount) <= 0) {
      setAmountError('O valor deve ser maior que zero.')
      return
    }
    saveMutation.mutate({
      amount: amount || null,
      date: date || null,
      donor_name: donorName || null,
      donor_document: donorDocument || null,
      source_type: sourceType || null,
      description: description || null,
      payment_method: paymentMethod || null,
      document_id: documentId || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Valor"
          type="number"
          step="0.01"
          inputMode="decimal"
          placeholder="0,00"
          value={amount}
          error={amountError}
          onChange={(event) => setAmount(event.target.value)}
        />
        <Input label="Data" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Doador"
          placeholder="Nome do doador"
          value={donorName}
          onChange={(event) => setDonorName(event.target.value)}
        />
        <Input
          label="CPF/CNPJ"
          placeholder="Somente números"
          value={donorDocument}
          onChange={(event) => setDonorDocument(event.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Origem"
          placeholder="Ex: Doação de pessoa física"
          value={sourceType}
          onChange={(event) => setSourceType(event.target.value)}
        />
        <Select
          label="Forma de pagamento"
          placeholder="Selecione"
          options={PAYMENT_METHODS}
          value={paymentMethod}
          onChange={(event) => setPaymentMethod(event.target.value)}
        />
      </div>

      <Textarea
        label="Descrição"
        rows={2}
        value={description}
        onChange={(event) => setDescription(event.target.value)}
      />

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-slate-700">Documento</span>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={documentId}
            onChange={(event) => setDocumentId(event.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="">Nenhum documento vinculado</option>
            {documentsQuery.data?.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.original_filename}
              </option>
            ))}
          </select>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) uploadMutation.mutate(file)
              event.target.value = ''
            }}
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            loading={uploadMutation.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            + Adicionar documento
          </Button>
        </div>
        {!documentId ? (
          <Alert tone="warning">
            <span className="text-xs">Sem documento, esta receita fica com status "documento pendente".</span>
          </Alert>
        ) : null}
      </div>

      <Button type="submit" loading={saveMutation.isPending}>
        Salvar receita
      </Button>
    </form>
  )
}
