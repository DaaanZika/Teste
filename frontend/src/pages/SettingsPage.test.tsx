import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SettingsPage } from '@/pages/SettingsPage'
import { renderWithProviders } from '@/test/utils'
import type { AuthStatus, GmailSuggestion, IntegrationsStatusResponse } from '@/types/api'

const authStatusMock = vi.fn()
const integrationsStatusMock = vi.fn()
const disconnectDriveMock = vi.fn()
const disconnectGmailMock = vi.fn()
const scanGmailMock = vi.fn()
const listGmailSuggestionsMock = vi.fn()
const confirmGmailSuggestionMock = vi.fn()
const rejectGmailSuggestionMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    auth: {
      status: (...args: unknown[]) => authStatusMock(...args),
      loginUrl: () => 'http://127.0.0.1:8000/auth/google/login',
      logout: vi.fn(),
    },
    integrations: {
      status: (...args: unknown[]) => integrationsStatusMock(...args),
      connectGoogleDriveUrl: () => 'http://127.0.0.1:8000/integrations/google-drive/connect',
      disconnectGoogleDrive: (...args: unknown[]) => disconnectDriveMock(...args),
      connectGmailUrl: () => 'http://127.0.0.1:8000/integrations/gmail/connect',
      disconnectGmail: (...args: unknown[]) => disconnectGmailMock(...args),
      scanGmail: (...args: unknown[]) => scanGmailMock(...args),
      listGmailSuggestions: (...args: unknown[]) => listGmailSuggestionsMock(...args),
      confirmGmailSuggestion: (...args: unknown[]) => confirmGmailSuggestionMock(...args),
      rejectGmailSuggestion: (...args: unknown[]) => rejectGmailSuggestionMock(...args),
    },
  },
}))

const localAuth: AuthStatus = {
  auth_provider: 'local',
  google_configured: false,
  authenticated: true,
  user: { id: 'u1', name: 'Operador Local', email: null, google_id: null, avatar: null, role: 'ADMIN', active: true, created_at: '', updated_at: '' },
}

const disconnectedIntegrations: IntegrationsStatusResponse = {
  google_oauth: { name: 'Google', connected: false, detail: null },
  google_drive: { name: 'Google Drive', connected: false, detail: 'Não conectado' },
  gmail: { name: 'Gmail', connected: false, detail: 'Não conectado' },
  backup: { name: 'Backup', connected: false, detail: 'Nenhum provedor de backup configurado' },
  database: { name: 'Banco de dados', connected: true, detail: null },
  ocr: { name: 'OCR (Tesseract)', connected: true, detail: null },
}

const pendingSuggestion: GmailSuggestion = {
  id: 's1',
  gmail_message_id: 'msg-1',
  sender: 'fornecedor@example.com',
  subject: 'Nota fiscal',
  received_at: null,
  attachment_filename: 'nota.pdf',
  mime_type: 'application/pdf',
  campaign_id: null,
  document_id: null,
  status: 'PENDING',
  rejected_reason: null,
  created_at: '',
}

describe('SettingsPage', () => {
  beforeEach(() => {
    authStatusMock.mockReset()
    integrationsStatusMock.mockReset()
    disconnectDriveMock.mockReset()
    disconnectGmailMock.mockReset()
    scanGmailMock.mockReset()
    listGmailSuggestionsMock.mockReset()
    listGmailSuggestionsMock.mockResolvedValue([])
    confirmGmailSuggestionMock.mockReset()
    rejectGmailSuggestionMock.mockReset()
  })

  it('renders real, live integration status instead of a hardcoded "coming soon" list', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue(disconnectedIntegrations)

    renderWithProviders(<SettingsPage />)

    await waitFor(() => expect(integrationsStatusMock).toHaveBeenCalled())
    expect(await screen.findByText('Google Drive')).toBeInTheDocument()
    expect(screen.getAllByText('Não conectado').length).toBeGreaterThan(0)
  })

  it('shows a connect button for an admin when Google is configured but Drive is not connected', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue({
      ...disconnectedIntegrations,
      google_oauth: { name: 'Google', connected: true, detail: null },
    })

    renderWithProviders(<SettingsPage />)

    expect(await screen.findByRole('button', { name: 'Conectar Google Drive' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Conectar Gmail' })).toBeInTheDocument()
  })

  it('shows a disconnect button for an admin when Drive is connected', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue({
      ...disconnectedIntegrations,
      google_oauth: { name: 'Google', connected: true, detail: null },
      google_drive: { name: 'Google Drive', connected: true, detail: null },
    })

    renderWithProviders(<SettingsPage />)

    expect(await screen.findByRole('button', { name: 'Desconectar Google Drive' })).toBeInTheDocument()
  })

  it('never claims a TSE submission or export happened', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue(disconnectedIntegrations)

    renderWithProviders(<SettingsPage />)

    expect(await screen.findByText(/não é o CONTA\+JE/i)).toBeInTheDocument()
  })

  it('hides connect/disconnect controls from a non-admin user', async () => {
    authStatusMock.mockResolvedValue({
      ...localAuth,
      user: { ...localAuth.user!, role: 'VIEWER' },
    })
    integrationsStatusMock.mockResolvedValue(disconnectedIntegrations)

    renderWithProviders(<SettingsPage />)

    expect(
      await screen.findByText('Apenas administradores podem conectar ou desconectar integrações.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Conectar Google Drive' })).not.toBeInTheDocument()
  })

  it('shows the Gmail suggestions card only once Gmail is connected', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue(disconnectedIntegrations)

    renderWithProviders(<SettingsPage />)

    await waitFor(() => expect(integrationsStatusMock).toHaveBeenCalled())
    expect(screen.queryByText('Comprovantes detectados no Gmail')).not.toBeInTheDocument()
  })

  it('lists a pending suggestion with confirm/reject actions when Gmail is connected', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue({
      ...disconnectedIntegrations,
      gmail: { name: 'Gmail', connected: true, detail: null },
    })
    listGmailSuggestionsMock.mockResolvedValue([pendingSuggestion])

    renderWithProviders(<SettingsPage />)

    expect(await screen.findByText('nota.pdf')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirmar importação' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rejeitar' })).toBeInTheDocument()
  })

  it('never imports a suggestion just by scanning — only confirm does', async () => {
    authStatusMock.mockResolvedValue(localAuth)
    integrationsStatusMock.mockResolvedValue({
      ...disconnectedIntegrations,
      gmail: { name: 'Gmail', connected: true, detail: null },
    })
    scanGmailMock.mockResolvedValue({ new_suggestions: [pendingSuggestion] })

    renderWithProviders(<SettingsPage />)

    const scanButton = await screen.findByRole('button', { name: 'Buscar novos' })
    scanButton.click()

    await waitFor(() => expect(scanGmailMock).toHaveBeenCalled())
    expect(confirmGmailSuggestionMock).not.toHaveBeenCalled()
  })
})
