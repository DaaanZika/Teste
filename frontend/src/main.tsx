import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from '@/App'
import { queryClient } from '@/lib/queryClient'
import { QuickAddProvider } from '@/state/QuickAddContext'
import { ToastProvider } from '@/state/ToastContext'
import '@/styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <QuickAddProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QuickAddProvider>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
)
