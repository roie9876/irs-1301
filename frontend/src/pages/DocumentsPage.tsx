import { useCallback, useEffect, useRef, useState } from 'react'
import { Upload, FileText, Check, AlertCircle, Loader2, Save, Lock, Trash2, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useTaxYear } from '@/lib/tax-year-context'
import {
  api,
  uploadFiles,
  type DocumentInfo,
  type DocumentListResponse,
  type FieldValue,
  type Form106Extraction,
  type UploadResult,
} from '@/lib/api'
import { cn } from '@/lib/utils'

const FIELD_LABELS: Record<
  keyof Form106Extraction,
  { label_he: string; field_1301: string; type: 'string' | 'number' }
> = {
  employer_name: { label_he: 'שם המעסיק', field_1301: '—', type: 'string' },
  employer_id: { label_he: 'מספר מזהה מעסיק', field_1301: '—', type: 'string' },
  tax_year: { label_he: 'שנת מס', field_1301: '—', type: 'number' },
  gross_salary: { label_he: 'הכנסה ברוטו', field_1301: '158/172', type: 'number' },
  tax_withheld: { label_he: 'מס שנוכה במקור', field_1301: 'סעיף 84', type: 'number' },
  pension_employer: { label_he: 'הפרשות מעסיק לפנסיה', field_1301: '248/249', type: 'number' },
  insured_income: { label_he: 'הכנסה מבוטחת', field_1301: '244/245', type: 'number' },
  convalescence_pay: { label_he: 'דמי הבראה', field_1301: '011/012', type: 'number' },
  education_fund: { label_he: 'קרן השתלמות', field_1301: '218/219', type: 'number' },
  work_days: { label_he: 'ימי עבודה', field_1301: '—', type: 'number' },
  national_insurance: { label_he: 'ביטוח לאומי', field_1301: '—', type: 'number' },
  health_insurance: { label_he: 'ביטוח בריאות', field_1301: '—', type: 'number' },
}

const NUMERIC_FIELDS = Object.entries(FIELD_LABELS)
  .filter(([, v]) => v.type === 'number' && v.field_1301 !== '—')
  .map(([k]) => k as keyof Form106Extraction)

const SUMMABLE_FIELDS = Object.entries(FIELD_LABELS)
  .filter(([k, v]) => v.type === 'number' && k !== 'tax_year')
  .map(([k]) => k as keyof Form106Extraction)

