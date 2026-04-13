import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Upload, FileText, Check, AlertCircle, Loader2, Save, Lock, Trash2, AlertTriangle, Eye, RefreshCcw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogHeader, DialogTitle, DialogContent } from '@/components/ui/dialog'
import { useTaxYear } from '@/lib/tax-year-context'
import { FloatingChat, type FormSnapshot } from '@/components/FloatingChat'
import {
  api,
  uploadFiles,
  type DocumentInfo,
  type DocumentListResponse,
  type FieldValue,
  type UploadResult,
} from '@/lib/api'
import { cn } from '@/lib/utils'

interface FieldMeta {
  label_he: string
  field_1301: string
  type: 'string' | 'number'
}

const FORM_106_FIELDS: Record<string, FieldMeta> = {
  employer_name: { label_he: 'שם המעסיק', field_1301: '—', type: 'string' },
  employer_id: { label_he: 'מספר מזהה מעסיק', field_1301: '—', type: 'string' },
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  gross_salary: { label_he: 'הכנסה ברוטו', field_1301: '158/172', type: 'number' },
  tax_withheld: { label_he: 'מס שנוכה במקור', field_1301: 'סעיף 84', type: 'number' },
  pension_employer: { label_he: 'הפרשות מעסיק לפנסיה', field_1301: '248/249', type: 'number' },
  pension_employee: { label_he: 'ניכוי קופ"ג כעמית שכיר', field_1301: '086/045', type: 'number' },
  insured_income: { label_he: 'הכנסה מבוטחת', field_1301: '244/245', type: 'number' },
  convalescence_pay: { label_he: 'דמי הבראה', field_1301: '011/012', type: 'number' },
  education_fund: { label_he: 'קרן השתלמות', field_1301: '218/219', type: 'number' },
  work_days: { label_he: 'ימי עבודה', field_1301: '—', type: 'number' },
  national_insurance: { label_he: 'ביטוח לאומי', field_1301: '—', type: 'number' },
  health_insurance: { label_he: 'ביטוח בריאות', field_1301: '—', type: 'number' },
  donations: { label_he: 'תרומות', field_1301: '237/037', type: 'number' },
}

const FORM_867_FIELDS: Record<string, FieldMeta> = {
  broker_name: { label_he: 'שם הברוקר', field_1301: '—', type: 'string' },
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  dividend_income: { label_he: 'הכנסה מדיבידנד', field_1301: '141', type: 'number' },
  dividend_foreign: { label_he: 'דיבידנד מחו"ל', field_1301: '—', type: 'number' },
  dividend_tax_withheld: { label_he: 'מס שנוכה מדיבידנד', field_1301: '—', type: 'number' },
  foreign_tax_paid: { label_he: 'מס ששולם בחו"ל', field_1301: '—', type: 'number' },
  interest_income: { label_he: 'הכנסה מריבית', field_1301: '327', type: 'number' },
  interest_tax_withheld: { label_he: 'מס שנוכה מריבית', field_1301: '—', type: 'number' },
}

const RENTAL_PAYMENT_FIELDS: Record<string, FieldMeta> = {
  taxpayer_name: { label_he: 'שם הנישום', field_1301: '—', type: 'string' },
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  payment_amount: { label_he: 'סכום תשלום', field_1301: '220', type: 'number' },
  payment_type: { label_he: 'סוג תשלום', field_1301: '—', type: 'string' },
  payment_date: { label_he: 'תאריך תשלום', field_1301: '—', type: 'string' },
}

const ANNUAL_SUMMARY_FIELDS: Record<string, FieldMeta> = {
  employee_name: { label_he: 'שם העובד', field_1301: '—', type: 'string' },
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  total_shares_sold: { label_he: 'מניות שנמכרו', field_1301: '—', type: 'number' },
  ordinary_income_ils: { label_he: 'הכנסת עבודה (₪)', field_1301: '158', type: 'number' },
  capital_income_ils: { label_he: 'רווח הון (₪)', field_1301: '139', type: 'number' },
  tax_advance_payment: { label_he: 'מקדמת מס', field_1301: '—', type: 'number' },
  tax_plan: { label_he: 'תוכנית מס', field_1301: '—', type: 'string' },
}

