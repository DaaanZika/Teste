/**
 * Types mirroring the backend's real Pydantic schemas exactly (see
 * backend/app/schemas/*.py and the generated OpenAPI document). Money
 * fields are typed as `string` because the backend serializes `Decimal`
 * as a string to preserve precision — never parse them to `number` for
 * arithmetic; every total shown in the UI comes from the backend already
 * computed.
 */

export type DocumentStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'PROCESSED'
  | 'HUMAN_REVIEW'
  | 'FAILED'
  | 'POSSIBLE_DUPLICATE'

export type OCRConfidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE'

export type ExpenseStatus = 'COMPLETE' | 'PENDING_INFORMATION'
export type RevenueStatus = 'COMPLETE' | 'PENDING_INFORMATION'
export type DocumentLinkStatus = 'ATTACHED' | 'PENDING' | 'NOT_REQUIRED'

export type AlertType = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL' | 'HUMAN_REVIEW'
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'

export type AuditAction =
  | 'CREATE'
  | 'UPDATE'
  | 'DELETE'
  | 'STATUS_CHANGE'
  | 'MANUAL_CORRECTION'
  | 'LINK_DOCUMENT'

export interface DocumentItemRead {
  id: string
  description: string | null
  quantity: string | null
  unit_value: string | null
  total_value: string | null
}

export interface DocumentRead {
  id: string
  campaign_id: string | null
  original_filename: string
  mime_type: string
  file_extension: string
  file_size_bytes: number
  sha256_hash: string
  status: DocumentStatus
  ocr_confidence: OCRConfidence
  ocr_text: string | null
  extracted_date: string | null
  extracted_amount: string | null
  extracted_supplier_name: string | null
  extracted_razao_social: string | null
  extracted_cnpj: string | null
  extracted_cpf: string | null
  extracted_description: string | null
  extracted_document_number: string | null
  extracted_payment_method: string | null
  possible_duplicate_of_id: string | null
  processing_error: string | null
  items: DocumentItemRead[]
  created_at: string
  updated_at: string
}

export interface DocumentUploadResponse {
  document: DocumentRead
  possible_duplicate: boolean
  duplicate_reasons: string[]
}

export interface DocumentCorrectionInput {
  extracted_date?: string | null
  extracted_amount?: number | string | null
  extracted_supplier_name?: string | null
  extracted_razao_social?: string | null
  extracted_cnpj?: string | null
  extracted_cpf?: string | null
  extracted_description?: string | null
  extracted_document_number?: string | null
  extracted_payment_method?: string | null
}

export interface ExpenseRead {
  id: string
  campaign_id: string | null
  date: string | null
  amount: string | null
  description: string | null
  category: string | null
  supplier_name: string | null
  supplier_document: string | null
  payment_method: string | null
  document_id: string | null
  document_status: DocumentLinkStatus
  status: ExpenseStatus
  missing_fields: string | null
  source_text: string | null
  created_at: string
  updated_at: string
}

export interface ExpenseCreateInput {
  campaign_id?: string | null
  date?: string | null
  amount?: number | string | null
  description?: string | null
  category?: string | null
  supplier_name?: string | null
  supplier_document?: string | null
  payment_method?: string | null
  document_id?: string | null
}

export type ExpenseUpdateInput = ExpenseCreateInput

export interface RevenueRead {
  id: string
  campaign_id: string | null
  date: string | null
  amount: string | null
  source_type: string | null
  donor_name: string | null
  donor_document: string | null
  description: string | null
  payment_method: string | null
  document_id: string | null
  document_status: DocumentLinkStatus
  status: RevenueStatus
  missing_fields: string | null
  created_at: string
  updated_at: string
}

export interface RevenueCreateInput {
  campaign_id?: string | null
  date?: string | null
  amount?: number | string | null
  source_type?: string | null
  donor_name?: string | null
  donor_document?: string | null
  description?: string | null
  payment_method?: string | null
  document_id?: string | null
}

export interface FinanceSummary {
  total_revenues: string
  total_expenses: string
  balance: string
  pending_information_expenses: number
  pending_information_revenues: number
  expenses_without_document: number
}

export interface FinanceBalance {
  balance: string
  total_revenues: string
  total_expenses: string
}

export interface PeriodTotal {
  period: string
  total_revenues: string
  total_expenses: string
  balance: string
}

export interface CategoryTotal {
  category: string
  total: string
  percentage_of_total: string
}

export interface SupplierTotal {
  supplier_name: string
  total: string
  percentage_of_total: string
}

export interface ComplianceAlertRead {
  id: string
  campaign_id: string | null
  rule_id: string | null
  type: AlertType
  status: AlertStatus
  title: string
  message: string
  entity: string | null
  entity_id: string | null
  created_at: string
}

export interface ComplianceRuleRead {
  id: string
  rule_id: string
  election_year: number | null
  rule_name: string
  description: string | null
  legal_source: string | null
  article: string | null
  paragraph: string | null
  inciso: string | null
  severity: string
  active: boolean
  validation_logic: string | null
}

export interface AuditLogRead {
  id: string
  entity: string
  entity_id: string
  action: AuditAction
  old_value: string | null
  new_value: string | null
  timestamp: string
  user_id: string | null
}

export interface DocumentsReportSummary {
  total: number
  processed: number
  pending: number
  human_review: number
  duplicated: number
  failed: number
}

export interface ExpenseReportRow {
  id: string
  date: string | null
  supplier_name: string | null
  amount: string | null
  category: string | null
  document_id: string | null
  document_status: DocumentLinkStatus
  status: ExpenseStatus
}

export interface RevenueReportRow {
  id: string
  source_type: string | null
  amount: string | null
  date: string | null
  document_id: string | null
  document_status: DocumentLinkStatus
  status: RevenueStatus
}

export type Role = 'ADMIN' | 'CAMPAIGN_MANAGER' | 'FINANCIAL' | 'ACCOUNTANT' | 'VIEWER'

export interface UserRead {
  id: string
  name: string
  email: string | null
  google_id: string | null
  avatar: string | null
  role: Role
  active: boolean
  created_at: string
  updated_at: string
}

export interface AuthStatus {
  auth_provider: string
  google_configured: boolean
  authenticated: boolean
  user: UserRead | null
}

export interface IntegrationStatus {
  name: string
  connected: boolean
  detail: string | null
}

export interface IntegrationsStatusResponse {
  google_oauth: IntegrationStatus
  google_drive: IntegrationStatus
  gmail: IntegrationStatus
  backup: IntegrationStatus
  database: IntegrationStatus
  ocr: IntegrationStatus
}

export type GmailSuggestionStatus = 'PENDING' | 'IMPORTED' | 'REJECTED'

export interface GmailSuggestion {
  id: string
  gmail_message_id: string
  sender: string | null
  subject: string | null
  received_at: string | null
  attachment_filename: string
  mime_type: string
  campaign_id: string | null
  document_id: string | null
  status: GmailSuggestionStatus
  rejected_reason: string | null
  created_at: string
}

export interface GmailScanResponse {
  new_suggestions: GmailSuggestion[]
}

/** The uniform error body returned by every handled backend failure. */
export interface ApiErrorBody {
  success: false
  error: string
  message: string
  requires_human_review: boolean
}
