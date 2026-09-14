import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AccountMenu } from '@/components/layout/AccountMenu'
import { renderWithProviders } from '@/test/utils'
import type { AuthStatus } from '@/types/api'

const statusMock = vi.fn()

vi.mock('@/api', () => ({
  api: {
    auth: {
      status: (...args: unknown[]) => statusMock(...args),
      loginUrl: () => 'http://127.0.0.1:8000/auth/google/login',
      logout: vi.fn(),
    },
  },
}))

describe('AccountMenu', () => {
  beforeEach(() => {
    statusMock.mockReset()
  })

  it('renders nothing in local mode (V1 default — no login flow)', async () => {
    statusMock.mockResolvedValue({
      auth_provider: 'local',
      google_configured: false,
      authenticated: true,
      user: { id: 'u1', name: 'Operador Local', email: null, google_id: null, avatar: null, role: 'ADMIN', active: true, created_at: '', updated_at: '' },
    } satisfies AuthStatus)

    renderWithProviders(<AccountMenu />)
    await waitFor(() => expect(statusMock).toHaveBeenCalled())
    // The provider tree (toast container, etc.) always renders something —
    // what matters is that AccountMenu itself contributes no login/user UI.
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows a Google login link when configured but not authenticated', async () => {
    statusMock.mockResolvedValue({
      auth_provider: 'google',
      google_configured: true,
      authenticated: false,
      user: null,
    } satisfies AuthStatus)

    renderWithProviders(<AccountMenu />)
    const link = await screen.findByRole('link', { name: 'Entrar com Google' })
    expect(link).toHaveAttribute('href', 'http://127.0.0.1:8000/auth/google/login')
  })

  it('shows the signed-in user and a logout button when authenticated', async () => {
    statusMock.mockResolvedValue({
      auth_provider: 'google',
      google_configured: true,
      authenticated: true,
      user: {
        id: 'u1',
        name: 'Maria Silva',
        email: 'maria@example.com',
        google_id: 'g1',
        avatar: null,
        role: 'FINANCIAL',
        active: true,
        created_at: '',
        updated_at: '',
      },
    } satisfies AuthStatus)

    renderWithProviders(<AccountMenu />)
    expect(await screen.findByText('Maria Silva')).toBeInTheDocument()
    expect(screen.getByText('Financeiro')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument()
  })
})
