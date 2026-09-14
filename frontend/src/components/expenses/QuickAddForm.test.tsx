import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QuickAddForm } from '@/components/expenses/QuickAddForm'
import { renderWithProviders } from '@/test/utils'
import type { ExpenseRead } from '@/types/api'

const quickMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    expenses: {
      quick: (...args: unknown[]) => quickMock(...args),
    },
  },
}))

function fixtureExpense(overrides: Partial<ExpenseRead> = {}): ExpenseRead {
  return {
    id: 'exp-1',
    campaign_id: null,
    date: null,
    amount: '850.00',
    description: 'gráfica ABC',
    category: 'Material Gráfico',
    supplier_name: 'gráfica ABC',
    supplier_document: null,
    payment_method: null,
    document_id: null,
    document_status: 'PENDING',
    status: 'PENDING_INFORMATION',
    missing_fields: 'data, documento',
    source_text: 'R$ 850 gráfica ABC',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('QuickAddForm', () => {
  beforeEach(() => {
    quickMock.mockReset()
  })

  it('sends the free-text entry to the backend and renders exactly what it returns', async () => {
    quickMock.mockResolvedValueOnce(fixtureExpense())
    const user = userEvent.setup()

    renderWithProviders(<QuickAddForm />)

    await user.type(screen.getByLabelText('Digite o gasto…'), 'R$ 850 gráfica ABC')
    await user.click(screen.getByRole('button', { name: 'Adicionar gasto' }))

    expect(quickMock).toHaveBeenCalledWith('R$ 850 gráfica ABC')

    await waitFor(() => expect(screen.getByText('Gasto registrado')).toBeInTheDocument())

    // Every field shown comes straight from the mocked backend response —
    // the component does not parse or invent this data itself.
    expect(screen.getByText('R$ 850,00')).toBeInTheDocument()
    expect(screen.getAllByText('gráfica ABC').length).toBeGreaterThan(0)
    expect(screen.getByText('Material Gráfico')).toBeInTheDocument()
    expect(screen.getByText(/Faltam: data, documento/)).toBeInTheDocument()
    expect(screen.getByText('⚠️ Documento pendente')).toBeInTheDocument()
  })

  it('shows a friendly error and does not crash when the backend call fails', async () => {
    quickMock.mockRejectedValueOnce(new Error('Não foi possível concluir a solicitação.'))
    const user = userEvent.setup()

    renderWithProviders(<QuickAddForm />)

    await user.type(screen.getByLabelText('Digite o gasto…'), 'texto qualquer')
    await user.click(screen.getByRole('button', { name: 'Adicionar gasto' }))

    await waitFor(() => expect(quickMock).toHaveBeenCalled())
    // No crash, no stack trace rendered, no result card shown.
    expect(screen.queryByText('Gasto registrado')).not.toBeInTheDocument()
  })

  it('does not submit an empty entry', async () => {
    renderWithProviders(<QuickAddForm />)
    expect(screen.getByRole('button', { name: 'Adicionar gasto' })).toBeDisabled()
    expect(quickMock).not.toHaveBeenCalled()
  })

  it('clicking an example fills the input', async () => {
    const user = userEvent.setup()
    renderWithProviders(<QuickAddForm />)

    await user.click(screen.getByText('Uber 86,40'))
    expect(screen.getByLabelText('Digite o gasto…')).toHaveValue('Uber 86,40')
  })
})
