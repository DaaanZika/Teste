import { describe, expect, it } from 'vitest'
import { formatCurrency, formatDate, formatDocument, formatFileSize } from '@/lib/format'

describe('formatCurrency', () => {
  it('formats a decimal string as BRL', () => {
    expect(formatCurrency('850.00')).toBe('R$ 850,00')
  })

  it('formats zero', () => {
    expect(formatCurrency('0.00')).toBe('R$ 0,00')
  })

  it('returns an em dash for null/undefined/empty', () => {
    expect(formatCurrency(null)).toBe('—')
    expect(formatCurrency(undefined)).toBe('—')
    expect(formatCurrency('')).toBe('—')
  })

  it('never throws on garbage input', () => {
    expect(formatCurrency('not-a-number')).toBe('—')
  })
})

describe('formatDate', () => {
  it('formats an ISO date string as dd/mm/yyyy without UTC shift', () => {
    expect(formatDate('2024-03-05')).toBe('05/03/2024')
  })

  it('returns an em dash for missing dates', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
  })
})

describe('formatDocument', () => {
  it('formats an 11-digit CPF', () => {
    expect(formatDocument('12345678909')).toBe('123.456.789-09')
  })

  it('formats a 14-digit CNPJ', () => {
    expect(formatDocument('12345678000190')).toBe('12.345.678/0001-90')
  })

  it('returns an em dash for missing values', () => {
    expect(formatDocument(null)).toBe('—')
  })
})

describe('formatFileSize', () => {
  it('formats bytes, kilobytes and megabytes', () => {
    expect(formatFileSize(500)).toBe('500 B')
    expect(formatFileSize(2048)).toBe('2.0 KB')
    expect(formatFileSize(5 * 1024 * 1024)).toBe('5.0 MB')
  })
})
