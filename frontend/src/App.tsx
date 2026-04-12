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
    <div className="mx-auto max-w-3xl space-y-8 py-10">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold text-[#1a3a5c]">עוזר דוח שנתי 1301</h1>
        <p className="text-lg text-muted-foreground">כלי עזר חכם להכנת הדוח השנתי למס הכנסה בישראל</p>
      </div>

      <div className="rounded-lg border bg-card p-6 space-y-4 text-sm leading-7 text-[#23496d]">
        <h2 className="text-lg font-bold">מה האפליקציה עושה?</h2>
        <ul className="list-disc list-inside space-y-2 text-[#4f6279]">
          <li><strong>העלאת מסמכים</strong> — העלה טפסי 106, 867, ספח תעודת זהות, אישורי שכירות ומסמכים נוספים. המערכת תחלץ אוטומטית את הנתונים הרלוונטיים.</li>
          <li><strong>מילוי אוטומטי</strong> — פרטים מזהים, הכנסות, ניכויים וזיכויים מתמלאים אוטומטית על בסיס המסמכים שהעלית.</li>
          <li><strong>חישוב מס</strong> — המערכת מחשבת את המס הצפוי, ההחזר או היתרה לתשלום, כולל מדרגות מס, מס יסף, נקודות זיכוי וניכויים.</li>
          <li><strong>הסברים ועזרה</strong> — לכל שדה בטופס יש הסבר בעברית פשוטה, ואפשר לשאול את העוזר המובנה שאלות על כל סעיף.</li>
          <li><strong>שמירת טיוטה</strong> — העבודה שלך נשמרת אוטומטית ואפשר לחזור אליה בכל עת.</li>
        </ul>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <a href="/documents" className="flex flex-col items-center gap-3 rounded-lg border bg-card p-5 text-center transition-colors hover:border-[#2f658d] hover:bg-[#f7fbff]">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#eef4fb] text-[#2f658d]">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>
          </div>
          <div className="font-bold text-[#1a3a5c]">העלאת מסמכים</div>
          <div className="text-xs text-muted-foreground">התחל בהעלאת טפסים ומסמכים</div>
        </a>
        <a href="/form1301" className="flex flex-col items-center gap-3 rounded-lg border bg-card p-5 text-center transition-colors hover:border-[#2f658d] hover:bg-[#f7fbff]">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#eef4fb] text-[#2f658d]">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"/><path d="m9 12 2 2 4-4"/></svg>
          </div>
          <div className="font-bold text-[#1a3a5c]">חישוב 1301</div>
          <div className="text-xs text-muted-foreground">מלא את הטופס וחשב מס</div>
        </a>
        <a href="/settings" className="flex flex-col items-center gap-3 rounded-lg border bg-card p-5 text-center transition-colors hover:border-[#2f658d] hover:bg-[#f7fbff]">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#eef4fb] text-[#2f658d]">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          </div>
          <div className="font-bold text-[#1a3a5c]">הגדרות</div>
          <div className="text-xs text-muted-foreground">הגדר מודל AI וספק</div>
        </a>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm leading-7">
        <h2 className="mb-2 font-bold text-amber-800">הבהרה חשובה — כתב ויתור</h2>
        <ul className="list-disc list-inside space-y-1 text-amber-900/80">
          <li>אפליקציה זו היא <strong>כלי עזר בלבד</strong> ואינה מהווה ייעוץ מס, ייעוץ משפטי או תחליף לרואה חשבון מוסמך.</li>
          <li>המפתחים <strong>אינם נושאים באחריות</strong> לכל נזק, הפסד, קנס, ריבית או תוצאה אחרת הנובעים משימוש באפליקציה או מהסתמכות על תוצאותיה.</li>
          <li>החישובים מבוססים על מידע שהוזן על ידי המשתמש ועל חילוץ אוטומטי שעלול להכיל שגיאות. <strong>יש לבדוק כל נתון לפני הגשת הדוח.</strong></li>
          <li>האפליקציה <strong>אינה מגישה דוחות</strong> לרשות המסים — היא רק מסייעת בהכנת הנתונים.</li>
          <li>השימוש באפליקציה מהווה הסכמה לתנאים אלה.</li>
        </ul>
      </div>
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
