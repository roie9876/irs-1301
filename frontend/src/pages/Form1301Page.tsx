import { useCallback, useEffect, useState } from 'react'
import { Calculator, AlertTriangle, TrendingDown, TrendingUp, Loader2, FileText } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTaxYear } from '@/lib/tax-year-context'
import {
  api,
  type DocumentInfo,
  type DocumentListResponse,
  type Form1301PreviewResponse,
} from '@/lib/api'
import { cn } from '@/lib/utils'

const DOC_TYPE_LABELS: Record<string, string> = {
  form_106: 'טופס 106',
  form_867: 'טופס 867 (דיבידנד/ריבית)',
  rental_payment: 'אישור תשלום מס שכירות',
  annual_summary: 'דוח שנתי מניות',
  receipt: 'קבלה/חשבונית',
  unknown: 'מסמך לא מזוהה',
}

function formatNIS(amount: number): string {
  return new Intl.NumberFormat('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 }).format(amount)
}

export function Form1301Page() {
  const { taxYear } = useTaxYear()
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Form1301PreviewResponse | null>(null)
  const [error, setError] = useState('')

  // Manual input fields (override auto-populated values from documents)
  const [inputs, setInputs] = useState({
    rental_income: '',
    rental_tax_paid: '',
    dividend_income: '',
    interest_income: '',
    capital_gains: '',
    donation_taxpayer: '',
    donation_spouse: '',
    life_insurance_taxpayer: '',
    life_insurance_spouse: '',
    credit_points_taxpayer: '',
    credit_points_spouse: '',
  })

  // Load documents on mount
  useEffect(() => {
    api<DocumentListResponse>('/documents')
      .then((data) => setDocuments(data.documents))
      .catch(() => {})
  }, [])

  const handleInputChange = (field: string, value: string) => {
    setInputs((prev) => ({ ...prev, [field]: value }))
  }

  const handleCalculate = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ year: String(taxYear) })
      for (const [key, val] of Object.entries(inputs)) {
        if (val) params.set(key, val)
      }
      const data = await api<Form1301PreviewResponse>(`/form-1301/preview?${params}`)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'שגיאה בחישוב')
    } finally {
      setLoading(false)
    }
  }, [taxYear, inputs])

  const yearDocs = documents.filter((d) => {
    const ext = d.extracted
    const docYear = ext?.tax_year?.value
    return !docYear || Number(docYear) === taxYear
  })

  const docsByType = yearDocs.reduce<Record<string, DocumentInfo[]>>((acc, doc) => {
    const type = doc.document_type || 'form_106'
    if (!acc[type]) acc[type] = []
    acc[type].push(doc)
    return acc
  }, {})

  const r = result?.result
  const balance = r?.calculation.balance ?? 0

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">סימולציית טופס 1301 — שנת {taxYear}</h1>
      </div>

      {/* Uploaded documents summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            מסמכים שהועלו
          </CardTitle>
        </CardHeader>
        <CardContent>
          {yearDocs.length === 0 ? (
            <p className="text-muted-foreground">
              לא הועלו מסמכים לשנת {taxYear}. עבור ל
              <a href="/documents" className="text-primary underline mx-1">דף המסמכים</a>
              כדי להעלות טפסים.
            </p>
          ) : (
            <div className="space-y-2">
              {Object.entries(docsByType).map(([type, docs]) => (
                <div key={type} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="font-medium">{DOC_TYPE_LABELS[type] || type}</span>
                  <span className="rounded bg-muted px-2 py-0.5 text-sm">
                    {docs.length} {docs.length === 1 ? 'מסמך' : 'מסמכים'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Additional income inputs */}
      <Card>
        <CardHeader>
          <CardTitle>הכנסות נוספות (לא מ-106)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="rental_income">הכנסה משכירות למגורים (מסלול 10%)</Label>
              <Input
                id="rental_income"
                type="number"
                placeholder="0"
                value={inputs.rental_income}
                onChange={(e) => handleInputChange('rental_income', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rental_tax_paid">מס שכירות ששולם (אוטומטי מאישור תשלום)</Label>
              <Input
                id="rental_tax_paid"
                type="number"
                placeholder="אוטומטי"
                value={inputs.rental_tax_paid}
                onChange={(e) => handleInputChange('rental_tax_paid', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="dividend_income">הכנסה מדיבידנד (אוטומטי מ-867)</Label>
              <Input
                id="dividend_income"
                type="number"
                placeholder="אוטומטי"
                value={inputs.dividend_income}
                onChange={(e) => handleInputChange('dividend_income', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="interest_income">הכנסה מריבית (אוטומטי מ-867)</Label>
              <Input
                id="interest_income"
                type="number"
                placeholder="אוטומטי"
                value={inputs.interest_income}
                onChange={(e) => handleInputChange('interest_income', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="capital_gains">רווח הון</Label>
              <Input
                id="capital_gains"
                type="number"
                placeholder="0"
                value={inputs.capital_gains}
                onChange={(e) => handleInputChange('capital_gains', e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Credits & deductions */}
      <Card>
        <CardHeader>
          <CardTitle>זיכויים וניכויים</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="donation_taxpayer">תרומות — נישום</Label>
              <Input
                id="donation_taxpayer"
                type="number"
                placeholder="0"
                value={inputs.donation_taxpayer}
                onChange={(e) => handleInputChange('donation_taxpayer', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="donation_spouse">תרומות — בן/בת זוג</Label>
              <Input
                id="donation_spouse"
                type="number"
                placeholder="0"
                value={inputs.donation_spouse}
                onChange={(e) => handleInputChange('donation_spouse', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="life_insurance_taxpayer">ביטוח חיים — נישום</Label>
              <Input
                id="life_insurance_taxpayer"
                type="number"
                placeholder="0"
                value={inputs.life_insurance_taxpayer}
                onChange={(e) => handleInputChange('life_insurance_taxpayer', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="life_insurance_spouse">ביטוח חיים — בן/בת זוג</Label>
              <Input
                id="life_insurance_spouse"
                type="number"
                placeholder="0"
                value={inputs.life_insurance_spouse}
                onChange={(e) => handleInputChange('life_insurance_spouse', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="credit_points_taxpayer">נקודות זיכוי — נישום (0 = אוטומטי)</Label>
              <Input
                id="credit_points_taxpayer"
                type="number"
                step="0.25"
                placeholder="אוטומטי"
                value={inputs.credit_points_taxpayer}
                onChange={(e) => handleInputChange('credit_points_taxpayer', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="credit_points_spouse">נקודות זיכוי — בן/בת זוג (0 = אוטומטי)</Label>
              <Input
                id="credit_points_spouse"
                type="number"
                step="0.25"
                placeholder="אוטומטי"
                value={inputs.credit_points_spouse}
                onChange={(e) => handleInputChange('credit_points_spouse', e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Calculate button */}
      <div className="flex justify-center">
        <Button onClick={handleCalculate} disabled={loading} size="lg" className="gap-2 px-8">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
          חשב טופס 1301
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 p-3 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Results */}
      {r && (
        <div className="space-y-4">
          {/* Balance card — the main result */}
          <Card className={cn(
            'border-2',
            balance > 0 ? 'border-red-300 bg-red-50' : 'border-green-300 bg-green-50'
          )}>
            <CardContent className="flex items-center justify-between py-6">
              <div className="flex items-center gap-3">
                {balance > 0 ? (
                  <TrendingUp className="h-8 w-8 text-red-600" />
                ) : (
                  <TrendingDown className="h-8 w-8 text-green-600" />
                )}
                <div>
                  <p className="text-lg font-bold">
                    {balance > 0 ? 'יתרה לתשלום' : 'החזר מס'}
                  </p>
                  <p className={cn(
                    'text-3xl font-bold',
                    balance > 0 ? 'text-red-700' : 'text-green-700'
                  )}>
                    {formatNIS(Math.abs(balance))}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Income breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>פירוט הכנסות</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <Row label="משכורת — נישום (שדה 158)" value={r.income.field_158} />
                  <Row label="משכורת — בן/בת זוג (שדה 172)" value={r.income.field_172} />
                  <Row label="שכירות למגורים 10% (שדה 222)" value={r.income.field_222} />
                  <Row label="דיבידנד 25% (שדה 141)" value={r.income.field_141} />
                  <Row label="ריבית 25% (שדה 327)" value={r.income.field_327} />
                  <Row label="רווח הון 25% (שדה 139)" value={r.income.field_139} />
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Tax calculation breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>פירוט מס</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <Row label="מס פרוגרסיבי — נישום" value={r.calculation.tax_regular_taxpayer} />
                  <Row label="מס פרוגרסיבי — בן/בת זוג" value={r.calculation.tax_regular_spouse} />
                  <Row label="מס שכירות 10%" value={r.calculation.tax_rental_10pct} />
                  <Row label="מס דיבידנד 25%" value={r.calculation.tax_dividend_25pct} />
                  <Row label="מס ריבית 25%" value={r.calculation.tax_interest_25pct} />
                  <Row label="מס רווח הון" value={r.calculation.tax_capital_gains} />
                  <Row label="מס יסף (3%)" value={r.calculation.surtax} highlight />
                  <Row label="סה״כ מס ברוטו" value={r.calculation.gross_tax} bold />
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Credits */}
          <Card>
            <CardHeader>
              <CardTitle>זיכויים</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <Row label="נקודות זיכוי — נישום" value={r.calculation.credit_points_amount_taxpayer} negative />
                  <Row label="נקודות זיכוי — בן/בת זוג" value={r.calculation.credit_points_amount_spouse} negative />
                  <Row label="זיכוי פנסיה — נישום" value={r.calculation.pension_credit_taxpayer} negative />
                  <Row label="זיכוי פנסיה — בן/בת זוג" value={r.calculation.pension_credit_spouse} negative />
                  <Row label="זיכוי תרומות (35%)" value={r.calculation.donation_credit} negative />
                  <Row label="זיכוי ביטוח חיים (25%)" value={r.calculation.life_insurance_credit} negative />
                  <Row label="סה״כ זיכויים" value={r.calculation.total_credits} bold negative />
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle>סיכום</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <Row label="מס נטו (אחרי זיכויים)" value={r.calculation.net_tax} bold />
                  <Row label="מס שנוכה במקור" value={r.calculation.total_withheld} negative />
                  <Row label="מס שכירות ששולם" value={r.calculation.total_paid - r.calculation.total_withheld} negative />
                  <Row label="סה״כ ששולם" value={r.calculation.total_paid} bold negative />
                  <tr className="border-t-2 border-foreground">
                    <td className="py-2 font-bold text-base">
                      {balance > 0 ? 'יתרה לתשלום' : 'החזר מס'}
                    </td>
                    <td className={cn(
                      'py-2 text-left font-bold text-base',
                      balance > 0 ? 'text-red-600' : 'text-green-600'
                    )}>
                      {formatNIS(Math.abs(balance))}
                    </td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Warnings */}
          {r.warnings.length > 0 && (
            <Card className="border-yellow-300 bg-yellow-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-yellow-700">
                  <AlertTriangle className="h-5 w-5" />
                  אזהרות
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc list-inside space-y-1 text-yellow-700">
                  {r.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Source documents */}
          {r.source_documents.length > 0 && (
            <p className="text-xs text-muted-foreground">
              מקור: {r.source_documents.join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function Row({
  label,
  value,
  bold,
  highlight,
  negative,
}: {
  label: string
  value: number
  bold?: boolean
  highlight?: boolean
  negative?: boolean
}) {
  if (value === 0) return null
  return (
    <tr className={cn(highlight && 'bg-yellow-50')}>
      <td className={cn('py-1.5', bold && 'font-bold')}>{label}</td>
      <td className={cn(
        'py-1.5 text-left tabular-nums',
        bold && 'font-bold',
        negative && 'text-green-700',
      )}>
        {negative && value > 0 ? '-' : ''}{formatNIS(value)}
      </td>
    </tr>
  )
}
