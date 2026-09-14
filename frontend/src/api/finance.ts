import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type { CategoryTotal, FinanceBalance, FinanceSummary, PeriodTotal, SupplierTotal } from '@/types/api'

export interface PeriodQuery {
  campaign_id?: string
  granularity?: 'day' | 'month' | 'year'
  start_date?: string
  end_date?: string
}

export interface DateRangeQuery {
  campaign_id?: string
  start_date?: string
  end_date?: string
}

export const financeApi = {
  async summary(query: DateRangeQuery = {}): Promise<FinanceSummary> {
    try {
      const { data } = await http.get<FinanceSummary>('/finance/summary', { params: query })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async balance(query: DateRangeQuery = {}): Promise<FinanceBalance> {
    try {
      const { data } = await http.get<FinanceBalance>('/finance/balance', { params: query })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async totalsByPeriod(query: PeriodQuery = {}): Promise<PeriodTotal[]> {
    try {
      const { data } = await http.get<PeriodTotal[]>('/finance/totals/period', { params: query })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async totalsByCategory(campaignId?: string, type: 'EXPENSE' | 'REVENUE' = 'EXPENSE'): Promise<CategoryTotal[]> {
    try {
      const { data } = await http.get<CategoryTotal[]>('/finance/totals/category', {
        params: { campaign_id: campaignId, type },
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async totalsBySupplier(campaignId?: string): Promise<SupplierTotal[]> {
    try {
      const { data } = await http.get<SupplierTotal[]>('/finance/totals/supplier', {
        params: { campaign_id: campaignId },
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
