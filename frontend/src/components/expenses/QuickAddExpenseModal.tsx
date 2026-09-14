import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExpenseForm } from '@/components/expenses/ExpenseForm'
import { QuickAddForm } from '@/components/expenses/QuickAddForm'
import { Modal } from '@/components/ui/Modal'
import { cn } from '@/lib/cn'
import { useQuickAdd } from '@/state/QuickAddContext'
import type { ExpenseRead } from '@/types/api'

type Mode = 'quick' | 'form'

export function QuickAddExpenseModal() {
  const { open, closeQuickAdd } = useQuickAdd()
  const [mode, setMode] = useState<Mode>('quick')
  const navigate = useNavigate()

  function handleClose() {
    closeQuickAdd()
    setMode('quick')
  }

  function goToDetail(expense: ExpenseRead) {
    handleClose()
    navigate(`/despesas/${expense.id}`)
  }

  return (
    <Modal open={open} onClose={handleClose} title="Adicionar Gasto" size="md">
      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1">
        <TabButton active={mode === 'quick'} onClick={() => setMode('quick')}>
          Modo rápido
        </TabButton>
        <TabButton active={mode === 'form'} onClick={() => setMode('form')}>
          Formulário completo
        </TabButton>
      </div>

      {mode === 'quick' ? (
        <QuickAddForm onEdit={goToDetail} />
      ) : (
        <ExpenseForm onSuccess={goToDetail} />
      )}
    </Modal>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
        active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700',
      )}
    >
      {children}
    </button>
  )
}
