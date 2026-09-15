import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { AddExpensePage } from '@/pages/AddExpensePage'
import { AdministracaoPage, useCanAccessAdministracao } from '@/pages/AdministracaoPage'
import { CompliancePage } from '@/pages/CompliancePage'
import { DashboardPage } from '@/pages/DashboardPage'
import { DocumentDetailPage } from '@/pages/DocumentDetailPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { ExpenseDetailPage } from '@/pages/ExpenseDetailPage'
import { ExpensesPage } from '@/pages/ExpensesPage'
import { FinancePage } from '@/pages/FinancePage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { LoginPage } from '@/pages/LoginPage'
import { PendingPage } from '@/pages/PendingPage'
import { PlatformAdminPage, useCanAccessPlatformAdmin } from '@/pages/PlatformAdminPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { RevenuesPage } from '@/pages/RevenuesPage'
import { SearchPage } from '@/pages/SearchPage'
import { SettingsPage } from '@/pages/SettingsPage'

/** Defense in depth only — the backend already 403s every one of these
 * routes for the wrong role (require_super_admin / MANAGE_USERS+org
 * scope). This just keeps the page from ever rendering client-side too. */
function RequireAdministracao({ children }: { children: ReactNode }) {
  const { allowed, isLoading } = useCanAccessAdministracao()
  if (isLoading) return null
  if (!allowed) return <Navigate to="/" replace />
  return <>{children}</>
}

function RequirePlatformAdmin({ children }: { children: ReactNode }) {
  const { allowed, isLoading } = useCanAccessPlatformAdmin()
  if (isLoading) return null
  if (!allowed) return <Navigate to="/" replace />
  return <>{children}</>
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/esqueci-senha" element={<ForgotPasswordPage />} />
      <Route path="/redefinir-senha" element={<ResetPasswordPage />} />
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
        <Route
          path="/administracao"
          element={
            <RequireAdministracao>
              <AdministracaoPage />
            </RequireAdministracao>
          }
        />
        <Route
          path="/admin"
          element={
            <RequirePlatformAdmin>
              <PlatformAdminPage />
            </RequirePlatformAdmin>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
