import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { api } from '@/api'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input, Select, Textarea } from '@/components/ui/Input'
import { invalidateFinanceRelated, queryKeys } from '@/lib/queryClient'
import { useToast } from '@/state/ToastContext'
import type { ExpenseCreateInput, ExpenseRead } from '@/types/api'

const PAYMENT_METHODS = [
  { value: 'PIX', label: 'PIX' },
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'CARTAO_CREDITO', label: 'Cartão de crédito' },
  { value: 'CARTAO_DEBITO', label: 'Cartão de débito' },
  { value: 'BOLETO', label: 'Boleto' },
  { value: 'TRANSFERENCIA', label: 'Transferência' },
  { value: 'CHEQUE', label: 'Cheque' },
]

interface ExpenseFormProps {
  initial?: ExpenseRead
  onSuccess?: (expense: ExpenseRead) => void
}

export function ExpenseForm({ initial, onSuccess }: ExpenseFormProps) {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [description, setDescription] = useState(initial?.description ?? '')
  const [amount, setAmount] = useState(initial?.amount ?? '')
  const [date, setDate] = useState(initial?.date ?? '')
  const [supplierName, setSupplierName] = useState(initial?.supplier_name ?? '')
  const [supplierDocument, setSupplierDocument] = useState(initial?.supplier_document ?? '')
  const [category, setCategory] = useState(initial?.category ?? '')
  const [paymentMethod, setPaymentMethod] = useState(initial?.payment_method ?? '')
  const [documentId, setDocumentId] = useState(initial?.document_id ?? '')
  const [amountError, setAmountError] = useState<string>()

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents(),
    queryFn: () => api.documents.list(),
  })

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
    mutationFn: (input: ExpenseCreateInput) =>
      initial ? api.expenses.update(initial.id, input) : api.expenses.create(input),
    onSuccess: (expense) => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      invalidateFinanceRelated()
      notify(initial ? 'Despesa atualizada.' : 'Despesa criada.', 'success')
      onSuccess?.(expense)
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
      description: description || null,
      amount: amount ? amount : null,
      date: date || null,
      supplier_name: supplierName || null,
      supplier_document: supplierDocument || null,
      category: category || null,
      payment_method: paymentMethod || null,
      document_id: documentId || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Textarea
        label="Descrição"
        placeholder="Ex: Impressão de material"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        rows={2}
      />

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
          label="Fornecedor"
          placeholder="Nome do fornecedor"
          value={supplierName}
          onChange={(event) => setSupplierName(event.target.value)}
        />
        <Input
          label="CPF/CNPJ"
          placeholder="Somente números"
          value={supplierDocument}
          onChange={(event) => setSupplierDocument(event.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Categoria"
          placeholder="Ex: Combustível"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        />
        <Select
          label="Forma de pagamento"
          placeholder="Selecione"
          options={PAYMENT_METHODS}
          value={paymentMethod}
          onChange={(event) => setPaymentMethod(event.target.value)}
        />
      </div>

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
            <span className="text-xs">Sem documento, esta despesa fica com status "documento pendente".</span>
          </Alert>
        ) : null}
      </div>

      <Button type="submit" loading={saveMutation.isPending}>
        {initial ? 'Salvar alterações' : 'Salvar despesa'}
      </Button>
    </form>
  )
}