const RECEIPT_FIELDS: Record<string, FieldMeta> = {
  vendor_name: { label_he: 'שם הספק', field_1301: '—', type: 'string' },
  date: { label_he: 'תאריך', field_1301: '—', type: 'string' },
  total_amount: { label_he: 'סכום כולל', field_1301: '—', type: 'number' },
  description: { label_he: 'תיאור', field_1301: '—', type: 'string' },
}

const RENTAL_EXCEL_FIELDS: Record<string, FieldMeta> = {
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  properties: { label_he: 'נכסים', field_1301: '—', type: 'string' },
  total_annual_income: { label_he: 'סה״כ הכנסה שנתית', field_1301: '222', type: 'number' },
  tax_rate_pct: { label_he: 'שיעור מס (%)', field_1301: '—', type: 'number' },
  tax_amount: { label_he: 'סכום מס', field_1301: '220', type: 'number' },
}

const ID_SUPPLEMENT_FIELDS: Record<string, FieldMeta> = {
  holder_name: { label_he: 'שם בעל התעודה', field_1301: '—', type: 'string' },
  holder_id: { label_he: 'ת.ז. בעל התעודה', field_1301: '—', type: 'string' },
  holder_birth_date: { label_he: 'תאריך לידה בעל התעודה', field_1301: '—', type: 'string' },
  holder_gender: { label_he: 'מין', field_1301: '—', type: 'string' },
  spouse_name: { label_he: 'שם בן/בת זוג', field_1301: '—', type: 'string' },
  spouse_id: { label_he: 'ת.ז. בן/בת זוג', field_1301: '—', type: 'string' },
  spouse_birth_date: { label_he: 'תאריך לידה בן/בת זוג', field_1301: '—', type: 'string' },
  address_street: { label_he: 'רחוב', field_1301: '—', type: 'string' },
  address_house_number: { label_he: 'מספר בית', field_1301: '—', type: 'string' },
  address_city: { label_he: 'יישוב', field_1301: '—', type: 'string' },
  address_zip: { label_he: 'מיקוד', field_1301: '—', type: 'string' },
}

const LIFE_INSURANCE_FIELDS: Record<string, FieldMeta> = {
  insured_name: { label_he: 'שם המבוטח', field_1301: '—', type: 'string' },
  insured_id: { label_he: 'ת.ז. מבוטח', field_1301: '—', type: 'string' },
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  insurance_company: { label_he: 'חברת ביטוח', field_1301: '—', type: 'string' },
  total_deposits: { label_he: 'סה״כ הפקדות שנתיות', field_1301: '036/081', type: 'number' },
  policy_type: { label_he: 'סוג פוליסה', field_1301: '—', type: 'string' },
  has_savings_component: { label_he: 'מרכיב חיסכון', field_1301: '—', type: 'string' },
}

const FIELD_MAPS: Record<string, Record<string, FieldMeta>> = {
  form_106: FORM_106_FIELDS,
  form_867: FORM_867_FIELDS,
  rental_payment: RENTAL_PAYMENT_FIELDS,
  annual_summary: ANNUAL_SUMMARY_FIELDS,
  receipt: RECEIPT_FIELDS,
  rental_excel: RENTAL_EXCEL_FIELDS,
  id_supplement: ID_SUPPLEMENT_FIELDS,
  life_insurance: LIFE_INSURANCE_FIELDS,
}

const DOC_TYPE_LABELS: Record<string, string> = {
  form_106: 'טופס 106',
  form_867: 'טופס 867',
  rental_payment: 'אישור תשלום שכירות',
  annual_summary: 'דוח שנתי מניות',
  receipt: 'קבלה',
  rental_excel: 'חישוב שכירות (Excel)',
  id_supplement: 'ספח תעודת זהות',
  life_insurance: 'ביטוח חיים',
}

function getFieldMap(docType: string): Record<string, FieldMeta> {
  return FIELD_MAPS[docType] || FORM_106_FIELDS
}

