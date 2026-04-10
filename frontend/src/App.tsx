import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { AppLayout } from './components/layout/AppLayout'
import { SettingsPage } from './pages/SettingsPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { Form1301Page } from './pages/Form1301Page'
import { api } from './lib/api'

interface SettingsStatus {
  has_api_key: boolean
  provider: string
}

function HomePage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <h1 className="text-2xl text-muted-foreground">ברוכים הבאים</h1>
    </div>
  )
}

export default function App() {
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [isConfigured, setIsConfigured] = useState(true)

  useEffect(() => {
    api<SettingsStatus>('/settings')
      .then((s) => {
        setIsConfigured(s.has_api_key && !!s.provider)
        setSettingsLoaded(true)
      })
      .catch(() => {
        setIsConfigured(false)
        setSettingsLoaded(true)
      })
  }, [])

  if (!settingsLoaded) return null

  return (
    <AppLayout>
      <Routes>
        <Route
          path="/"
          element={isConfigured ? <HomePage /> : <Navigate to="/settings" replace />}
        />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/form1301" element={<Form1301Page />} />
      </Routes>
    </AppLayout>
  )
}
