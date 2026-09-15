import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { QuickAddExpenseModal } from '@/components/expenses/QuickAddExpenseModal'
import { MobileNav } from '@/components/layout/MobileNav'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useNavItems } from '@/lib/nav'

function titleForPath(pathname: string, navItems: ReturnType<typeof useNavItems>): string {
  if (pathname.startsWith('/busca')) return 'Busca'
  if (pathname.startsWith('/documentos/')) return 'Documento'
  const exact = navItems.find((item) => (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)))
  return exact?.label ?? 'Campanhas'
}

export function AppLayout() {
  const location = useLocation()
  const navItems = useNavItems()
  const { data: status } = useAuthStatus()

  // SUPER_ADMIN belongs to no organization (platform-level role) — every
  // org-scoped page here 403s for them by design (see
  // app/core/tenancy.py::require_organization_scope). Their home is the
  // platform admin area, not the campaign app.
  if (status?.user?.role === 'SUPER_ADMIN' && location.pathname !== '/admin') {
    return <Navigate to="/admin" replace />
  }

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={titleForPath(location.pathname, navItems)} />
        <main className="flex-1 overflow-y-auto pb-24 lg:pb-8">
          <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
            <Outlet />
          </div>
        </main>
      </div>
      <MobileNav />
      <QuickAddExpenseModal />
    </div>
  )
}
