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
} from '@/components/icons'
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
