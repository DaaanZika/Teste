import { AxiosError } from 'axios'
import type { ApiErrorBody } from '@/types/api'

/**
 * Every backend error is normalized into this shape before it reaches a
 * component. Components render `message` (already in Portuguese, already
 * safe to show) — never a stack trace, never raw JSON (see PROMPT 2 §27).
 */
export class AppError extends Error {
  code: string
  requiresHumanReview: boolean
  status?: number

  constructor(message: string, code: string, requiresHumanReview = false, status?: number) {
    super(message)
    this.code = code
    this.requiresHumanReview = requiresHumanReview
    this.status = status
  }
}

const FRIENDLY_MESSAGES: Record<string, string> = {
  NOT_FOUND: 'Registro não encontrado. Ele pode ter sido removido ou o link está incorreto.',
  VALIDATION_FAILED: 'Alguns dados informados são inválidos. Revise os campos destacados.',
  INVALID_REQUEST: 'Alguns dados informados são inválidos. Revise os campos destacados.',
  UNSUPPORTED_FILE_TYPE: 'Este tipo de arquivo não é aceito. Envie PDF, JPG, JPEG, PNG ou WEBP.',
  FILE_TOO_LARGE: 'O arquivo é muito grande. Envie um arquivo menor.',
  POSSIBLE_DUPLICATE: 'Este documento parece já ter sido enviado antes.',
  DOCUMENT_PROCESSING_FAILED:
    'Não foi possível processar este documento. Tente novamente ou faça uma revisão manual.',
  INTERNAL_ERROR: 'Ocorreu um erro inesperado. Tente novamente em instantes.',
  HTTP_ERROR: 'Não foi possível concluir a solicitação.',
  NETWORK_ERROR: 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.',
}

const DEFAULT_MESSAGE = 'Algo deu errado. Tente novamente.'

export function toAppError(error: unknown): AppError {
  if (error instanceof AppError) return error

  if (error instanceof AxiosError) {
    if (!error.response) {
      return new AppError(FRIENDLY_MESSAGES.NETWORK_ERROR, 'NETWORK_ERROR', false)
    }
    const body = error.response.data as Partial<ApiErrorBody> | undefined
    const code = body?.error ?? 'HTTP_ERROR'
    const friendly = FRIENDLY_MESSAGES[code] ?? body?.message ?? DEFAULT_MESSAGE
    return new AppError(friendly, code, Boolean(body?.requires_human_review), error.response.status)
  }

  return new AppError(DEFAULT_MESSAGE, 'UNKNOWN_ERROR', false)
}
