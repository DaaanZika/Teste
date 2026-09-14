import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DashboardPage } from '@/pages/DashboardPage'
import { renderWithProviders } from '@/test/utils'
import type { ComplianceAlertRead, DocumentsReportSummary, FinanceSummary } from '@/types/api'

const summaryMock = vi.fn()
const documentsReportMock = vi.fn()
const alertsMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    finance: { summary: (...args: unknown[]) => summaryMock(...args) },
    reports: { documents: (...args: unknown[]) => documentsReportMock(...args) },
    compliance: { alerts: (...args: unknown[]) => alertsMock(...args) },
  },
}))

const summaryFixture: FinanceSummary = {
  total_revenues: '1000.00',
  total_expenses: '400.00',
  balance: '600.00',
  pending_information_expenses: 1,
  pending_information_revenues: 0,
  expenses_without_document: 2,
}

const documentsFixture: DocumentsReportSummary = {
  total: 7,
  processed: 3,
  pending: 0,
  human_review: 1,
  duplicated: 1,
  failed: 0,
}

const alertsFixture: ComplianceAlertRead[] = [
  {
    id: 'a1',
    campaign_id: null,
    rule_id: null,
    type: 'WARNING',
    status: 'OPEN',
    title: 'Despesa sem documento',
    message: 'x',
    entity: 'expense',
    entity_id: 'e1',
    created_at: '2024-01-01T00:00:00Z',
  },
]

describe('DashboardPage', () => {
  beforeEach(() => {
    summaryMock.mockReset()
    documentsReportMock.mockReset()
    alertsMock.mockReset()
  })

  it('shows a loading state before data arrives', () => {
    summaryMock.mockReturnValue(new Promise(() => {}))
    documentsReportMock.mockReturnValue(new Promise(() => {}))
    alertsMock.mockReturnValue(new Promise(() => {}))

    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('Carregando dashboard…')).toBeInTheDocument()
  })

  it('renders real backend totals once loaded — never a fabricated number', async () => {
    summaryMock.mockResolvedValue(summaryFixture)
    documentsReportMock.mockResolvedValue(documentsFixture)
    alertsMock.mockResolvedValue(alertsFixture)

    renderWithProviders(<DashboardPage />)

    await waitFor(() => expect(screen.getByText('R$ 1.000,00')).toBeInTheDocument())
    expect(screen.getByText('R$ 400,00')).toBeInTheDocument()
    expect(screen.getByText('R$ 600,00')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument() // documents.total
    expect(screen.getByText('5')).toBeInTheDocument() // computed pending count
    expect(screen.getAllByText('1').length).toBeGreaterThan(0) // alerts.length
  })

  it('shows an error state with a retry action when a backend call fails', async () => {
    summaryMock.mockRejectedValue(new Error('boom'))
    documentsReportMock.mockResolvedValue(documentsFixture)
    alertsMock.mockResolvedValue(alertsFixture)

    renderWithProviders(<DashboardPage />)

    expect(await screen.findByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
    expect(screen.getByText('Não foi possível carregar os dados do dashboard.')).toBeInTheDocument()
  })
})
