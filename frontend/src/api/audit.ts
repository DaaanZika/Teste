import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type { AuditLogRead } from '@/types/api'

export const auditApi = {
  async list(params?: { entity?: string; entity_id?: string }): Promise<AuditLogRead[]> {
    try {
      const { data } = await http.get<AuditLogRead[]>('/audit', { params })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
