import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReportsPage } from '@/pages/ReportsPage'
import { renderWithProviders } from '@/test/utils'
import type { FinanceSummary } from '@/types/api'

const summaryMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    reports: {
      summary: (...args: unknown[]) => summaryMock(...args),
      expenses: vi.fn(),
      revenues: vi.fn(),
      documents: vi.fn(),
      exportUrl: (type: string, format: string) =>
        `http://127.0.0.1:8000/reports/${type}/export?format=${format}`,
    },
    audit: { list: vi.fn() },
  },
}))

const summary: FinanceSummary = {
  total_revenues: '1000.00',
  total_expenses: '400.00',
  balance: '600.00',
  expenses_without_document: 0,
  pending_information_expenses: 0,
  pending_information_revenues: 0,
}

describe('ReportsPage export buttons', () => {
  beforeEach(() => {
    summaryMock.mockReset()
    summaryMock.mockResolvedValue(summary)
  })

  it('renders CSV/XLSX/PDF download links pointing at the real export endpoint', async () => {
    renderWithProviders(<ReportsPage />)

    await waitFor(() => expect(summaryMock).toHaveBeenCalled())

    const csvLink = await screen.findByRole('link', { name: 'CSV' })
    expect(csvLink).toHaveAttribute('href', 'http://127.0.0.1:8000/reports/summary/export?format=csv')

    expect(screen.getByRole('link', { name: 'XLSX' })).toHaveAttribute(
      'href',
      'http://127.0.0.1:8000/reports/summary/export?format=xlsx',
    )
    expect(screen.getByRole('link', { name: 'PDF' })).toHaveAttribute(
      'href',
      'http://127.0.0.1:8000/reports/summary/export?format=pdf',
    )
  })
})
