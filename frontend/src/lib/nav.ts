import {
  ComplianceIcon,
  DashboardIcon,
  DocumentIcon,
  ExpenseIcon,
  FinanceIcon,
  PendingIcon,
  PlusIcon,
  ReportsIcon,
  RevenueIcon,
  SettingsIcon,
  ShieldIcon,
} from '@/components/icons'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import type { ComponentType, SVGProps } from 'react'

export interface NavItem {
  to: string
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon },
  { to: '/documentos', label: 'Documentos', icon: DocumentIcon },
  { to: '/despesas', label: 'Despesas', icon: ExpenseIcon },
  { to: '/receitas', label: 'Receitas', icon: RevenueIcon },
  { to: '/adicionar-gasto', label: 'Adicionar Gasto', icon: PlusIcon },
  { to: '/financeiro', label: 'Financeiro', icon: FinanceIcon },
  { to: '/pendencias', label: 'Pendências', icon: PendingIcon },
  { to: '/conformidade', label: 'Conformidade', icon: ComplianceIcon },
  { to: '/relatorios', label: 'Relatórios', icon: ReportsIcon },
  { to: '/configuracoes', label: 'Configurações', icon: SettingsIcon },
]

const ADMINISTRACAO_ITEM: NavItem = { to: '/administracao', label: '⚙️ Administração', icon: SettingsIcon }
const PLATFORM_ADMIN_ITEM: NavItem = { to: '/admin', label: '👑 Plataforma', icon: ShieldIcon }

/** Appends the org "Administração" and/or SUPER_ADMIN "Plataforma" items
 * only for a role that actually has access — a role without access never
 * even sees the link (menus never render for unauthorized users). */
export function useNavItems(): NavItem[] {
  const { data } = useAuthStatus()
  const role = data?.user?.role
  const extras: NavItem[] = []
  if (role === 'OWNER' || role === 'ADMIN') extras.push(ADMINISTRACAO_ITEM)
  if (role === 'SUPER_ADMIN') extras.push(PLATFORM_ADMIN_ITEM)
  return extras.length > 0 ? [...NAV_ITEMS, ...extras] : NAV_ITEMS
}
