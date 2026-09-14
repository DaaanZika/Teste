import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { renderWithProviders } from '@/test/utils'
import type { DocumentRead } from '@/types/api'

const listMock = vi.fn()
const uploadMock = vi.fn()
const processMock = vi.fn()
const correctMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    documents: {
      list: (...args: unknown[]) => listMock(...args),
      upload: (...args: unknown[]) => uploadMock(...args),
      process: (...args: unknown[]) => processMock(...args),
      correct: (...args: unknown[]) => correctMock(...args),
    },
  },
  toAppError: (error: unknown) => (error instanceof Error ? error : new Error(String(error))),
}))

function baseDocument(overrides: Partial<DocumentRead> = {}): DocumentRead {
  return {
    id: 'doc-1',
    campaign_id: null,
    original_filename: 'recibo.png',
    mime_type: 'image/png',
    file_extension: '.png',
    file_size_bytes: 1234,
    sha256_hash: 'abc123',
    status: 'UPLOADED',
    ocr_confidence: 'NONE',
    ocr_text: null,
    extracted_date: null,
    extracted_amount: null,
    extracted_supplier_name: null,
    extracted_razao_social: null,
    extracted_cnpj: null,
    extracted_cpf: null,
    extracted_description: null,
    extracted_document_number: null,
    extracted_payment_method: null,
    possible_duplicate_of_id: null,
    processing_error: null,
    items: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('DocumentsPage upload pipeline', () => {
  beforeEach(() => {
    listMock.mockReset()
    uploadMock.mockReset()
    processMock.mockReset()
    correctMock.mockReset()
    listMock.mockResolvedValue([])
  })

  it('drives upload -> process -> review through the real two-call backend pipeline', async () => {
    const uploaded = baseDocument({ status: 'UPLOADED' })
    const processed = baseDocument({
      status: 'HUMAN_REVIEW',
      ocr_confidence: 'LOW',
      extracted_amount: '150.00',
    })

    uploadMock.mockResolvedValueOnce({ document: uploaded, possible_duplicate: false, duplicate_reasons: [] })
    processMock.mockResolvedValueOnce(processed)

    renderWithProviders(<DocumentsPage />)

    const file = new File(['conteudo'], 'recibo.png', { type: 'image/png' })
    const fileInput = document.querySelector('input[type="file"]:not([capture])') as HTMLInputElement
    const user = userEvent.setup()
    await user.upload(fileInput, file)

    await waitFor(() => expect(uploadMock).toHaveBeenCalledWith(file))
    await waitFor(() => expect(processMock).toHaveBeenCalledWith('doc-1'))

    // The review panel appears with the (low-confidence) result for human confirmation.
    expect(await screen.findByText('Confiança OCR: Baixa')).toBeInTheDocument()
    expect(screen.getByText('⚠️ Revisão necessária')).toBeInTheDocument()
  })

  it('flags an exact-hash duplicate without pretending a new document was processed', async () => {
    const existing = baseDocument({ id: 'doc-existing', status: 'PROCESSED' })
    uploadMock.mockResolvedValueOnce({ document: existing, possible_duplicate: true, duplicate_reasons: ['same_file_hash'] })

    renderWithProviders(<DocumentsPage />)

    const file = new File(['conteudo'], 'recibo.png', { type: 'image/png' })
    const fileInput = document.querySelector('input[type="file"]:not([capture])') as HTMLInputElement
    const user = userEvent.setup()
    await user.upload(fileInput, file)

    await waitFor(() => expect(uploadMock).toHaveBeenCalled())
    expect(await screen.findByText(/idêntico a um documento já enviado/)).toBeInTheDocument()
    expect(processMock).not.toHaveBeenCalled()
  })
})
