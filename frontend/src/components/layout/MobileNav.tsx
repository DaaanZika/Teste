import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { CameraIcon, DashboardIcon, DocumentIcon, FinanceIcon, MenuIcon, PlusIcon } from '@/components/icons'
import { cn } from '@/lib/cn'
import { NAV_ITEMS, useNavItems } from '@/lib/nav'
import { useQuickAdd } from '@/state/QuickAddContext'

const PRIMARY = [NAV_ITEMS[0], NAV_ITEMS[1], NAV_ITEMS[5]] // Dashboard, Documentos, Financeiro

export function MobileNav() {
  const [moreOpen, setMoreOpen] = useState(false)
  const { openQuickAdd } = useQuickAdd()
  const navigate = useNavigate()
  const navItems = useNavItems()
  const more = navItems.filter((item) => !PRIMARY.includes(item) && item.to !== '/adicionar-gasto')

  return (
    <>
      {/* Secondary floating action: scan a document straight to camera capture. */}
      <button
        type="button"
        onClick={() => navigate('/documentos?capturar=1')}
        className="fixed right-4 bottom-20 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-white text-slate-700 shadow-lg ring-1 ring-slate-200 lg:hidden"
        aria-label="Escanear documento"
      >
        <CameraIcon className="h-5 w-5" />
      </button>

      <nav
        className="fixed inset-x-0 bottom-0 z-30 flex items-stretch border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden"
        aria-label="Navegação principal"
      >
        <NavLink
          to={PRIMARY[0].to}
          end
          className={({ isActive }) => navClass(isActive)}
        >
          <DashboardIcon className="h-5 w-5" />
          <span>Dashboard</span>
        </NavLink>
        <NavLink to={PRIMARY[1].to} className={({ isActive }) => navClass(isActive)}>
          <DocumentIcon className="h-5 w-5" />
          <span>Documentos</span>
        </NavLink>

        <div className="flex flex-1 items-center justify-center">
          <button
            type="button"
            onClick={openQuickAdd}
            className="-mt-6 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg"
            aria-label="Adicionar gasto"
          >
            <PlusIcon className="h-6 w-6" />
          </button>
        </div>

        <NavLink to={PRIMARY[2].to} className={({ isActive }) => navClass(isActive)}>
          <FinanceIcon className="h-5 w-5" />
          <span>Financeiro</span>
        </NavLink>
        <button type="button" onClick={() => setMoreOpen(true)} className={navClass(false)}>
          <MenuIcon className="h-5 w-5" />
          <span>Mais</span>
        </button>
      </nav>

      {moreOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Fechar menu"
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMoreOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 rounded-t-2xl bg-white p-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] shadow-xl">
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-slate-200" />
            <div className="grid grid-cols-3 gap-3">
              {more.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMoreOpen(false)}
                  className="flex flex-col items-center gap-2 rounded-xl border border-slate-100 p-3 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <item.icon className="h-5 w-5 text-slate-500" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

function navClass(isActive: boolean) {
  return cn(
    'flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] font-medium',
    isActive ? 'text-brand-600' : 'text-slate-500',
  )
}
