import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type { DocumentCorrectionInput, DocumentRead, DocumentStatus, DocumentUploadResponse } from '@/types/api'

export const documentsApi = {
  async upload(file: File, campaignId?: string): Promise<DocumentUploadResponse> {
    const form = new FormData()
    form.append('file', file)
    if (campaignId) form.append('campaign_id', campaignId)
    try {
      const { data } = await http.post<DocumentUploadResponse>('/documents/upload', form)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async list(params?: { status?: DocumentStatus; campaign_id?: string }): Promise<DocumentRead[]> {
    try {
      const { data } = await http.get<DocumentRead[]>('/documents', { params })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async get(id: string): Promise<DocumentRead> {
    try {
      const { data } = await http.get<DocumentRead>(`/documents/${id}`)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  /**
   * With the default QUEUE_BACKEND=inline the backend runs OCR
   * synchronously and this call already returns a terminal status — the
   * polling loop below never runs. With QUEUE_BACKEND=redis (opt-in, needs
   * a running worker — see backend/README.md) the backend enqueues the job
   * and returns immediately with status PROCESSING; this function then
   * polls GET /documents/{id} until the worker finishes, so every caller
   * gets the same "resolves once processing is done" contract either way.
   */
  async process(id: string): Promise<DocumentRead> {
    try {
      const { data: initial } = await http.post<DocumentRead>(`/documents/${id}/process`)
      if (initial.status !== 'PROCESSING') return initial

      const maxAttempts = 40 // ~48s at 1.2s intervals — generous for a single OCR pass
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        await new Promise((resolve) => setTimeout(resolve, 1200))
        const { data: current } = await http.get<DocumentRead>(`/documents/${id}`)
        if (current.status !== 'PROCESSING') return current
      }
      return initial
    } catch (error) {
      throw toAppError(error)
    }
  },

  async correct(id: string, correction: DocumentCorrectionInput): Promise<DocumentRead> {
    try {
      const { data } = await http.patch<DocumentRead>(`/documents/${id}/correct`, correction)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
