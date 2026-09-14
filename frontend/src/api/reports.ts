import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type {
  DocumentsReportSummary,
  ExpenseReportRow,
  FinanceSummary,
  RevenueReportRow,
} from '@/types/api'

export type ReportExportType = 'summary' | 'expenses' | 'revenues' | 'documents'
export type ReportExportFormat = 'csv' | 'xlsx' | 'pdf'

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

  /**
   * A direct browser navigation URL, not an XHR call — like
   * auth.loginUrl()/integrations.connectGoogleDriveUrl(). The session
   * cookie still travels on this top-level GET (SameSite=Lax allows
   * that), so it works the same whether AUTH_PROVIDER is "local" or
   * "google". Every exported file is a "RELATÓRIO AUXILIAR", never an
   * official TSE/CONTA+JE filing — see backend export_service.py.
   */
  exportUrl(type: ReportExportType, format: ReportExportFormat, campaignId?: string): string {
    const params = new URLSearchParams({ format })
    if (campaignId) params.set('campaign_id', campaignId)
    return `${http.defaults.baseURL}/reports/${type}/export?${params.toString()}`
  },
}
