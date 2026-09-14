import { Badge } from '@/components/ui/Badge'
import type {
  AlertType,
  DocumentLinkStatus,
  DocumentStatus,
  ExpenseStatus,
  OCRConfidence,
  RevenueStatus,
} from '@/types/api'

const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, { label: string; tone: 'neutral' | 'success' | 'danger' | 'warning' | 'info' }> = {
  UPLOADED: { label: 'Enviado', tone: 'info' },
  PROCESSING: { label: 'Processando', tone: 'info' },
  PROCESSED: { label: 'Processado', tone: 'success' },
  HUMAN_REVIEW: { label: 'Revisão necessária', tone: 'warning' },
  FAILED: { label: 'Falha no processamento', tone: 'danger' },
  POSSIBLE_DUPLICATE: { label: 'Possível duplicidade', tone: 'warning' },
}

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const info = DOCUMENT_STATUS_LABELS[status]
  return <Badge tone={info.tone}>{info.label}</Badge>
}

const EXPENSE_STATUS_LABELS: Record<ExpenseStatus, { label: string; tone: 'success' | 'warning' }> = {
  COMPLETE: { label: 'Completo', tone: 'success' },
  PENDING_INFORMATION: { label: 'Informação pendente', tone: 'warning' },
}

export function ExpenseStatusBadge({ status }: { status: ExpenseStatus }) {
  const info = EXPENSE_STATUS_LABELS[status]
  return <Badge tone={info.tone}>{info.label}</Badge>
}

const REVENUE_STATUS_LABELS: Record<RevenueStatus, { label: string; tone: 'success' | 'warning' }> = {
  COMPLETE: { label: 'Completo', tone: 'success' },
  PENDING_INFORMATION: { label: 'Informação pendente', tone: 'warning' },
}

export function RevenueStatusBadge({ status }: { status: RevenueStatus }) {
  const info = REVENUE_STATUS_LABELS[status]
  return <Badge tone={info.tone}>{info.label}</Badge>
}

const DOCUMENT_LINK_LABELS: Record<DocumentLinkStatus, { label: string; tone: 'neutral' | 'success' | 'warning' }> = {
  ATTACHED: { label: 'Anexado', tone: 'success' },
  PENDING: { label: 'Sem documento', tone: 'warning' },
  NOT_REQUIRED: { label: 'Não exigido', tone: 'neutral' },
}

export function DocumentLinkBadge({ status }: { status: DocumentLinkStatus }) {
  const info = DOCUMENT_LINK_LABELS[status]
  return <Badge tone={info.tone}>{info.label}</Badge>
}

const OCR_CONFIDENCE_LABELS: Record<OCRConfidence, { label: string; tone: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  HIGH: { label: 'Confiança OCR: Alta', tone: 'success' },
  MEDIUM: { label: 'Confiança OCR: Média', tone: 'warning' },
  LOW: { label: 'Confiança OCR: Baixa', tone: 'danger' },
  NONE: { label: 'OCR indisponível', tone: 'neutral' },
}

export function OcrConfidenceBadge({ confidence }: { confidence: OCRConfidence }) {
  const info = OCR_CONFIDENCE_LABELS[confidence]
  return <Badge tone={info.tone}>{info.label}</Badge>
}

const ALERT_TYPE_LABELS: Record<AlertType, { label: string; tone: 'neutral' | 'success' | 'danger' | 'warning' | 'info' }> = {
  INFO: { label: 'Informativo', tone: 'info' },
  WARNING: { label: 'Atenção', tone: 'warning' },
  ERROR: { label: 'Inconsistência', tone: 'danger' },
  CRITICAL: { label: 'Crítico', tone: 'danger' },
  HUMAN_REVIEW: { label: 'Revisão humana', tone: 'warning' },
}

export function AlertTypeBadge({ type }: { type: AlertType }) {
  const info = ALERT_TYPE_LABELS[type]
  return <Badge tone={info.tone}>{info.label}</Badge>
}
