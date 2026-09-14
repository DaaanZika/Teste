import { auditApi } from '@/api/audit'
import { authApi } from '@/api/auth'
import { complianceApi } from '@/api/compliance'
import { documentsApi } from '@/api/documents'
import { expensesApi } from '@/api/expenses'
import { financeApi } from '@/api/finance'
import { integrationsApi } from '@/api/integrations'
import { reportsApi } from '@/api/reports'
import { revenuesApi } from '@/api/revenues'

/**
 * Single entry point for every backend call: `api.documents`, `api.expenses`,
 * etc. Components import this instead of using axios/fetch directly (PROMPT
 * 2 §30), so changing an endpoint path or response shape only touches one
 * file.
 */
export const api = {
  auth: authApi,
  documents: documentsApi,
  expenses: expensesApi,
  revenues: revenuesApi,
  finance: financeApi,
  reports: reportsApi,
  compliance: complianceApi,
  audit: auditApi,
  integrations: integrationsApi,
}

export { AppError, toAppError } from '@/lib/errors'
