import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { TaxYearProvider } from './lib/tax-year-context'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <TaxYearProvider>
        <App />
      </TaxYearProvider>
    </BrowserRouter>
  </StrictMode>,
)
