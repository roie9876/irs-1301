import { Settings, FileText } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex items-center justify-between h-14 px-4">
          <Link to="/" className="text-lg font-bold">
            עוזר דוח שנתי 1301
          </Link>
          <nav className="flex items-center gap-2">
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
