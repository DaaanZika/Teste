import { Link } from 'react-router-dom'
import { useAuthStatus, useLogout } from '@/hooks/useAuthStatus'
import { api } from '@/api'
import { ROLE_LABELS } from '@/lib/roles'

/**
 * Shows nothing extra in auth_provider="local" (V1's default — there is
 * only one implicit operator, login would be noise). Once auth_provider is
 * "google" or "password" (PROMPT 4), shows a login link (Google and/or
 * password, whichever is available) or the signed-in user + a logout
 * button (PROMPT 3 §6/§43, PROMPT 4 §login).
 */
export function AccountMenu() {
  const statusQuery = useAuthStatus()
  const logout = useLogout()

  if (statusQuery.isLoading) return null
  if (statusQuery.isError || !statusQuery.data) return null

  const status = statusQuery.data
  if (status.auth_provider === 'local') return null

  if (!status.authenticated || !status.user) {
    return (
      <div className="flex items-center gap-2">
        {status.google_configured && (
          <a
            href={api.auth.loginUrl()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Entrar com Google
          </a>
        )}
        <Link
          to="/login"
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          Entrar
        </Link>
      </div>
    )
  }

  const { user } = status

  return (
    <div className="flex items-center gap-2">
      {user.avatar ? (
        <img src={user.avatar} alt="" className="h-7 w-7 rounded-full" referrerPolicy="no-referrer" />
      ) : (
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-xs font-medium text-slate-600">
          {user.name.slice(0, 1).toUpperCase()}
        </div>
      )}
      <div className="hidden text-xs leading-tight sm:block">
        <p className="font-medium text-slate-800">{user.name}</p>
        <p className="text-slate-400">{ROLE_LABELS[user.role] ?? user.role}</p>
      </div>
      <button
        type="button"
        onClick={() => void logout()}
        className="text-xs font-medium text-slate-400 hover:text-slate-700"
      >
        Sair
      </button>
    </div>
  )
}
