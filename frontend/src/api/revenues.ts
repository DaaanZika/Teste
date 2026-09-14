import { http } from '@/lib/http'
import { toAppError } from '@/lib/errors'
import type { RevenueCreateInput, RevenueRead, RevenueStatus } from '@/types/api'

export const revenuesApi = {
  async list(params?: { campaign_id?: string; status?: RevenueStatus }): Promise<RevenueRead[]> {
    try {
      const { data } = await http.get<RevenueRead[]>('/revenues', { params })
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async get(id: string): Promise<RevenueRead> {
    try {
      const { data } = await http.get<RevenueRead>(`/revenues/${id}`)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },

  async create(input: RevenueCreateInput): Promise<RevenueRead> {
    try {
      const { data } = await http.post<RevenueRead>('/revenues', input)
      return data
    } catch (error) {
      throw toAppError(error)
    }
  },
}
