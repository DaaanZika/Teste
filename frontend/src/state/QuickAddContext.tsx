import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

interface QuickAddContextValue {
  open: boolean
  openQuickAdd: () => void
  closeQuickAdd: () => void
}

const QuickAddContext = createContext<QuickAddContextValue | null>(null)

/**
 * Makes "+ Adicionar Gasto" (PROMPT 2 §13) reachable from anywhere —
 * sidebar, topbar, mobile nav, a "Resolver" link on Pendências — without
 * prop-drilling a modal's open state through every layout component.
 */
export function QuickAddProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)

  const openQuickAdd = useCallback(() => setOpen(true), [])
  const closeQuickAdd = useCallback(() => setOpen(false), [])

  const value = useMemo(() => ({ open, openQuickAdd, closeQuickAdd }), [open, openQuickAdd, closeQuickAdd])

  return <QuickAddContext.Provider value={value}>{children}</QuickAddContext.Provider>
}

export function useQuickAdd() {
  const ctx = useContext(QuickAddContext)
  if (!ctx) throw new Error('useQuickAdd must be used within QuickAddProvider')
  return ctx
}
