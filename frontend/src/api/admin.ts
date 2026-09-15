import { toAppError } from '@/lib/errors'
import { http } from '@/lib/http'
import type {
  AuditLogRead,
  Organization,
  OrganizationCreate,
  OrganizationStatus,
  OrganizationUsage,
  PlatformMetrics,
  UserRead,
} from '@/types/api'

/** SUPER_ADMIN-only platform administration (PROMPT 4 FASE 6). Every call
 * here 403s for any other role — the backend gates by role, not
 * permission, so nothing else can accidentally unlock it. */
export const adminApi = {
  async metrics(): Promise<PlatformMetrics> {
    try {
      const { data } = await http.get<PlatformMetrics>('/admin/metrics')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async organizations(params?: { search?: string; status?: OrganizationStatus }): Promise<Organization[]> {
    try {
      const { data } = await http.get<Organization[]>('/admin/organizations', { params })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async createOrganization(payload: OrganizationCreate): Promise<Organization> {
    try {
      const { data } = await http.post<Organization>('/admin/organizations', payload)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async setOrganizationStatus(organizationId: string, status: OrganizationStatus): Promise<Organization> {
    try {
      const { data } = await http.post<Organization>(`/admin/organizations/${organizationId}/status`, { status })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async organizationUsage(organizationId: string): Promise<OrganizationUsage> {
    try {
      const { data } = await http.get<OrganizationUsage>(`/admin/organizations/${organizationId}/usage`)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async organizationUsers(organizationId: string): Promise<UserRead[]> {
    try {
      const { data } = await http.get<UserRead[]>(`/admin/organizations/${organizationId}/users`)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async allUsers(): Promise<UserRead[]> {
    try {
      const { data } = await http.get<UserRead[]>('/admin/users')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async activity(limit = 100): Promise<AuditLogRead[]> {
    try {
      const { data } = await http.get<AuditLogRead[]>('/admin/activity', { params: { limit } })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
