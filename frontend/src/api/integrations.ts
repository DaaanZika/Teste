import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type { IntegrationsStatusResponse } from '@/types/api'

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
}
