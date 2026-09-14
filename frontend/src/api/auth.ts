import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type { AuthStatus } from '@/types/api'

export const authApi = {
  /** Safe to call even when nobody is logged in — never throws for "not authenticated". */
  async status(): Promise<AuthStatus> {
    try {
      const { data } = await http.get<AuthStatus>('/auth/status')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** Full-page redirect — not an XHR call — so the browser follows Google's own login page. */
  loginUrl(): string {
    return `${http.defaults.baseURL}/auth/google/login`
  },

  async logout(): Promise<void> {
    try {
      await http.post('/auth/logout')
    } catch (error) {
      throw toAppError(error)
    }
  },
}