function confidenceBadge(confidence: number) {
  if (confidence >= 0.8) return <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">{Math.round(confidence * 100)}%</span>
  if (confidence >= 0.5) return <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">{Math.round(confidence * 100)}%</span>
  return <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">{confidence > 0 ? `${Math.round(confidence * 100)}%` : '—'}</span>
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
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api<DocumentListResponse>('/documents')
      .then((data) => setDocuments(data.documents))
      .catch(() => {})
  }, [])

  const lastFilesRef = useRef<File[]>([])

  const handleFiles = useCallback(async (files: File[], filePasswords?: Record<string, string>) => {
    const pdfFiles = files.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfFiles.length === 0) return

    lastFilesRef.current = pdfFiles
    setUploading(true)
    setErrors([])
    try {
      const response = await uploadFiles(pdfFiles, filePasswords)
      const successes = response.results.filter((r) => r.status === 'success')
      const failures = response.results.filter((r) => r.status === 'error')
      const encrypted = response.results.filter((r) => r.status === 'encrypted')

      setDocuments((prev) => [
        ...prev,
        ...successes.map((r) => ({
          doc_id: r.doc_id,
          original_filename: r.filename,
          extracted: r.extracted!,
          user_corrected: false,
        })),
      ])
      setErrors(failures)

      // Track encrypted files for password retry
      const encFiles = encrypted.map((r) => ({
        file: pdfFiles.find((f) => f.name === r.filename)!,
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

  const getFieldValue = (doc: DocumentInfo, field: keyof Form106Extraction): FieldValue => {
    const edited = editedFields[doc.doc_id]?.[field]
    if (edited) return edited
    return doc.extracted[field]
  }

  const setFieldEdit = (docId: string, field: string, value: string) => {
    const meta = FIELD_LABELS[field as keyof Form106Extraction]
    const parsed: number | string | null = meta.type === 'number' ? (value === '' ? null : Number(value)) : value
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

  const aggregation = documents.length >= 2
    ? SUMMABLE_FIELDS.reduce(
        (acc, field) => {
          const sum = documents.reduce((s, doc) => {
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
          <p className="text-lg font-medium">גרור קבצי PDF לכאן או לחץ לבחירה</p>
          <p className="text-sm text-muted-foreground">טופס 106 בלבד • ניתן להעלות מספר קבצים</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files || [])
            if (files.length) handleFiles(files)
            e.target.value = ''
          }}
        />
      </div>

      {/* Error cards */}
      {errors.map((err, i) => (
        <Card key={i} className="border-destructive/50">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-4 w-4" />
              {err.filename}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-destructive">{err.error}</p>
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
      {documents.map((doc) => (
        <Card key={doc.doc_id}>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <span>{doc.extracted.employer_name.value || doc.original_filename}</span>
              <span className="text-sm font-normal text-muted-foreground">({doc.original_filename})</span>
              {doc.user_corrected && (
                <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">תוקן</span>
              )}
              {doc.extracted.tax_year.value != null && doc.extracted.tax_year.value !== taxYear && (
                <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700" title={`מסמך לשנת ${doc.extracted.tax_year.value}, שנה נבחרת ${taxYear}`}>
                  <AlertTriangle className="h-3 w-3" />
                  שנת {doc.extracted.tax_year.value}
                </span>
              )}
            </CardTitle>
            <button
              onClick={() => deleteDocument(doc.doc_id)}
              className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              title="מחק מסמך"
            >
              <Trash2 className="h-4 w-4" />
            </button>
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
                  {(Object.keys(FIELD_LABELS) as (keyof Form106Extraction)[]).map((field) => {
                    const meta = FIELD_LABELS[field]
                    const fv = getFieldValue(doc, field)
                    return (
                      <tr key={field} className="border-b last:border-0">
                        <td className="py-2 font-medium">{meta.label_he}</td>
                        <td className="py-2 text-muted-foreground">{meta.field_1301}</td>
                        <td className="py-2">
                          <Input
                            type={meta.type === 'number' ? 'number' : 'text'}
                            value={fv.value ?? ''}
                            onChange={(e) => setFieldEdit(doc.doc_id, field, e.target.value)}
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
            <div className="mt-4 flex items-center gap-3">
              <Button
                onClick={() => saveCorrections(doc.doc_id)}
                disabled={!editedFields[doc.doc_id] || Object.keys(editedFields[doc.doc_id]).length === 0}
              >
                <Save className="ml-2 h-4 w-4" />
                שמור תיקונים
              </Button>
              {saveStatus[doc.doc_id] === 'saving' && <Loader2 className="h-4 w-4 animate-spin" />}
              {saveStatus[doc.doc_id] === 'saved' && (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <Check className="h-4 w-4" /> נשמר בהצלחה
                </span>
              )}
              {saveStatus[doc.doc_id] === 'error' && (
                <span className="text-sm text-destructive">שגיאה בשמירה</span>
              )}
            </div>
          </CardContent>
        </Card>
      ))}

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
                {SUMMABLE_FIELDS.map((field) => {
                  const meta = FIELD_LABELS[field]
                  const val = aggregation[field]
                  return (
                    <tr key={field} className="border-b last:border-0">
                      <td className="py-2 font-medium">{meta.label_he}</td>
                      <td className="py-2">
                        {meta.type === 'number' && field !== 'work_days'
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
    </div>
  )
}
