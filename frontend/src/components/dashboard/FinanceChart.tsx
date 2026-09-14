import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '@/api'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { cn } from '@/lib/cn'
import { formatCurrency, toISODate } from '@/lib/format'
import { queryKeys } from '@/lib/queryClient'

type RangeKey = 'today' | '7d' | '30d' | 'custom'

const RANGE_OPTIONS: Array<{ key: RangeKey; label: string }> = [
  { key: 'today', label: 'Hoje' },
  { key: '7d', label: '7 dias' },
  { key: '30d', label: '30 dias' },
  { key: 'custom', label: 'Personalizado' },
]

function computeRange(range: RangeKey, customStart: string, customEnd: string) {
  const today = new Date()
  const end = toISODate(today)

  if (range === 'today') return { start: end, end, granularity: 'day' as const }
  if (range === '7d') {
    const start = new Date(today)
    start.setDate(start.getDate() - 6)
    return { start: toISODate(start), end, granularity: 'day' as const }
  }
  if (range === '30d') {
    const start = new Date(today)
    start.setDate(start.getDate() - 29)
    return { start: toISODate(start), end, granularity: 'day' as const }
  }
  return { start: customStart || end, end: customEnd || end, granularity: 'day' as const }
}

export function FinanceChart() {
  const [range, setRange] = useState<RangeKey>('30d')
  const [customStart, setCustomStart] = useState(() => toISODate(new Date()))
  const [customEnd, setCustomEnd] = useState(() => toISODate(new Date()))

  const { start, end, granularity } = computeRange(range, customStart, customEnd)

  const query = useQuery({
    queryKey: queryKeys.financeTotalsPeriod({ start_date: start, end_date: end, granularity }),
    queryFn: () => api.finance.totalsByPeriod({ start_date: start, end_date: end, granularity }),
  })

  const chartData = useMemo(
    () =>
      (query.data ?? []).map((row) => ({
        period: row.period,
        label: formatShortDate(row.period),
        receitas: Number(row.total_revenues),
        despesas: Number(row.total_expenses),
      })),
    [query.data],
  )

  const hasMovement = chartData.some((row) => row.receitas > 0 || row.despesas > 0)

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {RANGE_OPTIONS.map((option) => (
          <button
            key={option.key}
            type="button"
            onClick={() => setRange(option.key)}
            className={cn(
              'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
              range === option.key ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
            )}
          >
            {option.label}
          </button>
        ))}
        {range === 'custom' ? (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <input
              type="date"
              value={customStart}
              onChange={(event) => setCustomStart(event.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1"
            />
            <span>até</span>
            <input
              type="date"
              value={customEnd}
              onChange={(event) => setCustomEnd(event.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1"
            />
          </div>
        ) : null}
      </div>

      {query.isLoading ? (
        <LoadingState label="Carregando gráfico…" />
      ) : query.isError ? (
        <ErrorState message="Não foi possível carregar o gráfico financeiro." onRetry={() => query.refetch()} />
      ) : !hasMovement ? (
        <EmptyState title="Nenhuma movimentação no período" description="Registre receitas ou despesas para ver a evolução aqui." icon="📈" />
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0f9d58" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#0f9d58" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d93025" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#d93025" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              width={56}
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip
              formatter={(value, name) => [formatCurrency(Number(value)), name === 'receitas' ? 'Receitas' : 'Despesas']}
              labelFormatter={(label) => label}
              contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
            />
            <Area type="monotone" dataKey="receitas" stroke="#0f9d58" fill="url(#revenueFill)" strokeWidth={2} />
            <Area type="monotone" dataKey="despesas" stroke="#d93025" fill="url(#expenseFill)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function formatShortDate(period: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(period)
  if (match) return `${match[3]}/${match[2]}`
  const monthMatch = /^(\d{4})-(\d{2})$/.exec(period)
  if (monthMatch) return `${monthMatch[2]}/${monthMatch[1].slice(2)}`
  return period
}
