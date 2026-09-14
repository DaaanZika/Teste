import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QuickAddProvider } from '@/state/QuickAddContext'
import { ToastProvider } from '@/state/ToastContext'

export function renderWithProviders(ui: ReactElement, { route = '/' }: { route?: string } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <QuickAddProvider>
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </QuickAddProvider>
      </ToastProvider>
    </QueryClientProvider>,
  )
}
