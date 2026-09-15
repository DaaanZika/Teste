import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type { AuthStatus, UserRead } from '@/types/api'

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

  /** Password login (PROMPT 4) — only meaningful once AUTH_PROVIDER isn't
   * "local" (that mode never checks the session cookie at all). */
  async login(email: string, password: string): Promise<UserRead> {
    try {
      const { data } = await http.post<UserRead>('/auth/login', { email, password })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    try {
      await http.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** Always resolves — the backend returns the same generic response
   * whether or not the e-mail exists (no enumeration). */
  async forgotPassword(email: string): Promise<void> {
    try {
      await http.post('/auth/forgot-password', { email })
    } catch (error) {
      throw toAppError(error)
    }
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    try {
      await http.post('/auth/reset-password', { token, new_password: newPassword })
    } catch (error) {
      throw toAppError(error)
    }
  },

  async logout(): Promise<void> {
    try {
      await http.post('/auth/logout')
    } catch (error) {
      throw toAppError(error)
    }
  },
}
