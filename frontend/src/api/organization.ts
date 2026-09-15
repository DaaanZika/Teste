import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type { Organization, OrganizationUsage } from '@/types/api'

/** The org "Administração" tab's "Organização" section — always the
 * caller's own organization, never one chosen by the client. */
export const organizationApi = {
  async get(): Promise<Organization> {
    try {
      const { data } = await http.get<Organization>('/organization')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async usage(): Promise<OrganizationUsage> {
    try {
      const { data } = await http.get<OrganizationUsage>('/organization/usage')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async update(name: string): Promise<Organization> {
    try {
      const { data } = await http.patch<Organization>('/organization', { name })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
