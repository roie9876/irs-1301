import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'

interface TaxYearContextValue {
  taxYear: number
  setTaxYear: (year: number) => Promise<void>
}

const TaxYearContext = createContext<TaxYearContextValue>({
  taxYear: 2024,
  setTaxYear: async () => {},
})

export function TaxYearProvider({ children }: { children: ReactNode }) {
  const [taxYear, setTaxYearState] = useState(2024)

  useEffect(() => {
    api<{ tax_year: number }>('/settings')
      .then((s) => setTaxYearState(s.tax_year))
      .catch(() => {})
  }, [])

  const setTaxYear = async (year: number) => {
    const prev = taxYear
    setTaxYearState(year)
    try {
      await api('/settings/tax-year', {
        method: 'PUT',
        body: JSON.stringify({ tax_year: year }),
      })
    } catch {
      setTaxYearState(prev)
    }
  }

  return (
    <TaxYearContext.Provider value={{ taxYear, setTaxYear }}>
      {children}
    </TaxYearContext.Provider>
  )
}

export function useTaxYear() {
  return useContext(TaxYearContext)
}
