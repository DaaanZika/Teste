import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ExpenseForm } from '@/components/expenses/ExpenseForm'
import { renderWithProviders } from '@/test/utils'

const createMock = vi.fn()
const listDocumentsMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    expenses: {
      create: (...args: unknown[]) => createMock(...args),
    },
    documents: {
      list: (...args: unknown[]) => listDocumentsMock(...args),
      upload: vi.fn(),
    },
  },
}))

describe('ExpenseForm', () => {
  beforeEach(() => {
    createMock.mockReset()
    listDocumentsMock.mockReset()
    listDocumentsMock.mockResolvedValue([])
  })

  it('blocks submission client-side for a negative amount, mirroring the backend rule', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ExpenseForm />)

    fireEvent.change(screen.getByLabelText('Valor'), { target: { value: '-10' } })
    await user.click(screen.getByRole('button', { name: 'Salvar despesa' }))

    expect(await screen.findByText('O valor deve ser maior que zero.')).toBeInTheDocument()
    expect(createMock).not.toHaveBeenCalled()
  })

  it('submits only the fields the user filled in, leaving the rest null (never inventing data)', async () => {
    createMock.mockResolvedValueOnce({ id: 'exp-1' })
    const user = userEvent.setup()

    renderWithProviders(<ExpenseForm />)
    await user.type(screen.getByLabelText('Descrição'), 'Gasolina')
    await user.type(screen.getByLabelText('Valor'), '150')
    await user.click(screen.getByRole('button', { name: 'Salvar despesa' }))

    await waitFor(() => expect(createMock).toHaveBeenCalledTimes(1))
    expect(createMock).toHaveBeenCalledWith(
      expect.objectContaining({
        description: 'Gasolina',
        amount: '150',
        date: null,
        supplier_name: null,
        document_id: null,
      }),
    )
  })

  it('warns that the expense will be marked pending without a document', async () => {
    renderWithProviders(<ExpenseForm />)
    expect(screen.getByText(/status "documento pendente"/)).toBeInTheDocument()
  })
})
