import { Routes, Route } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'

function HomePage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <h1 className="text-2xl text-muted-foreground">ברוכים הבאים</h1>
    </div>
  )
}

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </AppLayout>
  )
}
