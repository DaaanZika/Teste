import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type {
  DocumentsReportSummary,
  ExpenseReportRow,
  FinanceSummary,
  RevenueReportRow,
} from '@/types/api'

export const reportsApi = {
  async summary(campaignId?: string): Promise<FinanceSummary> {
    try {
      const { data } = await http.get<FinanceSummary>('/reports/summary', {
        params: { campaign_id: campaignId },
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async expenses(campaignId?: string): Promise<ExpenseReportRow[]> {
    try {
      const { data } = await http.get<ExpenseReportRow[]>('/reports/expenses', {
        params: { campaign_id: campaignId },
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async revenues(campaignId?: string): Promise<RevenueReportRow[]> {
    try {
      const { data } = await http.get<RevenueReportRow[]>('/reports/revenues', {
        params: { campaign_id: campaignId },
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async documents(campaignId?: string): Promise<DocumentsReportSummary> {
    try {
      const { data } = await http.get<DocumentsReportSummary>('/reports/documents', {
        params: { campaign_id: campaignId },
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
