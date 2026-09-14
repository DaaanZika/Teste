import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type {
  DocumentUploadResponse,
  GmailScanResponse,
  GmailSuggestion,
  GmailSuggestionStatus,
  IntegrationsStatusResponse,
} from '@/types/api'

export const integrationsApi = {
  async status(): Promise<IntegrationsStatusResponse> {
    try {
      const { data } = await http.get<IntegrationsStatusResponse>('/integrations/status')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** Full-page redirect — not an XHR call — so the browser follows Google's consent screen. */
  connectGoogleDriveUrl(): string {
    return `${http.defaults.baseURL}/integrations/google-drive/connect`
  },

  async disconnectGoogleDrive(): Promise<void> {
    try {
      await http.post('/integrations/google-drive/disconnect')
    } catch (error) {
      throw toAppError(error)
    }
  },

  connectGmailUrl(): string {
    return `${http.defaults.baseURL}/integrations/gmail/connect`
  },

  async disconnectGmail(): Promise<void> {
    try {
      await http.post('/integrations/gmail/disconnect')
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** Only detects candidates — never imports anything by itself. */
  async scanGmail(): Promise<GmailScanResponse> {
    try {
      const { data } = await http.post<GmailScanResponse>('/integrations/gmail/scan', {})
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async listGmailSuggestions(status?: GmailSuggestionStatus): Promise<GmailSuggestion[]> {
    try {
      const { data } = await http.get<GmailSuggestion[]>('/integrations/gmail/suggestions', {
        params: status ? { status } : undefined,
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** The only way a suggestion becomes a real Document — a human action. */
  async confirmGmailSuggestion(id: string): Promise<DocumentUploadResponse> {
    try {
      const { data } = await http.post<DocumentUploadResponse>(`/integrations/gmail/suggestions/${id}/confirm`)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async rejectGmailSuggestion(id: string, reason?: string): Promise<GmailSuggestion> {
    try {
      const { data } = await http.post<GmailSuggestion>(`/integrations/gmail/suggestions/${id}/reject`, { reason })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
