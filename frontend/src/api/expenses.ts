import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type { ExpenseCreateInput, ExpenseRead, ExpenseStatus, ExpenseUpdateInput } from '@/types/api'

export const expensesApi = {
  async list(params?: { campaign_id?: string; status?: ExpenseStatus }): Promise<ExpenseRead[]> {
    try {
      const { data } = await http.get<ExpenseRead[]>('/expenses', { params })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async get(id: string): Promise<ExpenseRead> {
    try {
      const { data } = await http.get<ExpenseRead>(`/expenses/${id}`)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async create(input: ExpenseCreateInput): Promise<ExpenseRead> {
    try {
      const { data } = await http.post<ExpenseRead>('/expenses', input)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  /** Free-text quick entry — the backend parses it (e.g. "R$ 850 gráfica ABC"). */
  async quick(text: string, campaignId?: string): Promise<ExpenseRead> {
    try {
      const { data } = await http.post<ExpenseRead>('/expenses/quick', {
        text,
        campaign_id: campaignId ?? null,
      })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async update(id: string, input: ExpenseUpdateInput): Promise<ExpenseRead> {
    try {
      const { data } = await http.put<ExpenseRead>(`/expenses/${id}`, input)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
