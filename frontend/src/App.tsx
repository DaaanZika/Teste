import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { AddExpensePage } from '@/pages/AddExpensePage'
import { CompliancePage } from '@/pages/CompliancePage'
import { DashboardPage } from '@/pages/DashboardPage'
import { DocumentDetailPage } from '@/pages/DocumentDetailPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { ExpenseDetailPage } from '@/pages/ExpenseDetailPage'
import { ExpensesPage } from '@/pages/ExpensesPage'
import { FinancePage } from '@/pages/FinancePage'
import { PendingPage } from '@/pages/PendingPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { RevenuesPage } from '@/pages/RevenuesPage'
import { SearchPage } from '@/pages/SearchPage'
import { SettingsPage } from '@/pages/SettingsPage'

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/documentos" element={<DocumentsPage />} />
        <Route path="/documentos/:id" element={<DocumentDetailPage />} />
        <Route path="/despesas" element={<ExpensesPage />} />
        <Route path="/despesas/:id" element={<ExpenseDetailPage />} />
        <Route path="/receitas" element={<RevenuesPage />} />
        <Route path="/adicionar-gasto" element={<AddExpensePage />} />
        <Route path="/financeiro" element={<FinancePage />} />
        <Route path="/pendencias" element={<PendingPage />} />
        <Route path="/conformidade" element={<CompliancePage />} />
        <Route path="/relatorios" element={<ReportsPage />} />
        <Route path="/configuracoes" element={<SettingsPage />} />
        <Route path="/busca" element={<SearchPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
