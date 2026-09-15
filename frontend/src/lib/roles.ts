import type { Role } from '@/types/api'

/** Mirrors app/core/rbac.py's role grouping — kept in one place so a menu
 * item or route guard never re-derives "is this an admin-ish role" ad hoc. */
export function isSuperAdmin(role: Role | undefined): boolean {
  return role === 'SUPER_ADMIN'
}

export function isOrgAdmin(role: Role | undefined): boolean {
  return role === 'OWNER' || role === 'ADMIN'
}

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: 'Administrador',
  CAMPAIGN_MANAGER: 'Gestor de campanha',
  FINANCIAL: 'Financeiro',
  ACCOUNTANT: 'Contador',
  VIEWER: 'Visualizador',
  SUPER_ADMIN: 'Super Admin',
  OWNER: 'Proprietário',
  FINANCEIRO: 'Financeiro',
  OPERACIONAL: 'Operacional',
  VISUALIZADOR: 'Visualizador',
  CUSTOM: 'Personalizado',
}
