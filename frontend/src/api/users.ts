import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type { UserCreate, UserRead, UserUpdate } from '@/types/api'

/** Org-scoped user management (PROMPT 4) — always the caller's own
 * organization; the backend derives that from the session, never from
 * anything sent here. */
export const usersApi = {
  async list(): Promise<UserRead[]> {
    try {
      const { data } = await http.get<UserRead[]>('/users')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async create(payload: UserCreate): Promise<UserRead> {
    try {
      const { data } = await http.post<UserRead>('/users', payload)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async update(userId: string, payload: UserUpdate): Promise<UserRead> {
    try {
      const { data } = await http.patch<UserRead>(`/users/${userId}`, payload)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** Sends a password-reset link to the user's e-mail; never returns the token. */
  async resetPassword(userId: string): Promise<void> {
    try {
      await http.post(`/users/${userId}/reset-password`)
    } catch (error) {
      throw toAppError(error)
    }
  },
}
