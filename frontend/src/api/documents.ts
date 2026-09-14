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

  async process(id: string): Promise<DocumentRead> {
    try {
      const { data } = await http.post<DocumentRead>(`/documents/${id}/process`)
      return data
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
