import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

/** Central place for cache-key prefixes so invalidation stays consistent across pages. */
export const queryKeys = {
  documents: (params?: Record<string, unknown>) => ['documents', params] as const,
  document: (id: string) => ['documents', id] as const,
  expenses: (params?: Record<string, unknown>) => ['expenses', params] as const,
  expense: (id: string) => ['expenses', id] as const,
  revenues: (params?: Record<string, unknown>) => ['revenues', params] as const,
  revenue: (id: string) => ['revenues', id] as const,
  financeSummary: (query?: Record<string, unknown>) => ['finance', 'summary', query] as const,
  financeBalance: (query?: Record<string, unknown>) => ['finance', 'balance', query] as const,
  financeTotalsPeriod: (query: Record<string, unknown>) => ['finance', 'totals', 'period', query] as const,
  financeTotalsCategory: (campaignId?: string, type?: string) =>
    ['finance', 'totals', 'category', campaignId, type] as const,
  financeTotalsSupplier: (campaignId?: string) => ['finance', 'totals', 'supplier', campaignId] as const,
  reportsDocuments: (campaignId?: string) => ['reports', 'documents', campaignId] as const,
  reportsExpenses: (campaignId?: string) => ['reports', 'expenses', campaignId] as const,
  reportsRevenues: (campaignId?: string) => ['reports', 'revenues', campaignId] as const,
  reportsSummary: (campaignId?: string) => ['reports', 'summary', campaignId] as const,
  complianceAlerts: (params?: Record<string, unknown>) => ['compliance', 'alerts', params] as const,
  complianceRules: () => ['compliance', 'rules'] as const,
  audit: (params?: Record<string, unknown>) => ['audit', params] as const,
}

/** Invalidates every cache entry a financial mutation (expense/revenue/document) can affect. */
export function invalidateFinanceRelated() {
  queryClient.invalidateQueries({ queryKey: ['finance'] })
  queryClient.invalidateQueries({ queryKey: ['reports'] })
  queryClient.invalidateQueries({ queryKey: ['compliance'] })
  queryClient.invalidateQueries({ queryKey: ['audit'] })
}
