import { useCallback, useEffect, useState } from 'react'
import { Calculator, AlertTriangle, TrendingDown, TrendingUp, Loader2, FileText, CheckCircle2, PenLine, ChevronDown, ChevronUp } from 'lucide-react'
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
  type Form1301Result,
} from '@/lib/api'
import { cn } from '@/lib/utils'

const DOC_TYPE_LABELS: Record<string, string> = {
  form_106: 'טופס 106',
  form_867: 'טופס 867 (דיבידנד/ריבית)',
  rental_payment: 'אישור תשלום מס שכירות',
  annual_summary: 'דוח שנתי מניות',
  receipt: 'קבלה/חשבונית',
  rental_excel: 'קובץ Excel שכירות',
  unknown: 'מסמך לא מזוהה',
}

function formatNIS(amount: number): string {
  return new Intl.NumberFormat('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 }).format(amount)
}

// --- Form field definitions matching IRS 1301 sections ---
interface FormFieldDef {
  code: string
  label: string
  key: string          // path into Form1301Result (e.g., 'income.field_158')
  source?: string      // auto-population source description
  inputKey?: string    // if manually editable, the key in inputs state
}

interface FormSectionDef {
  id: string
  partId: string
  title: string
  description?: string
  fields: FormFieldDef[]
}

const FORM_SECTIONS: FormSectionDef[] = [
  // === חלק ג — הכנסות מיגיעה אישית ===
  {
    id: 'business',
    partId: 'ג',
    title: 'סעיף 1 — הכנסה מעסק או משלח יד',
    fields: [
      { code: '150', label: 'עסק/משלח יד — נישום', key: 'income.field_150', inputKey: 'business_income_taxpayer' },
      { code: '170', label: 'עסק/משלח יד — בן/בת זוג', key: 'income.field_170', inputKey: 'business_income_spouse' },
    ],
  },
  {
    id: 'nii_self',
    partId: 'ג',
    title: 'סעיף 2א — תקבולי ביט"ל כעצמאי',
    fields: [
      { code: '250', label: 'ביט"ל עצמאי — נישום', key: 'income.field_250', inputKey: 'nii_self_employed_taxpayer' },
      { code: '270', label: 'ביט"ל עצמאי — בן/בת זוג', key: 'income.field_270', inputKey: 'nii_self_employed_spouse' },
    ],
  },
  {
    id: 'nii_employee',
    partId: 'ג',
    title: 'סעיף 2ב — תקבולי ביט"ל כשכיר',
    fields: [
      { code: '194', label: 'ביט"ל שכיר — נישום', key: 'income.field_194', inputKey: 'nii_employee_taxpayer' },
      { code: '196', label: 'ביט"ל שכיר — בן/בת זוג', key: 'income.field_196', inputKey: 'nii_employee_spouse' },
    ],
  },
  {
    id: 'salary',
    partId: 'ג',
    title: 'סעיף 3 — הכנסה ממשכורת',
    fields: [
      { code: '158', label: 'משכורת — נישום', key: 'income.field_158', source: 'טופס 106' },
      { code: '172', label: 'משכורת — בן/בת זוג', key: 'income.field_172', source: 'טופס 106' },
    ],
  },
  {
    id: 'shifts',
    partId: 'ג',
    title: 'סעיף 4 — עבודה במשמרות',
    fields: [
      { code: '069', label: 'משמרות — נישום', key: 'income.field_069', inputKey: 'shift_work_taxpayer' },
      { code: '068', label: 'משמרות — בן/בת זוג', key: 'income.field_068', inputKey: 'shift_work_spouse' },
    ],
  },
  {
    id: 'retirement',
    partId: 'ג',
    title: 'סעיף 5 — מענקי פרישה וקצבאות',
    fields: [
      { code: '258', label: 'מענקי פרישה/קצבאות — נישום', key: 'income.field_258', inputKey: 'retirement_grants_taxpayer' },
      { code: '272', label: 'מענקי פרישה/קצבאות — בן/בת זוג', key: 'income.field_272', inputKey: 'retirement_grants_spouse' },
    ],
  },
  // === חלק ד — הכנסות בשיעורי מס רגילים ===
  {
    id: 'real_estate',
    partId: 'ד',
    title: 'סעיף 8 — הכנסה מנכס בית',
    fields: [
      { code: '059', label: 'נכס בית — נישום', key: 'other_income.field_059', inputKey: 'real_estate_income_taxpayer' },
      { code: '201', label: 'נכס בית — בן/בת זוג', key: 'other_income.field_201', inputKey: 'real_estate_income_spouse' },
    ],
  },
  {
    id: 'other_income',
    partId: 'ד',
    title: 'סעיף 11 — הכנסות אחרות שאינן מיגיעה אישית',
    description: 'הכנסה סולארית, השכרת ציוד, תמלוגים',
    fields: [
      { code: '167', label: 'הכנסות אחרות — משותף', key: 'other_income.field_167', inputKey: 'other_income_joint' },
      { code: '305', label: 'הכנסות אחרות — נישום', key: 'other_income.field_305', inputKey: 'other_income_taxpayer' },
      { code: '205', label: 'הכנסות אחרות — בן/בת זוג', key: 'other_income.field_205', inputKey: 'other_income_spouse' },
    ],
  },
  // === חלק ה — הכנסות בשיעורי מס מיוחדים ===
  {
    id: 'interest_sec_15',
    partId: 'ה',
    title: 'סעיף 13 — ריבית ני"ע, דיבידנד מפעל מאושר — 15%',
    fields: [
      { code: '060', label: 'ריבית ני"ע 15% — נישום', key: 'special_rate.field_060', inputKey: 'interest_securities_15_taxpayer' },
      { code: '211', label: 'ריבית ני"ע 15% — בן/בת זוג', key: 'special_rate.field_211', inputKey: 'interest_securities_15_spouse' },
    ],
  },
  {
    id: 'interest_sec_20',
    partId: 'ה',
    title: 'סעיף 14 — ריבית ני"ע, קופ"ג — 20%',
    fields: [
      { code: '067', label: 'ריבית ני"ע 20% — נישום', key: 'special_rate.field_067', inputKey: 'interest_securities_20_taxpayer' },
      { code: '228', label: 'ריבית ני"ע 20% — בן/בת זוג', key: 'special_rate.field_228', inputKey: 'interest_securities_20_spouse' },
    ],
  },
  {
    id: 'interest_sec_25',
    partId: 'ה',
    title: 'סעיף 15 — ריבית ני"ע, קופ"ג — 25%',
    fields: [
      { code: '157', label: 'ריבית ני"ע 25% — נישום', key: 'special_rate.field_157', inputKey: 'interest_securities_25_taxpayer' },
      { code: '257', label: 'ריבית ני"ע 25% — בן/בת זוג', key: 'special_rate.field_257', inputKey: 'interest_securities_25_spouse' },
    ],
  },
  {
    id: 'dividend_preferred',
    partId: 'ה',
    title: 'סעיף 16 — דיבידנד מפעל מועדף/מאושר — 20%',
    fields: [
      { code: '173', label: 'דיבידנד מועדף 20% — נישום', key: 'special_rate.field_173', inputKey: 'dividend_preferred_20_taxpayer' },
      { code: '275', label: 'דיבידנד מועדף 20% — בן/בת זוג', key: 'special_rate.field_275', inputKey: 'dividend_preferred_20_spouse' },
    ],
  },
  {
    id: 'dividend_25',
    partId: 'ה',
    title: 'סעיף 17 — דיבידנד — 25%',
    description: 'דיבידנד ממניות, ESOP, קרנות נאמנות',
    fields: [
      { code: '141', label: 'דיבידנד 25% — נישום', key: 'special_rate.field_141', source: 'טופס 867 / דוח שנתי', inputKey: 'dividend_25_taxpayer' },
      { code: '241', label: 'דיבידנד 25% — בן/בת זוג', key: 'special_rate.field_241', inputKey: 'dividend_25_spouse' },
    ],
  },
  {
    id: 'dividend_30',
    partId: 'ה',
    title: 'סעיף 18 — דיבידנד בעל מניות מהותי — 30%',
    fields: [
      { code: '055', label: 'דיבידנד מהותי 30% — נישום', key: 'special_rate.field_055', inputKey: 'dividend_significant_30_taxpayer' },
      { code: '212', label: 'דיבידנד מהותי 30% — בן/בת זוג', key: 'special_rate.field_212', inputKey: 'dividend_significant_30_spouse' },
    ],
  },
  {
    id: 'interest_dep_15',
    partId: 'ה',
    title: 'סעיף 21 — ריבית פיקדונות/חסכונות — 15%',
    fields: [
      { code: '078', label: 'ריבית פיקדונות 15% — נישום', key: 'special_rate.field_078', inputKey: 'interest_deposits_15_taxpayer' },
      { code: '217', label: 'ריבית פיקדונות 15% — בן/בת זוג', key: 'special_rate.field_217', inputKey: 'interest_deposits_15_spouse' },
    ],
  },
  {
    id: 'interest_dep_20',
    partId: 'ה',
    title: 'סעיף 22 — ריבית פיקדונות/חסכונות — 20%',
    fields: [
      { code: '126', label: 'ריבית פיקדונות 20% — נישום', key: 'special_rate.field_126', inputKey: 'interest_deposits_20_taxpayer' },
      { code: '226', label: 'ריבית פיקדונות 20% — בן/בת זוג', key: 'special_rate.field_226', inputKey: 'interest_deposits_20_spouse' },
    ],
  },
  {
    id: 'interest_dep_25',
    partId: 'ה',
    title: 'סעיף 23 — ריבית פיקדונות/חסכונות — 25%',
    fields: [
      { code: '142', label: 'ריבית פיקדונות 25% — נישום', key: 'special_rate.field_142', source: 'טופס 867', inputKey: 'interest_deposits_25_taxpayer' },
      { code: '242', label: 'ריבית פיקדונות 25% — בן/בת זוג', key: 'special_rate.field_242', inputKey: 'interest_deposits_25_spouse' },
    ],
  },
  {
    id: 'rental_10',
    partId: 'ה',
    title: 'סעיף 24 — שכ"ד למגורים — מסלול 10%',
    fields: [
      { code: '222', label: 'שכ"ד למגורים 10% — נישום', key: 'special_rate.field_222', source: 'קובץ Excel', inputKey: 'rental_10_taxpayer' },
      { code: '284', label: 'שכ"ד למגורים 10% — בן/בת זוג', key: 'special_rate.field_284', inputKey: 'rental_10_spouse' },
    ],
  },
  {
    id: 'rental_abroad',
    partId: 'ה',
    title: 'סעיף 25 — שכ"ד מחו"ל — 15%',
    fields: [
      { code: '225', label: 'שכ"ד מחו"ל 15% — נישום', key: 'special_rate.field_225', inputKey: 'rental_abroad_15_taxpayer' },
      { code: '285', label: 'שכ"ד מחו"ל 15% — בן/בת זוג', key: 'special_rate.field_285', inputKey: 'rental_abroad_15_spouse' },
    ],
  },
  {
    id: 'gambling',
    partId: 'ה',
    title: 'סעיף 26 — הימורים, הגרלות, פרסים — 35%',
    fields: [
      { code: '227', label: 'הימורים/הגרלות 35% — נישום', key: 'special_rate.field_227', inputKey: 'gambling_35_taxpayer' },
      { code: '286', label: 'הימורים/הגרלות 35% — בן/בת זוג', key: 'special_rate.field_286', inputKey: 'gambling_35_spouse' },
    ],
  },
  {
    id: 'renewable',
    partId: 'ה',
    title: 'סעיף 27 — אנרגיות מתחדשות — 31%',
    fields: [
      { code: '335', label: 'אנרגיות מתחדשות 31% — נישום', key: 'special_rate.field_335', inputKey: 'renewable_energy_31_taxpayer' },
      { code: '337', label: 'אנרגיות מתחדשות 31% — בן/בת זוג', key: 'special_rate.field_337', inputKey: 'renewable_energy_31_spouse' },
    ],
  },
  {
    id: 'pension_dist',
    partId: 'ה',
    title: 'סעיף 28 — חלוקה לחיסכון פנסיוני — 20%',
    fields: [
      { code: '288', label: 'חלוקה לפנסיה 20% — נישום', key: 'special_rate.field_288', inputKey: 'pension_distribution_20_taxpayer' },
      { code: '338', label: 'חלוקה לפנסיה 20% — בן/בת זוג', key: 'special_rate.field_338', inputKey: 'pension_distribution_20_spouse' },
    ],
  },
  {
    id: 'unauthorized',
    partId: 'ה',
    title: 'סעיף 29 — משיכה שלא כדין מקופ"ג — 35%',
    fields: [
      { code: '213', label: 'משיכה שלא כדין 35% — נישום', key: 'special_rate.field_213', inputKey: 'unauthorized_withdrawal_35_taxpayer' },
      { code: '313', label: 'משיכה שלא כדין 35% — בן/בת זוג', key: 'special_rate.field_313', inputKey: 'unauthorized_withdrawal_35_spouse' },
    ],
  },
  // === חלק ח — רווח הון ===
  {
    id: 'capital_gains',
    partId: 'ח',
    title: 'חלק ח — רווח הון',
    description: 'מכירת מניות, RSU, ESPP, קריפטו',
    fields: [
      { code: '139', label: 'רווח הון 25%', key: 'capital_gains.field_139', inputKey: 'capital_gains' },
    ],
  },
  {
    id: 'crypto',
    partId: 'ח',
    title: 'הכנסות מקריפטו',
    description: 'רווח ממכירת מטבעות דיגיטליים — מדווח כרווח הון (שדה 139)',
    fields: [
      { code: '139*', label: 'רווח הון מקריפטו', key: '_crypto', inputKey: 'crypto_income' },
    ],
  },
  // === חלק י — הכנסות פטורות ===
  {
    id: 'exempt_disability',
    partId: 'י',
    title: 'סעיף 41 — פטור נכות 9(5)',
    fields: [
      { code: '109', label: 'פטור נכות — נישום', key: 'exempt.field_109', inputKey: 'exempt_disability_taxpayer' },
      { code: '309', label: 'פטור נכות — בן/בת זוג', key: 'exempt.field_309', inputKey: 'exempt_disability_spouse' },
    ],
  },
  {
    id: 'exempt_rental',
    partId: 'י',
    title: 'סעיף 42 — שכ"ד פטור',
    description: 'שכ"ד פטור ממס עד התקרה',
    fields: [
      { code: '332', label: 'שכ"ד פטור ממס', key: 'exempt.field_332', inputKey: 'exempt_rental_income' },
    ],
  },
  // === חלק יב — ניכויים אישיים ===
  {
    id: 'disability_ins_self',
    partId: 'יב',
    title: 'סעיף 49 — ביטוח אבדן כושר עבודה (עצמאי)',
    fields: [
      { code: '112', label: 'אבדן כושר עצמאי — נישום', key: 'deductions.field_112', inputKey: 'disability_insurance_self_taxpayer' },
      { code: '113', label: 'אבדן כושר עצמאי — בן/בת זוג', key: 'deductions.field_113', inputKey: 'disability_insurance_self_spouse' },
    ],
  },
  {
    id: 'disability_ins_emp',
    partId: 'יב',
    title: 'סעיף 50 — ביטוח אבדן כושר עבודה (שכיר)',
    fields: [
      { code: '206', label: 'אבדן כושר שכיר — נישום', key: 'deductions.field_206', inputKey: 'disability_insurance_employee_taxpayer' },
      { code: '207', label: 'אבדן כושר שכיר — בן/בת זוג', key: 'deductions.field_207', inputKey: 'disability_insurance_employee_spouse' },
    ],
  },
  {
    id: 'education_fund_self',
    partId: 'יב',
    title: 'סעיף 51 — קרן השתלמות לעצמאי',
    fields: [
      { code: '136', label: 'קרן השתלמות עצמאי — נישום', key: 'deductions.field_136', inputKey: 'education_fund_self_taxpayer' },
      { code: '137', label: 'קרן השתלמות עצמאי — בן/בת זוג', key: 'deductions.field_137', inputKey: 'education_fund_self_spouse' },
    ],
  },
  {
    id: 'education_fund_emp',
    partId: 'יב',
    title: 'סעיף 52 — משכורת לקרן השתלמות',
    fields: [
      { code: '218', label: 'קרן השתלמות שכיר — נישום', key: 'deductions.field_218', source: 'טופס 106' },
      { code: '219', label: 'קרן השתלמות שכיר — בן/בת זוג', key: 'deductions.field_219', source: 'טופס 106' },
    ],
  },
  {
    id: 'pension_self',
    partId: 'יב',
    title: 'סעיף 53 — קופ"ג כעמית עצמאי',
    fields: [
      { code: '135', label: 'קופ"ג עצמאי — נישום', key: 'deductions.field_135', inputKey: 'pension_self_taxpayer' },
      { code: '180', label: 'קופ"ג עצמאי — בן/בת זוג', key: 'deductions.field_180', inputKey: 'pension_self_spouse' },
    ],
  },
  {
    id: 'nii_non_work',
    partId: 'יב',
    title: 'סעיף 54 — ביט"ל על הכנסה שאינה עבודה',
    fields: [
      { code: '030', label: 'ביט"ל לא-עבודה — נישום', key: 'deductions.field_030', inputKey: 'nii_non_employment_taxpayer' },
      { code: '089', label: 'ביט"ל לא-עבודה — בן/בת זוג', key: 'deductions.field_089', inputKey: 'nii_non_employment_spouse' },
    ],
  },
  {
    id: 'insured_income',
    partId: 'יב',
    title: 'סעיף 58 — הכנסה מבוטחת',
    fields: [
      { code: '244', label: 'הכנסה מבוטחת — נישום', key: 'deductions.field_244', source: 'טופס 106' },
      { code: '245', label: 'הכנסה מבוטחת — בן/בת זוג', key: 'deductions.field_245', source: 'טופס 106' },
    ],
  },
  {
    id: 'pension_employer',
    partId: 'יב',
    title: 'סעיף 59 — הפקדות מעביד לקופות גמל',
    fields: [
      { code: '248', label: 'הפקדות מעביד — נישום', key: 'deductions.field_248', source: 'טופס 106' },
      { code: '249', label: 'הפקדות מעביד — בן/בת זוג', key: 'deductions.field_249', source: 'טופס 106' },
    ],
  },
  {
    id: 'convalescence',
    partId: 'יב',
    title: 'סעיף 60 — הפחתת דמי הבראה',
    fields: [
      { code: '011', label: 'דמי הבראה — נישום', key: 'deductions.field_011', source: 'טופס 106' },
      { code: '012', label: 'דמי הבראה — בן/בת זוג', key: 'deductions.field_012', source: 'טופס 106' },
    ],
  },
  // === חלק יג — נקודות זיכוי ===
  {
    id: 'credit_points',
    partId: 'יג',
    title: 'סעיפים 61-72 — נקודות זיכוי',
    description: 'תושב, ילדים, תואר, שחרור מצבא, הורה חד-הורי',
    fields: [
      { code: '020', label: 'נקודות זיכוי — נישום', key: 'credit_points.credit_points_taxpayer', inputKey: 'credit_points_taxpayer' },
      { code: '021', label: 'נקודות זיכוי — בן/בת זוג', key: 'credit_points.credit_points_spouse', inputKey: 'credit_points_spouse' },
      { code: '260', label: 'נקודות ילדים — נישום', key: 'credit_points.field_260', inputKey: 'children_credit_points_taxpayer' },
      { code: '262', label: 'נקודות ילדים — בן/בת זוג', key: 'credit_points.field_262', inputKey: 'children_credit_points_spouse' },
      { code: '026', label: 'הורה חד-הורי', key: 'credit_points.field_026', inputKey: 'single_parent_points' },
    ],
  },
  // === חלק יד — זיכויים ===
  {
    id: 'life_insurance',
    partId: 'יד',
    title: 'סעיף 73 — ביטוח חיים',
    description: 'ביטוח חיים (כולל משכנתא) — זיכוי 25%',
    fields: [
      { code: '036', label: 'ביטוח חיים — נישום', key: 'tax_credits.field_036', inputKey: 'life_insurance_taxpayer' },
      { code: '081', label: 'ביטוח חיים — בן/בת זוג', key: 'tax_credits.field_081', inputKey: 'life_insurance_spouse' },
    ],
  },
  {
    id: 'survivors_insurance',
    partId: 'יד',
    title: 'סעיף 74 — ביטוח קצבת שאירים',
    fields: [
      { code: '140', label: 'שאירים — נישום', key: 'tax_credits.field_140', inputKey: 'survivors_insurance_taxpayer' },
      { code: '240', label: 'שאירים — בן/בת זוג', key: 'tax_credits.field_240', inputKey: 'survivors_insurance_spouse' },
    ],
  },
  {
    id: 'pension_employee_credit',
    partId: 'יד',
    title: 'סעיף 75 — קצבה כעמית שכיר',
    description: 'הפרשות עובד לפנסיה — זיכוי 35%',
    fields: [
      { code: '045', label: 'עמית שכיר — נישום', key: 'tax_credits.field_045', source: 'טופס 106' },
      { code: '086', label: 'עמית שכיר — בן/בת זוג', key: 'tax_credits.field_086', source: 'טופס 106' },
    ],
  },
  {
    id: 'pension_self_credit',
    partId: 'יד',
    title: 'סעיף 76 — קצבה כעמית עצמאי',
    fields: [
      { code: '268', label: 'עמית עצמאי — נישום', key: 'tax_credits.field_268', inputKey: 'pension_self_credit_taxpayer' },
      { code: '269', label: 'עמית עצמאי — בן/בת זוג', key: 'tax_credits.field_269', inputKey: 'pension_self_credit_spouse' },
    ],
  },
  {
    id: 'institution_care',
    partId: 'יד',
    title: 'סעיף 77 — החזקת בן משפחה במוסד',
    fields: [
      { code: '132', label: 'מוסד — נישום', key: 'tax_credits.field_132', inputKey: 'institution_care_taxpayer' },
      { code: '232', label: 'מוסד — בן/בת זוג', key: 'tax_credits.field_232', inputKey: 'institution_care_spouse' },
    ],
  },
  {
    id: 'donations',
    partId: 'יד',
    title: 'סעיף 78 — תרומות למוסדות מוכרים',
    description: 'זיכוי 35%',
    fields: [
      { code: '037', label: 'תרומות ישראל — נישום', key: 'tax_credits.field_037', source: 'טופס 106', inputKey: 'donation_taxpayer' },
      { code: '237', label: 'תרומות ישראל — בן/בת זוג', key: 'tax_credits.field_237', inputKey: 'donation_spouse' },
      { code: '046', label: 'תרומות ארה"ב — נישום', key: 'tax_credits.field_046', inputKey: 'donation_us_taxpayer' },
      { code: '048', label: 'תרומות ארה"ב — בן/בת זוג', key: 'tax_credits.field_048', inputKey: 'donation_us_spouse' },
    ],
  },
  {
    id: 'rnd',
    partId: 'יד',
    title: 'סעיף 80 — השקעות במחקר ופיתוח',
    fields: [
      { code: '155', label: 'מו"פ — נישום', key: 'tax_credits.field_155', inputKey: 'rnd_investment_taxpayer' },
      { code: '199', label: 'מו"פ — בן/בת זוג', key: 'tax_credits.field_199', inputKey: 'rnd_investment_spouse' },
    ],
  },
  {
    id: 'eilat',
    partId: 'יד',
    title: 'סעיף 81 — תושב אילת/אזור פיתוח',
    fields: [
      { code: '183', label: 'הכנסה מזכה — אילת', key: 'tax_credits.field_183', inputKey: 'eilat_income_taxpayer' },
    ],
  },
  // === חלק טו — ניכויים במקור ===
  {
    id: 'tax_withheld_salary',
    partId: 'טו',
    title: 'סעיף 84 — מס שנוכה ממשכורת',
    fields: [
      { code: '042', label: 'מס שנוכה ממשכורת', key: 'withholdings.field_042', source: 'טופס 106' },
    ],
  },
  {
    id: 'tax_withheld_interest',
    partId: 'טו',
    title: 'סעיף 85 — ניכוי במקור מריבית ודיבידנד',
    fields: [
      { code: '043', label: 'מס שנוכה מריבית/דיבידנד', key: 'withholdings.field_043', source: 'טופס 867' },
    ],
  },
  {
    id: 'tax_withheld_other',
    partId: 'טו',
    title: 'סעיף 87 — ניכוי מס מהכנסות אחרות',
    fields: [
      { code: '040', label: 'מס שנוכה מהכנסות אחרות', key: 'withholdings.field_040', inputKey: 'withholding_other' },
    ],
  },
  {
    id: 'land_tax',
    partId: 'טו',
    title: 'סעיף 88 — מס שבח',
    fields: [
      { code: '041', label: 'מס שבח', key: 'withholdings.field_041', inputKey: 'land_appreciation_tax' },
    ],
  },
  {
    id: 'tax_advance',
    partId: 'טו',
    title: 'מקדמות מס שכירות ודוח שנתי',
    fields: [
      { code: '220', label: 'מס שכירות ששולם', key: 'withholdings.field_220', source: 'אישור תשלום', inputKey: 'rental_tax_paid' },
      { code: '---', label: 'מקדמות מדוח שנתי (ESOP)', key: 'withholdings.field_tax_advance', source: 'דוח שנתי' },
    ],
  },
]

function getFieldValue(result: Form1301Result, path: string): number {
  if (path.startsWith('_')) return 0 // virtual fields (crypto, solar, etc.)
  const parts = path.split('.')
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = result
  for (const p of parts) {
    obj = obj?.[p]
  }
  return typeof obj === 'number' ? obj : 0
}

export function Form1301Page() {
  const { taxYear } = useTaxYear()
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Form1301PreviewResponse | null>(null)
  const [error, setError] = useState('')
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  // Manual input fields
  const [inputs, setInputs] = useState<Record<string, string>>({
    // חלק ג
    business_income_taxpayer: '',
    business_income_spouse: '',
    nii_self_employed_taxpayer: '',
    nii_self_employed_spouse: '',
    nii_employee_taxpayer: '',
    nii_employee_spouse: '',
    shift_work_taxpayer: '',
    shift_work_spouse: '',
    retirement_grants_taxpayer: '',
    retirement_grants_spouse: '',
    // חלק ד
    real_estate_income_taxpayer: '',
    real_estate_income_spouse: '',
    other_income_taxpayer: '',
    other_income_spouse: '',
    other_income_joint: '',
    // חלק ה
    interest_securities_15_taxpayer: '',
    interest_securities_15_spouse: '',
    interest_securities_20_taxpayer: '',
    interest_securities_20_spouse: '',
    interest_securities_25_taxpayer: '',
    interest_securities_25_spouse: '',
    dividend_preferred_20_taxpayer: '',
    dividend_preferred_20_spouse: '',
    dividend_25_taxpayer: '',
    dividend_25_spouse: '',
    dividend_significant_30_taxpayer: '',
    dividend_significant_30_spouse: '',
    interest_deposits_15_taxpayer: '',
    interest_deposits_15_spouse: '',
    interest_deposits_20_taxpayer: '',
    interest_deposits_20_spouse: '',
    interest_deposits_25_taxpayer: '',
    interest_deposits_25_spouse: '',
    rental_10_taxpayer: '',
    rental_10_spouse: '',
    rental_abroad_15_taxpayer: '',
    rental_abroad_15_spouse: '',
    gambling_35_taxpayer: '',
    gambling_35_spouse: '',
    renewable_energy_31_taxpayer: '',
    renewable_energy_31_spouse: '',
    pension_distribution_20_taxpayer: '',
    pension_distribution_20_spouse: '',
    unauthorized_withdrawal_35_taxpayer: '',
    unauthorized_withdrawal_35_spouse: '',
    // חלק ח
    capital_gains: '',
    crypto_income: '',
    // חלק י
    exempt_rental_income: '',
    exempt_disability_taxpayer: '',
    exempt_disability_spouse: '',
    // חלק יב
    disability_insurance_self_taxpayer: '',
    disability_insurance_self_spouse: '',
    disability_insurance_employee_taxpayer: '',
    disability_insurance_employee_spouse: '',
    education_fund_self_taxpayer: '',
    education_fund_self_spouse: '',
    pension_self_taxpayer: '',
    pension_self_spouse: '',
    nii_non_employment_taxpayer: '',
    nii_non_employment_spouse: '',
    // חלק יג
    credit_points_taxpayer: '',
    credit_points_spouse: '',
    children_credit_points_taxpayer: '',
    children_credit_points_spouse: '',
    single_parent_points: '',
    // חלק יד
    life_insurance_taxpayer: '',
    life_insurance_spouse: '',
    survivors_insurance_taxpayer: '',
    survivors_insurance_spouse: '',
    pension_self_credit_taxpayer: '',
    pension_self_credit_spouse: '',
    institution_care_taxpayer: '',
    institution_care_spouse: '',
    donation_taxpayer: '',
    donation_spouse: '',
    donation_us_taxpayer: '',
    donation_us_spouse: '',
    rnd_investment_taxpayer: '',
    rnd_investment_spouse: '',
    eilat_income_taxpayer: '',
    // חלק טו
    rental_tax_paid: '',
    withholding_other: '',
    land_appreciation_tax: '',
  })

  // Load documents
  useEffect(() => {
    api<DocumentListResponse>('/documents')
      .then((data) => setDocuments(data.documents))
      .catch(() => {})
    setResult(null)
  }, [taxYear])

  const handleInputChange = (field: string, value: string) => {
    setInputs((prev) => ({ ...prev, [field]: value }))
  }

  const toggleSection = (id: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
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
      // Expand all sections after calculation
      setExpandedSections(new Set(FORM_SECTIONS.map((s) => s.id)))
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

  // Group sections by part
  const partGroups: { partId: string; title: string; sections: FormSectionDef[] }[] = [
    { partId: 'ג', title: 'חלק ג — הכנסות מיגיעה אישית', sections: [] },
    { partId: 'ד', title: 'חלק ד — הכנסות בשיעורי מס רגילים', sections: [] },
    { partId: 'ה', title: 'חלק ה — הכנסות בשיעורי מס מיוחדים', sections: [] },
    { partId: 'ח', title: 'חלק ח — רווח הון', sections: [] },
    { partId: 'י', title: 'חלק י — הכנסות פטורות', sections: [] },
    { partId: 'יב', title: 'חלק יב — ניכויים אישיים', sections: [] },
    { partId: 'יג', title: 'חלק יג — נקודות זיכוי', sections: [] },
    { partId: 'יד', title: 'חלק יד — זיכויים מהמס', sections: [] },
    { partId: 'טו', title: 'חלק טו — ניכויים במקור ותשלומים', sections: [] },
  ]
  for (const section of FORM_SECTIONS) {
    const group = partGroups.find((g) => g.partId === section.partId)
    if (group) group.sections.push(section)
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">מדריך מילוי טופס 1301 — שנת {taxYear}</h1>
      </div>

      {/* Uploaded documents summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            מסמכים שהועלו ({yearDocs.length})
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
            <div className="flex flex-wrap gap-2">
              {Object.entries(docsByType).map(([type, docs]) => (
                <div key={type} className="flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-sm">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                  <span>{DOC_TYPE_LABELS[type] || type}</span>
                  <span className="text-muted-foreground">({docs.length})</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Additional income questionnaire */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PenLine className="h-5 w-5" />
            הכנסות נוספות ונתונים ידניים
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            מלא כאן הכנסות שלא נמצאות במסמכים שהועלו. שדות ריקים = 0 או אוטומטי מהמסמכים.
          </p>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            מלא כאן הכנסות שלא נמצאות במסמכים שהועלו. שדות ריקים = 0 או אוטומטי.
            השדות מאורגנים לפי חלקי טופס 1301.
          </p>
          <div className="space-y-4">
            {/* חלק ג — הכנסות מיגיעה אישית */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1">חלק ג — הכנסות מיגיעה אישית</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="הכנסה מעסק — נישום (150)" id="business_income_taxpayer" value={inputs.business_income_taxpayer} onChange={handleInputChange} />
              <InputField label="הכנסה מעסק — בן/בת זוג (170)" id="business_income_spouse" value={inputs.business_income_spouse} onChange={handleInputChange} />
              <InputField label={'ביט"ל עצמאי — נישום (250)'} id="nii_self_employed_taxpayer" value={inputs.nii_self_employed_taxpayer} onChange={handleInputChange} />
              <InputField label={'ביט"ל עצמאי — בן/בת זוג (270)'} id="nii_self_employed_spouse" value={inputs.nii_self_employed_spouse} onChange={handleInputChange} />
              <InputField label={'ביט"ל שכיר — נישום (194)'} id="nii_employee_taxpayer" value={inputs.nii_employee_taxpayer} onChange={handleInputChange} />
              <InputField label={'ביט"ל שכיר — בן/בת זוג (196)'} id="nii_employee_spouse" value={inputs.nii_employee_spouse} onChange={handleInputChange} />
              <InputField label="משמרות — נישום (069)" id="shift_work_taxpayer" value={inputs.shift_work_taxpayer} onChange={handleInputChange} />
              <InputField label="משמרות — בן/בת זוג (068)" id="shift_work_spouse" value={inputs.shift_work_spouse} onChange={handleInputChange} />
              <InputField label="מענקי פרישה/קצבאות — נישום (258)" id="retirement_grants_taxpayer" value={inputs.retirement_grants_taxpayer} onChange={handleInputChange} />
              <InputField label="מענקי פרישה/קצבאות — בן/בת זוג (272)" id="retirement_grants_spouse" value={inputs.retirement_grants_spouse} onChange={handleInputChange} />
            </div>

            {/* חלק ד */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק ד — הכנסות בשיעורי מס רגילים</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="נכס בית — נישום (059)" id="real_estate_income_taxpayer" value={inputs.real_estate_income_taxpayer} onChange={handleInputChange} />
              <InputField label="נכס בית — בן/בת זוג (201)" id="real_estate_income_spouse" value={inputs.real_estate_income_spouse} onChange={handleInputChange} />
              <InputField label="הכנסות אחרות — משותף (167)" id="other_income_joint" value={inputs.other_income_joint} onChange={handleInputChange} />
              <InputField label="הכנסות אחרות — נישום (305)" id="other_income_taxpayer" value={inputs.other_income_taxpayer} onChange={handleInputChange} />
              <InputField label="הכנסות אחרות — בן/בת זוג (205)" id="other_income_spouse" value={inputs.other_income_spouse} onChange={handleInputChange} />
            </div>

            {/* חלק ה — שיעורי מס מיוחדים */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק ה — הכנסות בשיעורי מס מיוחדים</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="דיבידנד 25% — נישום (141)" id="dividend_25_taxpayer" value={inputs.dividend_25_taxpayer} onChange={handleInputChange} placeholder="אוטומטי מ-867" />
              <InputField label="דיבידנד 25% — בן/בת זוג (241)" id="dividend_25_spouse" value={inputs.dividend_25_spouse} onChange={handleInputChange} />
              <InputField label="ריבית פיקדונות 25% — נישום (142)" id="interest_deposits_25_taxpayer" value={inputs.interest_deposits_25_taxpayer} onChange={handleInputChange} placeholder="אוטומטי מ-867" />
              <InputField label="ריבית פיקדונות 25% — בן/בת זוג (242)" id="interest_deposits_25_spouse" value={inputs.interest_deposits_25_spouse} onChange={handleInputChange} />
              <InputField label="דיבידנד מהותי 30% — נישום (055)" id="dividend_significant_30_taxpayer" value={inputs.dividend_significant_30_taxpayer} onChange={handleInputChange} />
              <InputField label="דיבידנד מהותי 30% — בן/בת זוג (212)" id="dividend_significant_30_spouse" value={inputs.dividend_significant_30_spouse} onChange={handleInputChange} />
              <InputField label={'שכ"ד למגורים 10% — נישום (222)'} id="rental_10_taxpayer" value={inputs.rental_10_taxpayer} onChange={handleInputChange} placeholder="אוטומטי מ-Excel" />
              <InputField label={'שכ"ד למגורים 10% — בן/בת זוג (284)'} id="rental_10_spouse" value={inputs.rental_10_spouse} onChange={handleInputChange} />
              <InputField label={'שכ"ד מחו"ל 15% — נישום (225)'} id="rental_abroad_15_taxpayer" value={inputs.rental_abroad_15_taxpayer} onChange={handleInputChange} />
              <InputField label={'שכ"ד מחו"ל 15% — בן/בת זוג (285)'} id="rental_abroad_15_spouse" value={inputs.rental_abroad_15_spouse} onChange={handleInputChange} />
              <InputField label="הימורים/הגרלות 35% — נישום (227)" id="gambling_35_taxpayer" value={inputs.gambling_35_taxpayer} onChange={handleInputChange} />
              <InputField label="הימורים/הגרלות 35% — בן/בת זוג (286)" id="gambling_35_spouse" value={inputs.gambling_35_spouse} onChange={handleInputChange} />
              <InputField label="אנרגיות מתחדשות 31% — נישום (335)" id="renewable_energy_31_taxpayer" value={inputs.renewable_energy_31_taxpayer} onChange={handleInputChange} />
              <InputField label="אנרגיות מתחדשות 31% — בן/בת זוג (337)" id="renewable_energy_31_spouse" value={inputs.renewable_energy_31_spouse} onChange={handleInputChange} />
            </div>

            {/* חלק ח — רווח הון */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק ח — רווח הון</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="רווח הון — מניות/RSU (139)" id="capital_gains" value={inputs.capital_gains} onChange={handleInputChange} />
              <InputField label="רווח הון — קריפטו (→ 139)" id="crypto_income" value={inputs.crypto_income} onChange={handleInputChange} />
            </div>

            {/* חלק י — פטורות */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק י — הכנסות פטורות</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label={'שכ"ד פטור ממס (332)'} id="exempt_rental_income" value={inputs.exempt_rental_income} onChange={handleInputChange} />
              <InputField label="פטור נכות — נישום (109)" id="exempt_disability_taxpayer" value={inputs.exempt_disability_taxpayer} onChange={handleInputChange} />
              <InputField label="פטור נכות — בן/בת זוג (309)" id="exempt_disability_spouse" value={inputs.exempt_disability_spouse} onChange={handleInputChange} />
            </div>

            {/* חלק יב — ניכויים */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק יב — ניכויים אישיים</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="אבדן כושר עצמאי — נישום (112)" id="disability_insurance_self_taxpayer" value={inputs.disability_insurance_self_taxpayer} onChange={handleInputChange} />
              <InputField label="אבדן כושר עצמאי — בן/בת זוג (113)" id="disability_insurance_self_spouse" value={inputs.disability_insurance_self_spouse} onChange={handleInputChange} />
              <InputField label="אבדן כושר שכיר — נישום (206)" id="disability_insurance_employee_taxpayer" value={inputs.disability_insurance_employee_taxpayer} onChange={handleInputChange} />
              <InputField label="אבדן כושר שכיר — בן/בת זוג (207)" id="disability_insurance_employee_spouse" value={inputs.disability_insurance_employee_spouse} onChange={handleInputChange} />
              <InputField label="קרן השתלמות עצמאי — נישום (136)" id="education_fund_self_taxpayer" value={inputs.education_fund_self_taxpayer} onChange={handleInputChange} />
              <InputField label="קרן השתלמות עצמאי — בן/בת זוג (137)" id="education_fund_self_spouse" value={inputs.education_fund_self_spouse} onChange={handleInputChange} />
              <InputField label={'קופ"ג עצמאי — נישום (135)'} id="pension_self_taxpayer" value={inputs.pension_self_taxpayer} onChange={handleInputChange} />
              <InputField label={'קופ"ג עצמאי — בן/בת זוג (180)'} id="pension_self_spouse" value={inputs.pension_self_spouse} onChange={handleInputChange} />
              <InputField label={'ביט"ל לא-עבודה — נישום (030)'} id="nii_non_employment_taxpayer" value={inputs.nii_non_employment_taxpayer} onChange={handleInputChange} />
              <InputField label={'ביט"ל לא-עבודה — בן/בת זוג (089)'} id="nii_non_employment_spouse" value={inputs.nii_non_employment_spouse} onChange={handleInputChange} />
            </div>

            {/* חלק יג — נקודות זיכוי */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק יג — נקודות זיכוי</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="נקודות זיכוי — נישום (0=אוטומטי)" id="credit_points_taxpayer" value={inputs.credit_points_taxpayer} onChange={handleInputChange} placeholder="אוטומטי 2.25" step="0.25" />
              <InputField label="נקודות זיכוי — בן/בת זוג (0=אוטומטי)" id="credit_points_spouse" value={inputs.credit_points_spouse} onChange={handleInputChange} placeholder="אוטומטי 2.75" step="0.25" />
              <InputField label="נקודות ילדים — נישום (260)" id="children_credit_points_taxpayer" value={inputs.children_credit_points_taxpayer} onChange={handleInputChange} step="0.5" />
              <InputField label="נקודות ילדים — בן/בת זוג (262)" id="children_credit_points_spouse" value={inputs.children_credit_points_spouse} onChange={handleInputChange} step="0.5" />
              <InputField label="הורה חד-הורי (026)" id="single_parent_points" value={inputs.single_parent_points} onChange={handleInputChange} step="0.5" />
            </div>

            {/* חלק יד — זיכויים */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק יד — זיכויים מהמס</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="ביטוח חיים — נישום (036)" id="life_insurance_taxpayer" value={inputs.life_insurance_taxpayer} onChange={handleInputChange} />
              <InputField label="ביטוח חיים — בן/בת זוג (081)" id="life_insurance_spouse" value={inputs.life_insurance_spouse} onChange={handleInputChange} />
              <InputField label="שאירים — נישום (140)" id="survivors_insurance_taxpayer" value={inputs.survivors_insurance_taxpayer} onChange={handleInputChange} />
              <InputField label="שאירים — בן/בת זוג (240)" id="survivors_insurance_spouse" value={inputs.survivors_insurance_spouse} onChange={handleInputChange} />
              <InputField label="עמית עצמאי — נישום (268)" id="pension_self_credit_taxpayer" value={inputs.pension_self_credit_taxpayer} onChange={handleInputChange} />
              <InputField label="עמית עצמאי — בן/בת זוג (269)" id="pension_self_credit_spouse" value={inputs.pension_self_credit_spouse} onChange={handleInputChange} />
              <InputField label="מוסד — נישום (132)" id="institution_care_taxpayer" value={inputs.institution_care_taxpayer} onChange={handleInputChange} />
              <InputField label="מוסד — בן/בת זוג (232)" id="institution_care_spouse" value={inputs.institution_care_spouse} onChange={handleInputChange} />
              <InputField label="תרומות — נישום (037)" id="donation_taxpayer" value={inputs.donation_taxpayer} onChange={handleInputChange} placeholder="אוטומטי מ-106" />
              <InputField label="תרומות — בן/בת זוג (237)" id="donation_spouse" value={inputs.donation_spouse} onChange={handleInputChange} />
              <InputField label={'תרומות ארה"ב — נישום (046)'} id="donation_us_taxpayer" value={inputs.donation_us_taxpayer} onChange={handleInputChange} />
              <InputField label={'תרומות ארה"ב — בן/בת זוג (048)'} id="donation_us_spouse" value={inputs.donation_us_spouse} onChange={handleInputChange} />
              <InputField label={'מו"פ — נישום (155)'} id="rnd_investment_taxpayer" value={inputs.rnd_investment_taxpayer} onChange={handleInputChange} />
              <InputField label={'מו"פ — בן/בת זוג (199)'} id="rnd_investment_spouse" value={inputs.rnd_investment_spouse} onChange={handleInputChange} />
              <InputField label="אילת — הכנסה מזכה (183)" id="eilat_income_taxpayer" value={inputs.eilat_income_taxpayer} onChange={handleInputChange} />
            </div>

            {/* חלק טו — ניכויים במקור */}
            <h3 className="text-sm font-semibold text-muted-foreground border-b pb-1 mt-6">חלק טו — ניכויים במקור</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <InputField label="מס שכירות ששולם (220)" id="rental_tax_paid" value={inputs.rental_tax_paid} onChange={handleInputChange} placeholder="אוטומטי מאישור" />
              <InputField label="ניכוי מהכנסות אחרות (040)" id="withholding_other" value={inputs.withholding_other} onChange={handleInputChange} />
              <InputField label="מס שבח (041)" id="land_appreciation_tax" value={inputs.land_appreciation_tax} onChange={handleInputChange} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Calculate button */}
      <div className="flex justify-center">
        <Button onClick={handleCalculate} disabled={loading} size="lg" className="gap-2 px-8">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
          חשב והכן מדריך מילוי
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 p-3 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* ====== RESULTS — Form Filling Guide ====== */}
      {r && (
        <div className="space-y-4">
          {/* Balance card */}
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

          {/* === FORM FILLING GUIDE by Parts === */}
          <h2 className="text-lg font-bold mt-6">מדריך מילוי — לפי סעיפי טופס 1301</h2>
          <p className="text-sm text-muted-foreground -mt-2">
            מלא את הערכים הבאים בטופס המקוון של רשות המסים. שדות עם ✅ מאוכלסים אוטומטית.
          </p>

          {partGroups.filter((g) => g.sections.length > 0).map((group) => (
            <Card key={group.partId}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{group.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 p-0">
                {group.sections.map((section) => {
                  const isExpanded = expandedSections.has(section.id)
                  const hasValues = section.fields.some((f) => {
                    const val = getFieldValue(r, f.key)
                    return val !== 0
                  })

                  return (
                    <div key={section.id} className="border-t">
                      <button
                        onClick={() => toggleSection(section.id)}
                        className={cn(
                          'w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-muted/50 transition-colors text-right',
                          hasValues && 'font-medium',
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {hasValues && <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />}
                          <span>{section.title}</span>
                          {section.description && (
                            <span className="text-muted-foreground font-normal hidden md:inline">
                              — {section.description}
                            </span>
                          )}
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                        )}
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-3">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="text-muted-foreground text-xs">
                                <th className="text-right py-1 font-normal w-16">קוד שדה</th>
                                <th className="text-right py-1 font-normal">תיאור</th>
                                <th className="text-left py-1 font-normal w-32">ערך</th>
                                <th className="text-left py-1 font-normal w-24">מקור</th>
                              </tr>
                            </thead>
                            <tbody>
                              {section.fields.map((field) => {
                                const val = getFieldValue(r, field.key)
                                const inputVal = field.inputKey ? inputs[field.inputKey] : undefined
                                const isManual = !!inputVal && Number(inputVal) > 0
                                const isAuto = !isManual && val > 0 && !!field.source

                                return (
                                  <tr key={field.code} className={cn(val > 0 ? 'bg-blue-50/50' : '')}>
                                    <td className="py-1.5 font-mono text-xs font-bold text-blue-800">
                                      {field.code}
                                    </td>
                                    <td className="py-1.5">{field.label}</td>
                                    <td className="py-1.5 text-left tabular-nums font-medium">
                                      {val > 0 ? formatNIS(val) : (typeof val === 'string' && val ? val : '—')}
                                    </td>
                                    <td className="py-1.5 text-left text-xs">
                                      {isAuto && (
                                        <span className="text-green-700">✅ {field.source}</span>
                                      )}
                                      {isManual && (
                                        <span className="text-blue-700">✏️ ידני</span>
                                      )}
                                      {!isAuto && !isManual && field.inputKey && (
                                        <span className="text-muted-foreground">ידני</span>
                                      )}
                                      {!isAuto && !isManual && !field.inputKey && field.source && (
                                        <span className="text-muted-foreground">{field.source}</span>
                                      )}
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          ))}

          {/* Tax Calculation Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>חישוב מס</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <Row label="מס פרוגרסיבי — נישום" value={r.calculation.tax_regular_taxpayer} />
                  <Row label="מס פרוגרסיבי — בן/בת זוג" value={r.calculation.tax_regular_spouse} />
                  <Row label="מס 10% (שכ״ד למגורים)" value={r.calculation.tax_rental_10pct} />
                  <Row label="מס 15% (ריבית/שכ״ד חו״ל)" value={r.calculation.tax_15pct} />
                  <Row label="מס 20% (דיבידנד מועדף/ריבית)" value={r.calculation.tax_20pct} />
                  <Row label="מס 25% (דיבידנד/ריבית)" value={r.calculation.tax_25pct} />
                  <Row label="מס 30% (דיבידנד מהותי)" value={r.calculation.tax_30pct} />
                  <Row label="מס 31% (אנרגיות מתחדשות)" value={r.calculation.tax_31pct} />
                  <Row label="מס 35% (הימורים/משיכה שלא כדין)" value={r.calculation.tax_35pct} />
                  <Row label="מס רווח הון" value={r.calculation.tax_capital_gains} />
                  <Row label="מס יסף (3%)" value={r.calculation.surtax} highlight />
                  <Row label="סה״כ מס ברוטו" value={r.calculation.gross_tax} bold />
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Credits Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>זיכויים</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <Row label="נקודות זיכוי — נישום" value={r.calculation.credit_points_amount_taxpayer} negative />
                  <Row label="נקודות זיכוי — בן/בת זוג" value={r.calculation.credit_points_amount_spouse} negative />
                  <Row label="זיכוי פנסיה 45א — נישום" value={r.calculation.pension_employee_credit_taxpayer} negative />
                  <Row label="זיכוי פנסיה 45א — בן/בת זוג" value={r.calculation.pension_employee_credit_spouse} negative />
                  <Row label="זיכוי תרומות (35%)" value={r.calculation.donation_credit} negative />
                  <Row label="זיכוי ביטוח חיים — נישום" value={r.calculation.life_insurance_credit_taxpayer} negative />
                  <Row label="זיכוי ביטוח חיים — בן/בת זוג" value={r.calculation.life_insurance_credit_spouse} negative />
                  <Row label="סה״כ זיכויים נישום" value={r.calculation.total_credits_taxpayer} negative />
                  <Row label="סה״כ זיכויים בן/בת זוג" value={r.calculation.total_credits_spouse} negative />
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
                  <Row label="מס שנוכה ממשכורת (סעיף 84)" value={r.calculation.total_withheld} negative />
                  <Row label="ניכוי ריבית/דיבידנד (סעיף 85)" value={r.withholdings.field_043} negative />
                  <Row label="ניכוי מהכנסות אחרות (סעיף 87)" value={r.withholdings.field_040} negative />
                  <Row label="מס שבח (סעיף 88)" value={r.withholdings.field_041} negative />
                  <Row label="מקדמות מדוח שנתי" value={r.withholdings.field_tax_advance} negative />
                  <Row label="מס שכירות ששולם" value={r.withholdings.field_220} negative />
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

// --- Helper Components ---

function InputField({
  label, id, value, onChange, placeholder, step,
}: {
  label: string; id: string; value: string
  onChange: (id: string, val: string) => void
  placeholder?: string; step?: string
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs">{label}</Label>
      <Input
        id={id}
        type="number"
        step={step || '1'}
        placeholder={placeholder || '0'}
        value={value}
        onChange={(e) => onChange(id, e.target.value)}
        className="h-8 text-sm"
      />
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
