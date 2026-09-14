import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { MobileNav } from '@/components/layout/MobileNav'
import { renderWithProviders } from '@/test/utils'
import { useQuickAdd } from '@/state/QuickAddContext'

function QuickAddProbe() {
  const { open } = useQuickAdd()
  return <div data-testid="quick-add-state">{open ? 'open' : 'closed'}</div>
}

describe('MobileNav', () => {
  it('exposes both priority actions from PROMPT 2 §25: Adicionar Gasto and Escanear Documento', () => {
    renderWithProviders(
      <>
        <MobileNav />
        <QuickAddProbe />
      </>,
    )

    expect(screen.getByRole('button', { name: 'Adicionar gasto' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Escanear documento' })).toBeInTheDocument()
  })

  it('the central + button opens the quick-add modal', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <>
        <MobileNav />
        <QuickAddProbe />
      </>,
    )

    expect(screen.getByTestId('quick-add-state')).toHaveTextContent('closed')
    await user.click(screen.getByRole('button', { name: 'Adicionar gasto' }))
    expect(screen.getByTestId('quick-add-state')).toHaveTextContent('open')
  })

  it('"Mais" opens a drawer with the remaining sections', async () => {
    const user = userEvent.setup()
    renderWithProviders(<MobileNav />)

    await user.click(screen.getByRole('button', { name: 'Mais' }))
    expect(screen.getByRole('link', { name: /Conformidade/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Relatórios/ })).toBeInTheDocument()
  })
})
