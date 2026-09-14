import { forwardRef, useId } from 'react'
import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface FieldWrapperProps {
  label?: string
  hint?: string
  error?: string
  required?: boolean
  className?: string
}

function FieldShell({
  label,
  hint,
  error,
  required,
  className,
  htmlFor,
  children,
}: FieldWrapperProps & { htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label ? (
        <label htmlFor={htmlFor} className="text-sm font-medium text-slate-700">
          {label}
          {required ? <span className="text-expense"> *</span> : null}
        </label>
      ) : null}
      {children}
      {error ? (
        <p className="text-xs text-expense" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & FieldWrapperProps

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, required, className, id, ...rest },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? rest.name ?? generatedId
  return (
    <FieldShell label={label} hint={hint} error={error} required={required} htmlFor={inputId}>
      <input
        ref={ref}
        id={inputId}
        className={cn(
          'rounded-lg border px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition-colors',
          'placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100',
          error ? 'border-expense' : 'border-slate-300',
          className,
        )}
        aria-invalid={Boolean(error) || undefined}
        {...rest}
      />
    </FieldShell>
  )
})

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & FieldWrapperProps

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, error, required, className, id, ...rest },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? rest.name ?? generatedId
  return (
    <FieldShell label={label} hint={hint} error={error} required={required} htmlFor={inputId}>
      <textarea
        ref={ref}
        id={inputId}
        className={cn(
          'rounded-lg border px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition-colors',
          'placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100',
          error ? 'border-expense' : 'border-slate-300',
          className,
        )}
        aria-invalid={Boolean(error) || undefined}
        {...rest}
      />
    </FieldShell>
  )
})

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> &
  FieldWrapperProps & { options: Array<{ value: string; label: string }>; placeholder?: string }

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, error, required, className, id, options, placeholder, ...rest },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? rest.name ?? generatedId
  return (
    <FieldShell label={label} hint={hint} error={error} required={required} htmlFor={inputId}>
      <select
        ref={ref}
        id={inputId}
        className={cn(
          'rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition-colors',
          'focus:border-brand-500 focus:ring-2 focus:ring-brand-100',
          error ? 'border-expense' : 'border-slate-300',
          className,
        )}
        aria-invalid={Boolean(error) || undefined}
        {...rest}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  )
})
