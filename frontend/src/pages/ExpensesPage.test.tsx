import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ExpensesPage } from '@/pages/ExpensesPage'
import { renderWithProviders } from '@/test/utils'
import type { ExpenseRead } from '@/types/api'

const listMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    expenses: { list: (...args: unknown[]) => listMock(...args) },
  },
}))

function expense(overrides: Partial<ExpenseRead>): ExpenseRead {
  return {
    id: overrides.id ?? 'e1',
    campaign_id: null,
    date: '2024-01-01',
    amount: '100.00',
    description: 'Despesa',
    category: null,
    supplier_name: null,
    supplier_document: null,
    payment_method: null,
    document_id: null,
    document_status: 'PENDING',
    status: 'COMPLETE',
    missing_fields: null,
    source_text: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('ExpensesPage', () => {
  beforeEach(() => {
    listMock.mockReset()
  })

  it('shows an empty state with a call to action when there are no expenses', async () => {
    listMock.mockResolvedValue([])
    renderWithProviders(<ExpensesPage />)
    expect(await screen.findByText('Nenhuma despesa cadastrada')).toBeInTheDocument()
  })

  it('shows an error state with retry when the backend call fails', async () => {
    listMock.mockRejectedValueOnce(new Error('boom'))
    renderWithProviders(<ExpensesPage />)
    expect(await screen.findByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })

  it('filters the real list client-side by supplier name as the user types', async () => {
    listMock.mockResolvedValue([
      expense({ id: 'e1', description: 'Gasolina', supplier_name: 'Posto Central' }),
      expense({ id: 'e2', description: 'Material', supplier_name: 'Gráfica ABC' }),
    ])
    const user = userEvent.setup()

    renderWithProviders(<ExpensesPage />)
    await waitFor(() => expect(screen.getByText('Posto Central')).toBeInTheDocument())
    expect(screen.getByText('Gráfica ABC')).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('Pesquisar…'), 'gráfica')

    expect(screen.getByText('Gráfica ABC')).toBeInTheDocument()
    expect(screen.queryByText('Posto Central')).not.toBeInTheDocument()
  })
})