function getDocTitle(doc: DocumentInfo): string {
  const typeLabel = DOC_TYPE_LABELS[doc.document_type] || doc.document_type
  const name = doc.extracted?.employer_name?.value
    || doc.extracted?.broker_name?.value
    || doc.extracted?.vendor_name?.value
    || doc.extracted?.insured_name?.value
    || doc.extracted?.employee_name?.value
    || doc.extracted?.taxpayer_name?.value
    || doc.extracted?.holder_name?.value
    || doc.extracted?.properties?.value
    || ''
  return name ? `${typeLabel} — ${name}` : typeLabel
}

function confidenceBadge(confidence: number) {
  if (confidence >= 0.8) return <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">{Math.round(confidence * 100)}%</span>
  if (confidence >= 0.5) return <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">{Math.round(confidence * 100)}%</span>
  return <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">{confidence > 0 ? `${Math.round(confidence * 100)}%` : '—'}</span>
}

function normalizeDisplayValue(field: string, value: FieldValue['value']) {
  if (field === 'holder_gender') {
    const normalized = String(value ?? '').trim().toLowerCase()
    if (normalized === 'male' || normalized === 'זכר') return 'זכר'
    if (normalized === 'female' || normalized === 'נקבה') return 'נקבה'
  }
  return value
}

