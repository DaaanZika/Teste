import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api'
import { Alert, Button, Input } from '@/components/ui'

/** Always shows the same generic confirmation whether or not the e-mail
 * exists — the backend deliberately never reveals that (no enumeration). */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    try {
      await api.auth.forgotPassword(email)
    } finally {
      setLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-lg font-semibold text-slate-900">Esqueci minha senha</h1>
        <p className="mb-6 text-sm text-slate-500">
          Informe seu e-mail — se houver uma conta cadastrada, enviaremos um link de redefinição.
        </p>

        {submitted ? (
          <Alert tone="success" title="Se este e-mail estiver cadastrado, um link foi enviado.">
            Verifique sua caixa de entrada. O link expira em 30 minutos.
          </Alert>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="E-mail"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Button type="submit" loading={loading} className="justify-center">
              Enviar link
            </Button>
          </form>
        )}

        <Link to="/login" className="mt-4 inline-block text-xs text-slate-500 hover:text-slate-700">
          Voltar ao login
        </Link>
      </div>
    </div>
  )
}
