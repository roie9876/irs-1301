import { Settings, FileText, Calendar, Calculator } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useTaxYear } from '@/lib/tax-year-context'

const TAX_YEARS = [2025, 2024, 2023, 2022, 2021, 2020]

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation()
  const { taxYear, setTaxYear } = useTaxYear()

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex items-center justify-between h-14 px-4">
          <Link to="/" className="text-lg font-bold">
            עוזר דוח שנתי 1301
          </Link>
          <nav className="flex items-center gap-2">
            <div className="inline-flex items-center gap-1 rounded-md border bg-muted px-2 py-1">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <select
                value={taxYear}
                onChange={(e) => setTaxYear(Number(e.target.value))}
                className="bg-transparent text-sm font-medium outline-none cursor-pointer"
              >
                {TAX_YEARS.map((y) => (
                  <option key={y} value={y}>
                    שנת מס {y}
                  </option>
                ))}
              </select>
            </div>
            <Link
              to="/documents"
              className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground ${
                location.pathname === '/documents' ? 'bg-accent text-accent-foreground' : ''
              }`}
            >
              <FileText className="h-4 w-4" />
              מסמכים
            </Link>
            <Link
              to="/form1301"
              className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground ${
                location.pathname === '/form1301' ? 'bg-accent text-accent-foreground' : ''
              }`}
            >
              <Calculator className="h-4 w-4" />
              חישוב 1301
            </Link>
            <Link
              to="/settings"
              className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground ${
                location.pathname === '/settings' ? 'bg-accent text-accent-foreground' : ''
              }`}
            >
              <Settings className="h-4 w-4" />
              הגדרות
            </Link>
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}
