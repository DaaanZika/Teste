import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusIcon, SearchIcon } from '@/components/icons'
import { Button } from '@/components/ui/Button'
import { useQuickAdd } from '@/state/QuickAddContext'

export function Topbar({ title }: { title: string }) {
  const { openQuickAdd } = useQuickAdd()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  function onSearchSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = query.trim()
    if (trimmed) navigate(`/busca?q=${encodeURIComponent(trimmed)}`)
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
      <h1 className="text-base font-semibold text-slate-900 lg:text-lg">{title}</h1>

      <form onSubmit={onSearchSubmit} className="ml-auto hidden max-w-sm flex-1 sm:block">
        <label className="relative block">
          <span className="sr-only">Busca global</span>
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por fornecedor, valor, CNPJ, número da nota…"
            className="w-full rounded-lg border border-slate-300 bg-slate-50 py-2 pr-3 pl-9 text-sm outline-none focus:border-brand-500 focus:bg-white focus:ring-2 focus:ring-brand-100"
          />
        </label>
      </form>

      <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} onClick={openQuickAdd} className="ml-auto sm:ml-0">
        <span className="hidden sm:inline">Adicionar Gasto</span>
        <span className="sm:hidden">Gasto</span>
      </Button>
    </header>
  )
}
