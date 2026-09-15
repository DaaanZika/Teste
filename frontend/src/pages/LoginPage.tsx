import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import { Alert, Button, Input } from '@/components/ui'
import { useAuthStatus } from '@/hooks/useAuthStatus'

/**
 * Password login (PROMPT 4) — only meaningful once AUTH_PROVIDER isn't
 * "local" (that mode never checks a session cookie at all, see
 * app/core/security.py). Deliberately generic on failure: the backend
 * returns the same error for a wrong password and an unknown e-mail, so
 * this never hints at which one it was (no account enumeration).
 */
export function LoginPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: status } = useAuthStatus()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.auth.login(email, password)
      await queryClient.invalidateQueries({ queryKey: ['auth', 'status'] })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível entrar.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white">
            C
          </div>
          <h1 className="text-lg font-semibold text-slate-900">Entrar</h1>
          <p className="mt-1 text-sm text-slate-500">Acesse sua organização.</p>
        </div>

        {error ? (
          <Alert tone="danger" className="mb-4">
            {error}
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="E-mail"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Input
            label="Senha"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button type="submit" loading={loading} className="mt-1 justify-center">
            Entrar
          </Button>
        </form>

        <div className="mt-4 flex items-center justify-between text-xs">
          {status?.google_configured ? (
            <a href={api.auth.loginUrl()} className="text-slate-500 hover:text-slate-700">
              Entrar com Google
            </a>
          ) : (
            <span />
          )}
          <a href="/esqueci-senha" className="text-slate-500 hover:text-slate-700">
            Esqueci minha senha
          </a>
        </div>
      </div>
    </div>
  )
}
