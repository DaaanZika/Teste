import { beforeEach, describe, expect, it, vi } from 'vitest'
import { documentsApi } from '@/api/documents'
import type { DocumentRead } from '@/types/api'

const postMock = vi.fn()
const getMock = vi.fn()

vi.mock('@/lib/http', () => ({
  http: {
    post: (...args: unknown[]) => postMock(...args),
    get: (...args: unknown[]) => getMock(...args),
  },
}))

function doc(status: DocumentRead['status']): DocumentRead {
  return {
    id: 'd1',
    campaign_id: null,
    original_filename: 'a.pdf',
    mime_type: 'application/pdf',
    file_extension: 'pdf',
    file_size_bytes: 1,
    sha256_hash: 'x',
    status,
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
    storage_provider: 'local',
    backup_status: 'NOT_CONFIGURED',
    backup_completed_at: null,
    backup_error: null,
    items: [],
    created_at: '',
    updated_at: '',
  }
}

describe('documentsApi.process', () => {
  beforeEach(() => {
    postMock.mockReset()
    getMock.mockReset()
    vi.useRealTimers()
  })

  it('resolves immediately with the default inline backend (terminal status, no polling)', async () => {
    postMock.mockResolvedValue({ data: doc('PROCESSED') })

    const result = await documentsApi.process('d1')

    expect(result.status).toBe('PROCESSED')
    expect(getMock).not.toHaveBeenCalled()
  })

  it('polls GET /documents/{id} until the async queue finishes the job', async () => {
    vi.useFakeTimers()
    postMock.mockResolvedValue({ data: doc('PROCESSING') })
    getMock
      .mockResolvedValueOnce({ data: doc('PROCESSING') })
      .mockResolvedValueOnce({ data: doc('HUMAN_REVIEW') })

    const resultPromise = documentsApi.process('d1')
    // Two polling ticks (1.2s each) before the second GET reports done.
    await vi.advanceTimersByTimeAsync(1200)
    await vi.advanceTimersByTimeAsync(1200)
    const result = await resultPromise

    expect(result.status).toBe('HUMAN_REVIEW')
    expect(getMock).toHaveBeenCalledTimes(2)
    expect(getMock).toHaveBeenCalledWith('/documents/d1')
    vi.useRealTimers()
  })
})