export function DocumentsPage() {
  const { taxYear } = useTaxYear()
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [errors, setErrors] = useState<UploadResult[]>([])
  const [encryptedFiles, setEncryptedFiles] = useState<{ file: File; filename: string }[]>([])
  const [passwords, setPasswords] = useState<Record<string, string>>({})
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [editedFields, setEditedFields] = useState<Record<string, Record<string, FieldValue>>>({})
  const [saveStatus, setSaveStatus] = useState<Record<string, 'saving' | 'saved' | 'error'>>({})
  const [reextractStatus, setReextractStatus] = useState<Record<string, 'running' | 'done' | 'error'>>({})
  const [viewerDoc, setViewerDoc] = useState<DocumentInfo | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const chatSnapshot = useMemo<FormSnapshot>(() => ({
    taxYear,
    activeTab: 'documents',
    personalForm: {},
    generalForm: {},
    inputs: {},
    sourceDocuments: documents.map((d) => d.original_filename),
    warnings: [],
    balance: 0,
    netTax: 0,
  }), [taxYear, documents])

  useEffect(() => {
    api<DocumentListResponse>('/documents')
      .then((data) => setDocuments(data.documents))
      .catch(() => {})
  }, [taxYear])

  // Filter documents for the selected tax year
  const filteredDocuments = documents.filter((d) => {
    const docYear = d.extracted?.tax_year?.value
    return !docYear || Number(docYear) === taxYear
  })

  const lastFilesRef = useRef<File[]>([])

  const handleFiles = useCallback(async (files: File[], filePasswords?: Record<string, string>) => {
    const supportedFiles = files.filter((f) => {
      const name = f.name.toLowerCase()
      return name.endsWith('.pdf') || name.endsWith('.xlsx') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png') || name.endsWith('.webp')
    })
    if (supportedFiles.length === 0) return

    lastFilesRef.current = supportedFiles
    setUploading(true)
    setErrors([])
    try {
      const response = await uploadFiles(supportedFiles, filePasswords)
      const successes = response.results.filter((r) => r.status === 'success')
      const failures = response.results.filter((r) => r.status === 'error')
      const skipped = response.results.filter((r) => r.status === 'skipped')
      const encrypted = response.results.filter((r) => r.status === 'encrypted')

      setDocuments((prev) => [
        ...prev,
        ...successes.map((r) => ({
          doc_id: r.doc_id,
          original_filename: r.filename,
          document_type: r.document_type || 'form_106',
          extracted: r.extracted!,
          user_corrected: false,
        })),
      ])
      setErrors([...failures, ...skipped])

      // Track encrypted files for password retry
      const encFiles = encrypted.map((r) => ({
        file: supportedFiles.find((f) => f.name === r.filename)!,
        filename: r.filename,
      })).filter((e) => e.file)
      setEncryptedFiles((prev) => {
        const existing = prev.filter((p) => !encFiles.some((e) => e.filename === p.filename))
        return [...existing, ...encFiles]
      })
    } catch {
      setErrors([{ filename: 'upload', doc_id: '', status: 'error', error: 'שגיאה בהעלאה' }])
    } finally {
      setUploading(false)
    }
  }, [])

  const retryWithPasswords = useCallback(async () => {
    const filesToRetry = encryptedFiles.map((e) => e.file)
    if (filesToRetry.length === 0) return
    setEncryptedFiles([])
    await handleFiles(filesToRetry, passwords)
  }, [encryptedFiles, passwords, handleFiles])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const files = Array.from(e.dataTransfer.files)
      handleFiles(files)
    },
    [handleFiles],
  )

  const getFieldValue = (doc: DocumentInfo, field: string): FieldValue => {
    const edited = editedFields[doc.doc_id]?.[field]
    if (edited) {
      return { ...edited, value: normalizeDisplayValue(field, edited.value) }
    }
    const extracted = doc.extracted[field] || { value: null, confidence: 0 }
    return { ...extracted, value: normalizeDisplayValue(field, extracted.value) }
  }

  const setFieldEdit = (docId: string, field: string, value: string, fieldMeta: FieldMeta) => {
    const parsed: number | string | null = fieldMeta.type === 'number' ? (value === '' ? null : Number(value)) : value
    setEditedFields((prev) => ({
      ...prev,
      [docId]: {
        ...prev[docId],
        [field]: { value: parsed, confidence: 1.0 },
      },
    }))
  }

  const saveCorrections = async (docId: string) => {
    const fields = editedFields[docId]
    if (!fields || Object.keys(fields).length === 0) return

    setSaveStatus((prev) => ({ ...prev, [docId]: 'saving' }))
    try {
      const updated = await api<DocumentInfo>(`/documents/${docId}`, {
        method: 'PUT',
        body: JSON.stringify({ fields }),
      })
      setDocuments((prev) => prev.map((d) => (d.doc_id === docId ? updated : d)))
      setEditedFields((prev) => {
        const copy = { ...prev }
        delete copy[docId]
        return copy
      })
      setSaveStatus((prev) => ({ ...prev, [docId]: 'saved' }))
      setTimeout(() => setSaveStatus((prev) => {
        const copy = { ...prev }
        delete copy[docId]
        return copy
      }), 2000)
    } catch {
      setSaveStatus((prev) => ({ ...prev, [docId]: 'error' }))
    }
  }

  const deleteDocument = async (docId: string) => {
    if (!confirm('למחוק את המסמך?')) return
    try {
      await api(`/documents/${docId}`, { method: 'DELETE' })
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId))
    } catch {
      // ignore
    }
  }

  const reextractDocument = async (docId: string) => {
    setReextractStatus((prev) => ({ ...prev, [docId]: 'running' }))
    try {
      const refreshed = await api<DocumentInfo>(`/documents/${docId}/reextract`, { method: 'POST' })
      setDocuments((prev) => prev.map((doc) => (doc.doc_id === docId ? refreshed : doc)))
      setViewerDoc((prev) => (prev?.doc_id === docId ? refreshed : prev))
      setReextractStatus((prev) => ({ ...prev, [docId]: 'done' }))
      setTimeout(() => setReextractStatus((prev) => {
        const copy = { ...prev }
        delete copy[docId]
        return copy
      }), 2000)
    } catch {
      setReextractStatus((prev) => ({ ...prev, [docId]: 'error' }))
    }
  }

  const form106Docs = filteredDocuments.filter((d) => (d.document_type || 'form_106') === 'form_106')
  const summableFields = Object.entries(FORM_106_FIELDS)
    .filter(([k, v]) => v.type === 'number' && k !== 'tax_year')
    .map(([k]) => k)

  const aggregation = form106Docs.length >= 2
    ? summableFields.reduce(
        (acc, field) => {
          const sum = form106Docs.reduce((s, doc) => {
            const val = getFieldValue(doc, field).value
            return s + (typeof val === 'number' ? val : 0)
          }, 0)
          acc[field] = sum
          return acc
        },
        {} as Record<string, number>,
      )
    : null

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      {/* Page heading */}
      <h1 className="text-xl font-bold">מסמכים — שנת {taxYear}</h1>

      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors',
          dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50',
          uploading && 'pointer-events-none opacity-60',
        )}
      >
        {uploading ? (
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        ) : (
          <Upload className="h-10 w-10 text-muted-foreground" />
        )}
        <div>
          <p className="text-lg font-medium">גרור קבצי PDF, Excel או תמונה לכאן או לחץ לבחירה</p>
          <p className="text-sm text-muted-foreground">טופס 106, 867, אישור תשלום שכירות, קבלת רו"ח, חישוב שכירות (xlsx), ספח ת.ז. (תמונה) • ניתן להעלות מספר קבצים</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.xlsx,.jpg,.jpeg,.png,.webp"
          multiple
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files || [])
            if (files.length) handleFiles(files)
            e.target.value = ''
          }}
        />
      </div>

      {/* Error / skipped cards */}
      {errors.map((err, i) => (
        <Card key={i} className={err.status === 'skipped' ? 'border-muted' : 'border-destructive/50'}>
          <CardHeader className="pb-2">
            <CardTitle className={`flex items-center gap-2 ${err.status === 'skipped' ? 'text-muted-foreground' : 'text-destructive'}`}>
              <AlertCircle className="h-4 w-4" />
              {err.filename}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-sm ${err.status === 'skipped' ? 'text-muted-foreground' : 'text-destructive'}`}>{err.error}</p>
          </CardContent>
        </Card>
      ))}

      {/* Encrypted files — password prompt */}
      {encryptedFiles.length > 0 && (
        <Card className="border-yellow-500/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-700">
              <Lock className="h-5 w-5" />
              קבצים מוגנים בסיסמה
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {encryptedFiles.map((ef) => (
              <div key={ef.filename} className="flex items-center gap-3">
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 truncate text-sm">{ef.filename}</span>
                <Input
                  type="password"
                  placeholder="סיסמה"
                  className="h-8 w-48"
                  value={passwords[ef.filename] || ''}
                  onChange={(e) =>
                    setPasswords((prev) => ({ ...prev, [ef.filename]: e.target.value }))
                  }
                  onKeyDown={(e) => { if (e.key === 'Enter') retryWithPasswords() }}
                />
              </div>
            ))}
            <Button onClick={retryWithPasswords} disabled={uploading}>
              {uploading ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <Lock className="ml-2 h-4 w-4" />}
              נסה שוב עם סיסמה
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Document cards */}
      {filteredDocuments.length === 0 && !uploading && (
        <p className="text-center text-muted-foreground py-4">אין מסמכים לשנת {taxYear}. העלה קבצים באמצעות האזור למעלה.</p>
      )}
      {filteredDocuments.map((doc) => {
        const docType = doc.document_type || 'form_106'
        const fieldMap = getFieldMap(docType)
        const docYear = doc.extracted?.tax_year?.value
        return (
        <Card key={doc.doc_id}>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <span>{getDocTitle(doc)}</span>
              <span className="text-sm font-normal text-muted-foreground">({doc.original_filename})</span>
              {doc.user_corrected && (
                <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">תוקן</span>
              )}
              {docYear != null && Number(docYear) !== taxYear && (
                <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700" title={`מסמך לשנת ${docYear}, שנה נבחרת ${taxYear}`}>
                  <AlertTriangle className="h-3 w-3" />
                  שנת {docYear}
                </span>
              )}
            </CardTitle>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setViewerDoc(doc)}
                className="rounded p-1 text-muted-foreground hover:bg-primary/10 hover:text-primary"
                title="הצג מסמך וחילוץ"
              >
                <Eye className="h-4 w-4" />
              </button>
              <button
                onClick={() => reextractDocument(doc.doc_id)}
                className="rounded p-1 text-muted-foreground hover:bg-primary/10 hover:text-primary"
                title="חלץ מחדש"
              >
                {reextractStatus[doc.doc_id] === 'running' ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
              </button>
              <button
                onClick={() => deleteDocument(doc.doc_id)}
                className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="מחק מסמך"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="py-2 text-right font-medium">שדה</th>
                    <th className="py-2 text-right font-medium">שדה 1301</th>
                    <th className="py-2 text-right font-medium">ערך</th>
                    <th className="py-2 text-right font-medium">ביטחון</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(fieldMap).map(([field, meta]) => {
                    const fv = getFieldValue(doc, field)
                    return (
                      <tr key={field} className="border-b last:border-0">
                        <td className="py-2 font-medium">{meta.label_he}</td>
                        <td className="py-2 text-muted-foreground">{meta.field_1301}</td>
                        <td className="py-2">
                          <Input
                            type={meta.type === 'number' ? 'number' : 'text'}
                            value={fv.value ?? ''}
                            onChange={(e) => setFieldEdit(doc.doc_id, field, e.target.value, meta)}
                            className="h-8 w-40"
                          />
                        </td>
                        <td className="py-2">{confidenceBadge(fv.confidence)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {docType === 'id_supplement' && Array.isArray(doc.extracted?.children) && (
              <div className="mt-4">
                <h4 className="font-medium mb-2">ילדים</h4>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="py-1 text-right font-medium">שם</th>
                      <th className="py-1 text-right font-medium">ת.ז.</th>
                      <th className="py-1 text-right font-medium">תאריך לידה</th>
                      <th className="py-1 text-right font-medium">שנת לידה</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(doc.extracted.children as Array<{name?: string; id_number?: string; birth_date?: string; birth_year?: number}>).map((child, ci) => (
                      <tr key={ci} className="border-b last:border-0">
                        <td className="py-1">{child.name || '—'}</td>
                        <td className="py-1">{child.id_number || '—'}</td>
                        <td className="py-1">{child.birth_date || '—'}</td>
                        <td className="py-1">{child.birth_year || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {doc.extraction_warnings?.length ? (
              <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                {doc.extraction_warnings.map((warning) => (
                  <div key={warning}>{warning}</div>
                ))}
              </div>
            ) : null}
            <div className="mt-4 flex items-center gap-3">
              <Button
                onClick={() => saveCorrections(doc.doc_id)}
                disabled={!editedFields[doc.doc_id] || Object.keys(editedFields[doc.doc_id]).length === 0}
              >
                <Save className="ml-2 h-4 w-4" />
                שמור תיקונים
              </Button>
              <Button variant="outline" onClick={() => reextractDocument(doc.doc_id)} disabled={reextractStatus[doc.doc_id] === 'running'}>
                {reextractStatus[doc.doc_id] === 'running' ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="ml-2 h-4 w-4" />}
                חלץ מחדש
              </Button>
              {saveStatus[doc.doc_id] === 'saving' && <Loader2 className="h-4 w-4 animate-spin" />}
              {saveStatus[doc.doc_id] === 'saved' && (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <Check className="h-4 w-4" /> נשמר בהצלחה
                </span>
              )}
              {reextractStatus[doc.doc_id] === 'done' && <span className="text-sm text-green-600">החילוץ רוענן</span>}
              {reextractStatus[doc.doc_id] === 'error' && <span className="text-sm text-destructive">שגיאה בחילוץ מחדש</span>}
              {saveStatus[doc.doc_id] === 'error' && (
                <span className="text-sm text-destructive">שגיאה בשמירה</span>
              )}
            </div>
          </CardContent>
        </Card>
        )
      })}

      {/* Aggregation summary */}
      {aggregation && (
        <Card>
          <CardHeader>
            <CardTitle>סיכום כל המעסיקים</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="py-2 text-right font-medium">שדה</th>
                  <th className="py-2 text-right font-medium">סה״כ</th>
                </tr>
              </thead>
              <tbody>
                {summableFields.map((field) => {
                  const meta = FORM_106_FIELDS[field]
                  const val = aggregation[field]
                  return (
                    <tr key={field} className="border-b last:border-0">
                      <td className="py-2 font-medium">{meta.label_he}</td>
                      <td className="py-2">
                        {field !== 'work_days'
                          ? `₪${val.toLocaleString('he-IL')}`
                          : val.toLocaleString('he-IL')}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Document Viewer Dialog */}
      <Dialog open={viewerDoc !== null} onClose={() => setViewerDoc(null)}>
        {viewerDoc && (() => {
          const vDocType = viewerDoc.document_type || 'form_106'
          const vFieldMap = getFieldMap(vDocType)
          const vTypeLabel = DOC_TYPE_LABELS[vDocType] || vDocType
          const isImage = viewerDoc.original_filename.match(/\.(jpg|jpeg|png|webp)$/i)
          const isExcel = viewerDoc.original_filename.match(/\.xlsx$/i)
          const fileUrl = `/api/documents/${viewerDoc.doc_id}/file`

          return (
            <>
              <DialogHeader onClose={() => setViewerDoc(null)}>
                <DialogTitle>{vTypeLabel} — {viewerDoc.original_filename}</DialogTitle>
              </DialogHeader>
              <DialogContent className="p-0">
                <div className="flex h-[75vh]">
                  {/* Right side: Document preview */}
                  <div className="flex-1 border-l bg-muted/30 overflow-auto">
                    {isExcel ? (
                      <div className="flex h-full items-center justify-center text-muted-foreground">
                        <p>תצוגת Excel לא נתמכת — ניתן לפתוח את הקובץ ישירות</p>
                      </div>
                    ) : isImage ? (
                      <img
                        src={fileUrl}
                        alt={viewerDoc.original_filename}
                        className="h-full w-full object-contain"
                      />
                    ) : (
                      <iframe
                        src={fileUrl}
                        className="h-full w-full"
                        title={viewerDoc.original_filename}
                      />
                    )}
                  </div>
                  {/* Left side: Extracted fields */}
                  <div className="w-[400px] shrink-0 overflow-auto p-4">
                    <h3 className="mb-3 font-semibold text-sm">נתונים שחולצו</h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="py-2 text-right font-medium">שדה</th>
                          <th className="py-2 text-right font-medium">ערך</th>
                          <th className="py-2 text-right font-medium">ביטחון</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(vFieldMap).map(([field, meta]) => {
                          const fv = getFieldValue(viewerDoc, field)
                          return (
                            <tr key={field} className="border-b last:border-0">
                              <td className="py-2 font-medium">{meta.label_he}</td>
                              <td className="py-2">
                                <Input
                                  type={meta.type === 'number' ? 'number' : 'text'}
                                  value={fv.value ?? ''}
                                  onChange={(e) => setFieldEdit(viewerDoc.doc_id, field, e.target.value, meta)}
                                  className="h-7 w-32 text-sm"
                                />
                              </td>
                              <td className="py-2">{confidenceBadge(fv.confidence)}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                    {vDocType === 'id_supplement' && Array.isArray(viewerDoc.extracted?.children) && (
                      <div className="mt-4">
                        <h4 className="font-medium mb-2 text-sm">ילדים</h4>
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b">
                              <th className="py-1 text-right font-medium">שם</th>
                              <th className="py-1 text-right font-medium">שנת לידה</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(viewerDoc.extracted.children as Array<{name?: string; birth_year?: number}>).map((child, ci) => (
                              <tr key={ci} className="border-b last:border-0">
                                <td className="py-1">{child.name || '—'}</td>
                                <td className="py-1">{child.birth_year || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    <div className="mt-4">
                      <div className="flex items-center gap-2">
                        <Button
                          onClick={() => saveCorrections(viewerDoc.doc_id)}
                          disabled={!editedFields[viewerDoc.doc_id] || Object.keys(editedFields[viewerDoc.doc_id]).length === 0}
                          size="sm"
                        >
                          <Save className="ml-2 h-4 w-4" />
                          שמור תיקונים
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => reextractDocument(viewerDoc.doc_id)} disabled={reextractStatus[viewerDoc.doc_id] === 'running'}>
                          {reextractStatus[viewerDoc.doc_id] === 'running' ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="ml-2 h-4 w-4" />}
                          חלץ מחדש
                        </Button>
                      </div>
                      {viewerDoc.extraction_warnings?.length ? (
                        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                          {viewerDoc.extraction_warnings.map((warning) => (
                            <div key={warning}>{warning}</div>
                          ))}
                        </div>
                      ) : null}
                      {saveStatus[viewerDoc.doc_id] === 'saved' && (
                        <span className="mr-2 text-sm text-green-600">נשמר</span>
                      )}
                    </div>
                  </div>
                </div>
              </DialogContent>
            </>
          )
        })()}
      </Dialog>

      <FloatingChat snapshot={chatSnapshot} />
    </div>
  )
}
