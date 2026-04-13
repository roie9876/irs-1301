import { useCallback, useEffect, useImperativeHandle, forwardRef, useRef, useState } from 'react'
import { MessageCircle, X, Send, Loader2, Minimize2 } from 'lucide-react'
import { api, type AdvisorAnswerResponse } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface FormSnapshot {
  taxYear: number
  activeTab: string
  personalForm: Record<string, string>
  generalForm: Record<string, string>
  inputs: Record<string, string>
  sourceDocuments: string[]
  warnings: string[]
  balance: number
  netTax: number
  /** code → Hebrew label, e.g. "150" → "הכנסה מעסק או משלח יד" */
  fieldLabels?: Record<string, string>
}

export interface FloatingChatHandle {
  askAndSend: (question: string) => void
}

interface FloatingChatProps {
  snapshot: FormSnapshot
}

export const FloatingChat = forwardRef<FloatingChatHandle, FloatingChatProps>(function FloatingChat({ snapshot }, ref) {
  const [open, setOpen] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open && !minimized) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open, minimized])

  const buildFormSummary = useCallback((): string => {
    const lines: string[] = []
    lines.push(`שנת מס: ${snapshot.taxYear}`)
    lines.push(`לשונית נוכחית: ${snapshot.activeTab === 'personal' ? 'פרטים אישיים' : snapshot.activeTab === 'general' ? 'פרטים כלליים' : 'פירוט הכנסות'}`)

    if (snapshot.personalForm.taxpayer_first_name || snapshot.personalForm.taxpayer_last_name) {
      lines.push(`נישום: ${snapshot.personalForm.taxpayer_first_name || ''} ${snapshot.personalForm.taxpayer_last_name || ''}`.trim())
    }
    if (snapshot.personalForm.marital_status) {
      lines.push(`מצב משפחתי: ${snapshot.personalForm.marital_status}`)
    }
    if (snapshot.personalForm.address_city) {
      lines.push(`יישוב: ${snapshot.personalForm.address_city}`)
    }

    const generalEntries = Object.entries(snapshot.generalForm).filter(([, v]) => v && v !== '')
    if (generalEntries.length > 0) {
      const labels = snapshot.fieldLabels ?? {}
      lines.push(`פרטים כלליים שמולאו: ${generalEntries.map(([k, v]) => {
        const label = labels[k]
        return label ? `${k} (${label})=${v}` : `${k}=${v}`
      }).join(', ')}`)
    }

    const incomeEntries = Object.entries(snapshot.inputs).filter(([, v]) => v && v !== '' && v !== '0')
    if (incomeEntries.length > 0) {
      const labels = snapshot.fieldLabels ?? {}
      lines.push(`שדות הכנסה שמולאו: ${incomeEntries.map(([k, v]) => {
        const label = labels[k]
        return label ? `${k} (${label})=${v}` : `${k}=${v}`
      }).join(', ')}`)
    }

    if (snapshot.balance !== 0) lines.push(`יתרה/החזר: ${snapshot.balance}`)
    if (snapshot.netTax !== 0) lines.push(`מס נטו: ${snapshot.netTax}`)
    if (snapshot.sourceDocuments.length > 0) lines.push(`מסמכים: ${snapshot.sourceDocuments.join(', ')}`)
    if (snapshot.warnings.length > 0) lines.push(`אזהרות: ${snapshot.warnings.join(', ')}`)

    return lines.join('\n')
  }, [snapshot])

  const doSend = useCallback(async (question: string) => {
    if (!question.trim()) return
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 45000)
      const data = await api<AdvisorAnswerResponse>('/form-1301/chat', {
        method: 'POST',
        signal: controller.signal,
        body: JSON.stringify({
          question,
          tax_year: snapshot.taxYear,
          form_summary: buildFormSummary(),
          source_documents: snapshot.sourceDocuments,
          warnings: snapshot.warnings,
          balance: snapshot.balance,
          net_tax: snapshot.netTax,
        }),
      })
      clearTimeout(timeoutId)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer || 'לא קיבלתי תשובה. נסה שוב.' }])
    } catch (err) {
      const message = err instanceof DOMException && err.name === 'AbortError'
        ? 'העוזר לא הגיב בזמן. בדוק שהגדרות LLM תקינות בדף ההגדרות.'
        : err instanceof Error ? err.message : 'לא ניתן להתחבר לעוזר'
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `שגיאה: ${message}` },
      ])
    } finally {
      setLoading(false)
    }
  }, [snapshot, buildFormSummary])

  useImperativeHandle(ref, () => ({
    askAndSend: (question: string) => {
      setOpen(true)
      setMinimized(false)
      setInput('')
      void doSend(question)
    },
  }), [doSend])

  const sendMessage = useCallback(async () => {
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    await doSend(question)
  }, [input, loading, doSend])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage()
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 left-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[#2f658d] text-white shadow-lg transition-transform hover:scale-105"
        title="צ'אט עם העוזר"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    )
  }

  if (minimized) {
    return (
      <div className="fixed bottom-6 left-6 z-50 flex items-center gap-2 rounded-full bg-[#2f658d] px-4 py-2 text-white shadow-lg cursor-pointer" onClick={() => setMinimized(false)}>
        <MessageCircle className="h-5 w-5" />
        <span className="text-sm font-medium">עוזר הדוח</span>
        {messages.length > 0 && <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs">{messages.length}</span>}
      </div>
    )
  }

  return (
    <div className="fixed bottom-6 left-6 z-50 flex w-96 max-h-[70vh] flex-col rounded-xl border border-[#c3d3e4] bg-white shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between rounded-t-xl bg-[#1a3a5c] px-4 py-3 text-white">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          <span className="font-medium">עוזר הדוח</span>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" onClick={() => setMinimized(true)} className="rounded p-1 hover:bg-white/20" title="מזער">
            <Minimize2 className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setOpen(false)} className="rounded p-1 hover:bg-white/20" title="סגור">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3" style={{ minHeight: '200px', maxHeight: '50vh' }}>
        {messages.length === 0 && (
          <div className="space-y-3 text-sm text-[#5d6f85]">
            <p>שלום! אני העוזר לדוח השנתי 1301.</p>
            <p>אני רואה את כל הנתונים שמילאת עד עכשיו ויכול לענות על שאלות לפי המדריכים הרשמיים של רשות המסים.</p>
            <div className="space-y-1">
              <p className="font-medium text-[#23496d]">שאלות לדוגמה:</p>
              <button type="button" onClick={() => setInput('מה עוד חסר לי בדוח?')} className="block w-full text-right rounded border border-[#d9e5f1] bg-[#f7fbff] px-3 py-1.5 text-xs hover:bg-[#eef4fb]">מה עוד חסר לי בדוח?</button>
              <button type="button" onClick={() => setInput('האם אני זכאי לנקודות זיכוי נוספות?')} className="block w-full text-right rounded border border-[#d9e5f1] bg-[#f7fbff] px-3 py-1.5 text-xs hover:bg-[#eef4fb]">האם אני זכאי לנקודות זיכוי נוספות?</button>
              <button type="button" onClick={() => setInput('מה המשמעות של שדה 331?')} className="block w-full text-right rounded border border-[#d9e5f1] bg-[#f7fbff] px-3 py-1.5 text-xs hover:bg-[#eef4fb]">מה המשמעות של שדה 331?</button>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'rounded-lg px-3 py-2 text-sm leading-6',
              msg.role === 'user'
                ? 'bg-[#2f658d] text-white mr-4'
                : 'bg-[#f0f4fa] text-[#23496d] ml-4',
            )}
          >
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-[#5d6f85] ml-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            חושב...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#d9e5f1] p-3">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="שאל שאלה..."
            className="h-9 flex-1 rounded-lg border border-[#c3d3e4] px-3 text-sm"
            disabled={loading}
          />
          <button
            type="button"
            onClick={() => void sendMessage()}
            disabled={loading || !input.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#2f658d] text-white disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
})
