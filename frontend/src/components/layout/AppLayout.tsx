import { Outlet, useLocation } from 'react-router-dom'
import { QuickAddExpenseModal } from '@/components/expenses/QuickAddExpenseModal'
import { MobileNav } from '@/components/layout/MobileNav'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { NAV_ITEMS } from '@/lib/nav'

function titleForPath(pathname: string): string {
  if (pathname.startsWith('/busca')) return 'Busca'
  if (pathname.startsWith('/documentos/')) return 'Documento'
  const exact = NAV_ITEMS.find((item) => (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)))
  return exact?.label ?? 'Campanhas'
}

export function AppLayout() {
  const location = useLocation()

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={titleForPath(location.pathname)} />
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
