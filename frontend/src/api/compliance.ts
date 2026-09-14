import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type { AlertStatus, ComplianceAlertRead, ComplianceRuleRead } from '@/types/api'

export const complianceApi = {
  async alerts(params?: { status?: AlertStatus; campaign_id?: string }): Promise<ComplianceAlertRead[]> {
    try {
      const { data } = await http.get<ComplianceAlertRead[]>('/compliance/alerts', { params })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async rules(): Promise<ComplianceRuleRead[]> {
    try {
      const { data } = await http.get<ComplianceRuleRead[]>('/compliance/rules')
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
