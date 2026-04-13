import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Calculator, AlertTriangle, TrendingDown, TrendingUp,
  Loader2, FileText, CheckCircle2, Save, MessageCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTaxYear } from '@/lib/tax-year-context'
import {
  api,
  type DocumentInfo,
  type DocumentListResponse,
  type FieldHelpResponse,
  type Form1301PreviewResponse,
  type Form1301Result,
} from '@/lib/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import { FloatingChat, type FormSnapshot, type FloatingChatHandle } from '@/components/FloatingChat'

type FormTab = 'personal' | 'general' | 'income'

type GeneralRow = {
  code: string
  label: string
  explanation: string
  type: 'radio' | 'checkbox' | 'select' | 'immigrant-status-date' | 'radio-with-select' | 'radio-with-text' | 'checkbox-group'
  options?: Array<{ value: string; label: string }>
  hint?: string
  displayCode?: string
}

const PERSONAL_STATUS_OPTIONS = ['רווק', 'נשוי', 'אלמן', 'גרוש', 'פרוד']

const PERSONAL_SUMMARY_FIELDS = [
  { key: 'tax_file_number', label: 'מספר תיק' },
  { key: 'tax_year', label: 'שנת מס' },
  { key: 'taxpayer_first_name', label: 'שם פרטי' },
  { key: 'taxpayer_last_name', label: 'שם משפחה' },
  { key: 'taxpayer_occupation', label: 'עיסוק' },
  { key: 'branch_code', label: 'פקיד שומה' },
]

const GENERAL_INFO_SECTIONS: Array<{ title: string; rows: GeneralRow[] }> = [
  {
    title: 'פרטים כלליים והצהרות בסיס',
    rows: [
      { code: 'foreign_income_file', label: 'האם אחד מבעלי מספר תיק - הכנסות מחו"ל?', explanation: 'סמן כן אם לך או לבן/בת הזוג היו הכנסות מחוץ לישראל שצריך לדווח עליהן, למשל שכר, דיבידנד, ריבית, שכירות או עסק בחו"ל.', type: 'radio', displayCode: 'חו"ל' },
      { code: 'foreign_income_household', label: 'האם היו לך/לבן זוגך הכנסות חוץ?', explanation: 'זו שאלה דומה אך ברמת משק הבית. אם למי מכם הייתה הכנסה ממקור זר במהלך השנה, בחר כן.', type: 'radio', displayCode: 'חו"ל' },
      {
        code: 'settlement_type',
        label: 'סוג היישוב',
        explanation: 'בחר את סוג היישוב רק אם הייתה זכאות להטבת מס כתושב יישוב מזכה. ברוב המקרים בוחרים יישוב רגיל.',
        type: 'select',
        options: [
          { value: 'regular', label: 'יישוב רגיל' },
          { value: 'priority_a', label: 'יישוב מזכה א' },
          { value: 'priority_b', label: 'יישוב מזכה ב' },
          { value: 'development', label: 'עיירת פיתוח / אזור מוטב' },
        ],
      },
      {
        code: 'aliyah_household_scope',
        label: 'בה"ח/י עולה',
        explanation: 'זה קיצור לשאלה אם אחד מבני הזוג הוא עולה חדש או תושב חוזר הזכאי להקלות מס, והאם ההקלות מתייחסות להכנסות של משק הבית כולו או רק של אותו אדם.',
        type: 'select',
        options: [
          { value: 'household', label: 'הכנסותי והכנסות בן/בת זוגי' },
          { value: 'self_only', label: 'הנני בלבד' },
          { value: 'separate_report', label: 'אני מגיש דוח גם אם לא חלות על הכנסותי הקלות מס' },
        ],
      },
      {
        code: 'spouse_report_mode',
        label: 'בן/בת זוג',
        explanation: 'כאן מציינים אם לבן או לבת הזוג יש דוח נפרד, אין הכנסה, או שהם סייעו בהפקת ההכנסה שלך. זה משפיע על ייחוס הכנסות בין בני הזוג.',
        type: 'radio-with-select',
        options: [
          { value: 'separate_report', label: 'בן/בת זוגי מגיש דוח נפרד' },
          { value: 'no_income', label: 'אין הכנסה לבן/בת זוגי' },
          { value: 'assisted_income', label: 'בן/בת זוגי עזר לי בהשגת ההכנסה' },
        ],
      },
    ],
  },
  {
    title: 'נתוני משפחה ותושבות',
    rows: [
      {
        code: '331',
        label: 'מקור הכנסה משותף/ביקור הכנסת משפחתי לבן/בת הזוג',
        explanation: 'השדה הזה בודק אם יש מקור הכנסה משותף לך ולבן/בת הזוג, או אם בן/בת הזוג סייעו בהפקת ההכנסה. בדרך כלל מסמנים כן רק אם באמת יש פעילות משותפת.',
        type: 'radio-with-select',
        options: [
          { value: 'section_66d', label: 'עמדתי בתנאי סעיף 66(ד) לפקודה' },
          { value: 'not_section_66d', label: 'לא עמדתי בתנאי סעיף 66(ד) לפקודה' },
        ],
      },
      { code: '273', label: 'בן זוג רשום - עולה חדש/תושב חוזר ותיק/רגיל הזכאי להקלות במס', explanation: 'ממלאים רק אם בן הזוג הרשום קיבל מעמד של עולה חדש או תושב חוזר שמזכה בהטבות מס. יש לציין גם את תאריך העלייה או החזרה.', type: 'immigrant-status-date' },
      { code: '274', label: 'בן/בת זוג - עולה חדש/תושב חוזר ותיק/רגיל הזכאי להקלות במס', explanation: 'ממלאים רק אם בן או בת הזוג קיבלו מעמד כזה. אם לא, משאירים ריק.', type: 'immigrant-status-date' },
    ],
  },
  {
    title: 'חו"ל ותכנוני מס',
    rows: [
      { code: '297', label: 'האם חלו חובות מחו"ל', explanation: 'סמן כן אם היו חובות דיווח או הכנסות שמקורן מחוץ לישראל ושיש להן השפעה על הדוח.', type: 'radio' },
      { code: '107', label: 'נכס בחו"ל', explanation: 'סמן אם החזקת נכס מחוץ לישראל, למשל דירה, חשבון השקעות או נכס אחר שיש לו משמעות לדיווח.', type: 'checkbox' },
      {
        code: '108',
        label: 'נאמנות',
        explanation: 'השדה מיועד למצבים שבהם אתה יוצר, נהנה או מקבל חלוקות מנאמנות. אם אין לך קשר לנאמנות, השאר לא מסומן.',
        type: 'checkbox-group',
        options: [
          { value: 'creator', label: 'יוצר/נהנה בנאמנות - הכנסות הנאמנות כלולות בדוח זה' },
          { value: 'beneficiary_report', label: 'נהנה בנאמנות שההכנסות שחולקו לי כלולות בדוח זה' },
          { value: 'beneficiary_distributions', label: 'נהנה בנאמנות שממנה היו לי חלוקות בשנת המס' },
        ],
      },
      {
        code: '263',
        label: 'תכנון מס / פעולה החייבת בדיווח',
        explanation: 'מסמנים כן רק אם בוצעה פעולה שמחייבת דיווח מיוחד לרשות המסים, למשל תכנון מס לפי הרשימות המחייבות. אם אינך יודע, בדרך כלל זה לא סעיף שמסמנים סתם כך.',
        type: 'radio-with-text',
        hint: 'כאשר מסומן "כן" יש לציין את קוד הטופס או האסמכתה הרלוונטית.',
      },
      { code: '259', label: 'סיום בנייה / דירה לקופה', explanation: 'זהו שדה חריג הקשור למצבים נדל"ניים מסוימים. אם אין לך אירוע כזה או שלא קיבלת הנחיה מפורשת, לרוב בוחרים ברירת מחדל או משאירים ריק.', type: 'select' },
      { code: '365', label: 'בקשה לייחוס הכנסות בין בני זוג', explanation: 'כאן מסמנים אם מבקשים לייחס הכנסות מסוימות בין בני הזוג לפי הכללים בדין. ממלאים רק אם יש צורך אמיתי בחלוקה שונה של ההכנסות.', type: 'radio' },
    ],
  },
  {
    title: 'נתונים עסקיים והוצאות מיוחדות',
    rows: [
      { code: '150', label: 'הנני בעל שליטה בחבר בני אדם אשר סכום מסוים ממנו מדווח בטופס 150', explanation: 'מסמנים כן אם אתה בעל שליטה בחברה ויש לך חובת דיווח רלוונטית בטופס 150. אחרת משאירים לא.', type: 'radio' },
      { code: '034', label: 'הפקת תיעוד פנים / הוצאות הפקת הכנסה', explanation: 'שדה זה מתייחס להוצאות הקשורות ליצירת ההכנסה, למשל שכ"ט רו"ח או הוצאות מקצועיות. אם אין הוצאות כאלה, בחר לא.', type: 'radio' },
      { code: '307', label: 'הכנסות פטורות / אנרגיות מתחדשות / פעילות באינטרנט', explanation: 'זהו סעיף הצהרתי למצבים מיוחדים. אם לא הייתה לך פעילות כזו, אל תסמן.', type: 'checkbox' },
    ],
  },
]

const DOC_TYPE_LABELS: Record<string, string> = {
  form_106: 'טופס 106',
  form_867: 'טופס 867',
  rental_payment: 'אישור תשלום שכירות',
  annual_summary: 'דוח שנתי מניות',
  receipt: 'קבלה/חשבונית',
  rental_excel: 'Excel שכירות',
  unknown: 'לא מזוהה',
}

function formatNIS(amount: number): string {
  return new Intl.NumberFormat('he-IL', {
    style: 'currency', currency: 'ILS', maximumFractionDigits: 0,
  }).format(amount)
}

// --- IRS form data structure ---

interface CellDef {
  code: string
  resultKey: string
  inputKey?: string
  placeholder?: string
  step?: string
}

interface IRSRow {
  num: number
  description: string
  notes?: string[]
  taxpayer?: CellDef
  spouse?: CellDef
}

interface IRSSection {
  partId: string
  title: string
  rows: IRSRow[]
}

type AdvisorItem = {
  id: string
  title: string
  detail: string
  level: 'info' | 'warn' | 'missing'
}

type SavedDraft = {
  activeTab: FormTab
  personalForm: Record<string, string>
  generalForm: Record<string, string>
  inputs: Record<string, string>
  savedAt: string
  draftVersion?: number
}

const DRAFT_VERSION = 2

const IRS_SECTIONS: IRSSection[] = [
  // ===== ג — הכנסות חייבות בשיעורי מס רגילים =====
  {
    partId: 'ג',
    title: 'ג. הכנסות חייבות בשיעורי מס רגילים',
    rows: [
      {
        num: 1, description: 'הכנסה מעסק או משלח יד',
        taxpayer: { code: '150', resultKey: 'income.field_150', inputKey: 'business_income_taxpayer' },
        spouse: { code: '170', resultKey: 'income.field_170', inputKey: 'business_income_spouse' },
      },
      {
        num: 2, description: 'תקבולי ביטוח לאומי — עצמאי',
        taxpayer: { code: '250', resultKey: 'income.field_250', inputKey: 'nii_self_employed_taxpayer' },
        spouse: { code: '270', resultKey: 'income.field_270', inputKey: 'nii_self_employed_spouse' },
      },
      {
        num: 3, description: 'תקבולי ביטוח לאומי — שכיר',
        taxpayer: { code: '194', resultKey: 'income.field_194', inputKey: 'nii_employee_taxpayer' },
        spouse: { code: '196', resultKey: 'income.field_196', inputKey: 'nii_employee_spouse' },
      },
      {
        num: 4, description: 'הכנסה ממשכורת',
        taxpayer: { code: '158', resultKey: 'income.field_158' },
        spouse: { code: '172', resultKey: 'income.field_172' },
      },
      {
        num: 5, description: 'עבודה במשמרות',
        taxpayer: { code: '069', resultKey: 'income.field_069', inputKey: 'shift_work_taxpayer' },
        spouse: { code: '068', resultKey: 'income.field_068', inputKey: 'shift_work_spouse' },
      },
      {
        num: 6, description: 'מענקי פרישה וקצבאות',
        taxpayer: { code: '258', resultKey: 'income.field_258', inputKey: 'retirement_grants_taxpayer' },
        spouse: { code: '272', resultKey: 'income.field_272', inputKey: 'retirement_grants_spouse' },
      },
      {
        num: 7, description: 'השתכרות מביטוח אבטלה / מילואים / דמי לידה',
        taxpayer: { code: '120', resultKey: '_unemployment_tp', inputKey: 'unemployment_benefits_taxpayer' },
        spouse: { code: '220', resultKey: '_unemployment_sp', inputKey: 'unemployment_benefits_spouse' },
      },
      {
        num: 8,
        description: 'הכנסות אחרות מיגיעה אישית בארץ',
        notes: ['לרבות הכנסה שאינה ממשכורת או שכר עבודה רגיל'],
        taxpayer: { code: '007', resultKey: '_other_personal_tp', inputKey: 'other_personal_income_taxpayer' },
        spouse: { code: '013', resultKey: '_other_personal_sp', inputKey: 'other_personal_income_spouse' },
      },
    ],
  },
  // ===== ד — הכנסות אחרות בשיעורי מס רגילים =====
  {
    partId: 'ד',
    title: 'ד. הכנסות אחרות בשיעורי מס רגילים',
    rows: [
      {
        num: 7, description: 'הכנסה מנכס בית',
        taxpayer: { code: '059', resultKey: 'other_income.field_059', inputKey: 'real_estate_income_taxpayer' },
        spouse: { code: '201', resultKey: 'other_income.field_201', inputKey: 'real_estate_income_spouse' },
      },
      {
        num: 10, description: 'הכנסות מהשכרת מקרקעין שאינן למגורים',
        taxpayer: { code: '150', resultKey: '_non_residential_rent_tp', inputKey: 'non_residential_rent_taxpayer' },
        spouse: { code: '301', resultKey: '_non_residential_rent_sp', inputKey: 'non_residential_rent_spouse' },
      },
      {
        num: 11, description: 'תמורות / הכנסות אחרות מנכסי מקרקעין',
        taxpayer: { code: '367', resultKey: '_property_other_tp', inputKey: 'property_other_income_taxpayer' },
        spouse: { code: '202', resultKey: '_property_other_sp', inputKey: 'property_other_income_spouse' },
      },
      {
        num: 12, description: 'הכנסות אחרות — משותף',
        taxpayer: { code: '167', resultKey: 'other_income.field_167', inputKey: 'other_income_joint' },
      },
      {
        num: 13, description: 'הכנסות אחרות',
        taxpayer: { code: '305', resultKey: 'other_income.field_305', inputKey: 'other_income_taxpayer' },
        spouse: { code: '205', resultKey: 'other_income.field_205', inputKey: 'other_income_spouse' },
      },
    ],
  },
  // ===== ה — הכנסות חייבות בשיעורי מס מיוחדים =====
  {
    partId: 'ה',
    title: 'ה. הכנסות חייבות בשיעורי מס מיוחדים',
    rows: [
      {
        num: 10, description: 'ריבית ניירות ערך, דיבידנד מפעל מאושר — 15%',
        taxpayer: { code: '060', resultKey: 'special_rate.field_060', inputKey: 'interest_securities_15_taxpayer' },
        spouse: { code: '211', resultKey: 'special_rate.field_211', inputKey: 'interest_securities_15_spouse' },
      },
      {
        num: 11, description: 'ריבית ניירות ערך, קופות גמל — 20%',
        taxpayer: { code: '067', resultKey: 'special_rate.field_067', inputKey: 'interest_securities_20_taxpayer' },
        spouse: { code: '228', resultKey: 'special_rate.field_228', inputKey: 'interest_securities_20_spouse' },
      },
      {
        num: 12, description: 'ריבית ניירות ערך, קופות גמל — 25%',
        taxpayer: { code: '157', resultKey: 'special_rate.field_157', inputKey: 'interest_securities_25_taxpayer' },
        spouse: { code: '257', resultKey: 'special_rate.field_257', inputKey: 'interest_securities_25_spouse' },
      },
      {
        num: 13, description: 'דיבידנד מפעל מועדף/מאושר — 20%',
        taxpayer: { code: '173', resultKey: 'special_rate.field_173', inputKey: 'dividend_preferred_20_taxpayer' },
        spouse: { code: '275', resultKey: 'special_rate.field_275', inputKey: 'dividend_preferred_20_spouse' },
      },
      {
        num: 14, description: 'דיבידנד — 25%',
        taxpayer: { code: '141', resultKey: 'special_rate.field_141', inputKey: 'dividend_25_taxpayer' },
        spouse: { code: '241', resultKey: 'special_rate.field_241', inputKey: 'dividend_25_spouse' },
      },
      {
        num: 15, description: 'דיבידנד בעל מניות מהותי — 30%',
        taxpayer: { code: '055', resultKey: 'special_rate.field_055', inputKey: 'dividend_significant_30_taxpayer' },
        spouse: { code: '212', resultKey: 'special_rate.field_212', inputKey: 'dividend_significant_30_spouse' },
      },
      {
        num: 16, description: 'ריבית על פיקדונות/חסכונות — 15%',
        taxpayer: { code: '078', resultKey: 'special_rate.field_078', inputKey: 'interest_deposits_15_taxpayer' },
        spouse: { code: '217', resultKey: 'special_rate.field_217', inputKey: 'interest_deposits_15_spouse' },
      },
      {
        num: 17, description: 'ריבית על פיקדונות/חסכונות — 20%',
        taxpayer: { code: '126', resultKey: 'special_rate.field_126', inputKey: 'interest_deposits_20_taxpayer' },
        spouse: { code: '226', resultKey: 'special_rate.field_226', inputKey: 'interest_deposits_20_spouse' },
      },
      {
        num: 18, description: 'ריבית על פיקדונות/חסכונות — 25%',
        taxpayer: { code: '142', resultKey: 'special_rate.field_142', inputKey: 'interest_deposits_25_taxpayer' },
        spouse: { code: '242', resultKey: 'special_rate.field_242', inputKey: 'interest_deposits_25_spouse' },
      },
      {
        num: 19, description: 'הכנסת שכר דירה למגורים — 10%',
        taxpayer: { code: '222', resultKey: 'special_rate.field_222', inputKey: 'rental_10_taxpayer' },
        spouse: { code: '284', resultKey: 'special_rate.field_284', inputKey: 'rental_10_spouse' },
      },
      {
        num: 20, description: 'שכר דירה מחוץ לארץ — 15%',
        taxpayer: { code: '225', resultKey: 'special_rate.field_225', inputKey: 'rental_abroad_15_taxpayer' },
        spouse: { code: '285', resultKey: 'special_rate.field_285', inputKey: 'rental_abroad_15_spouse' },
      },
      {
        num: 21, description: 'הימורים, הגרלות, פרסים — 35%',
        taxpayer: { code: '227', resultKey: 'special_rate.field_227', inputKey: 'gambling_35_taxpayer' },
        spouse: { code: '286', resultKey: 'special_rate.field_286', inputKey: 'gambling_35_spouse' },
      },
      {
        num: 22, description: 'הכנסות מאנרגיות מתחדשות — 31%',
        taxpayer: { code: '335', resultKey: 'special_rate.field_335', inputKey: 'renewable_energy_31_taxpayer' },
        spouse: { code: '337', resultKey: 'special_rate.field_337', inputKey: 'renewable_energy_31_spouse' },
      },
      {
        num: 23, description: 'חלוקה מחיסכון פנסיוני — 20%',
        taxpayer: { code: '288', resultKey: 'special_rate.field_288', inputKey: 'pension_distribution_20_taxpayer' },
        spouse: { code: '338', resultKey: 'special_rate.field_338', inputKey: 'pension_distribution_20_spouse' },
      },
      {
        num: 24, description: 'משיכה שלא כדין מקופת גמל — 35%',
        taxpayer: { code: '213', resultKey: 'special_rate.field_213', inputKey: 'unauthorized_withdrawal_35_taxpayer' },
        spouse: { code: '313', resultKey: 'special_rate.field_313', inputKey: 'unauthorized_withdrawal_35_spouse' },
      },
    ],
  },
  // ===== ח — רווחי הון =====
  {
    partId: 'ח',
    title: 'ח. רווחי הון',
    rows: [
      {
        num: 25, description: 'רווח הון ריאלי — מניות, RSU, ESPP',
        taxpayer: { code: '139', resultKey: 'capital_gains.field_139', inputKey: 'capital_gains' },
      },
      {
        num: 26, description: 'רווח הון — מטבעות דיגיטליים (קריפטו)',
        taxpayer: { code: '139', resultKey: '_crypto', inputKey: 'crypto_income' },
      },
      {
        num: 32,
        description: 'הפסד הון להעברה לשנים הבאות',
        notes: ['לאחר התאמת הסכום המופיע בשדה 150/170 או בשומות קודמות'],
        taxpayer: { code: '032', resultKey: '_capital_loss_tp', inputKey: 'capital_loss_carryforward_taxpayer' },
        spouse: { code: '163', resultKey: '_capital_loss_sp', inputKey: 'capital_loss_carryforward_spouse' },
      },
    ],
  },
  // ===== י — הכנסות פטורות =====
  {
    partId: 'י',
    title: 'י. הכנסות פטורות ממס',
    rows: [
      {
        num: 27, description: 'פטור נכות — סעיף 9(5)',
        taxpayer: { code: '109', resultKey: 'exempt.field_109', inputKey: 'exempt_disability_taxpayer' },
        spouse: { code: '309', resultKey: 'exempt.field_309', inputKey: 'exempt_disability_spouse' },
      },
      {
        num: 28, description: 'שכר דירה פטור ממס',
        taxpayer: { code: '332', resultKey: 'exempt.field_332', inputKey: 'exempt_rental_income' },
      },
      {
        num: 33,
        description: 'הכנסה פטורה ממכירת נכס / קצבה פטורה',
        taxpayer: { code: '184', resultKey: '_exempt_misc_tp', inputKey: 'exempt_misc_taxpayer' },
        spouse: { code: '185', resultKey: '_exempt_misc_sp', inputKey: 'exempt_misc_spouse' },
      },
      {
        num: 34,
        description: 'רווחים / הכנסות פטורות מעסק או משלח יד',
        taxpayer: { code: '186', resultKey: '_exempt_business_tp', inputKey: 'exempt_business_taxpayer' },
        spouse: { code: '187', resultKey: '_exempt_business_sp', inputKey: 'exempt_business_spouse' },
      },
      {
        num: 35,
        description: 'הכנסה פטורה אחרת',
        taxpayer: { code: '238', resultKey: '_exempt_other_tp', inputKey: 'exempt_other_taxpayer' },
        spouse: { code: '239', resultKey: '_exempt_other_sp', inputKey: 'exempt_other_spouse' },
      },
    ],
  },
  {
    partId: 'יא',
    title: 'יא. הכנסות חו"ל והכנסות מיוחדות',
    rows: [
      {
        num: 36,
        description: 'מס רווח הון / שבח שנפרס',
        taxpayer: { code: '054', resultKey: '_foreign_spread_gain', inputKey: 'spread_gain_taxpayer' },
      },
      {
        num: 37,
        description: 'סכום הכנסות פטורות ממקור חוץ',
        taxpayer: { code: '056', resultKey: '_foreign_exempt_income', inputKey: 'foreign_exempt_income_taxpayer' },
      },
      {
        num: 38,
        description: 'סכום מס הכנסה מחו"ל / מס שנוכה בחו"ל',
        taxpayer: { code: '256', resultKey: '_foreign_tax_paid', inputKey: 'foreign_tax_paid_taxpayer' },
      },
      {
        num: 39,
        description: 'סך הכנסות חו"ל נוספות',
        taxpayer: { code: '290', resultKey: '_foreign_income_total', inputKey: 'foreign_income_total_taxpayer' },
      },
    ],
  },
  // ===== יב — ניכויים אישיים =====
  {
    partId: 'יב',
    title: 'יב. ניכויים אישיים',
    rows: [
      {
        num: 29, description: 'ביטוח אבדן כושר עבודה — עצמאי',
        taxpayer: { code: '112', resultKey: 'deductions.field_112', inputKey: 'disability_insurance_self_taxpayer' },
        spouse: { code: '113', resultKey: 'deductions.field_113', inputKey: 'disability_insurance_self_spouse' },
      },
      {
        num: 30, description: 'ביטוח אבדן כושר עבודה — שכיר',
        taxpayer: { code: '206', resultKey: 'deductions.field_206', inputKey: 'disability_insurance_employee_taxpayer' },
        spouse: { code: '207', resultKey: 'deductions.field_207', inputKey: 'disability_insurance_employee_spouse' },
      },
      {
        num: 31, description: 'קרן השתלמות — עצמאי',
        taxpayer: { code: '136', resultKey: 'deductions.field_136', inputKey: 'education_fund_self_taxpayer' },
        spouse: { code: '137', resultKey: 'deductions.field_137', inputKey: 'education_fund_self_spouse' },
      },
      {
        num: 32, description: 'משכורת לקרן השתלמות — שכיר',
        taxpayer: { code: '218', resultKey: 'deductions.field_218' },
        spouse: { code: '219', resultKey: 'deductions.field_219' },
      },
      {
        num: 33, description: 'הפקדה לקופת גמל — עמית עצמאי',
        taxpayer: { code: '135', resultKey: 'deductions.field_135', inputKey: 'pension_self_taxpayer' },
        spouse: { code: '180', resultKey: 'deductions.field_180', inputKey: 'pension_self_spouse' },
      },
      {
        num: 34, description: 'ביטוח לאומי על הכנסה שאינה מעבודה',
        taxpayer: { code: '030', resultKey: 'deductions.field_030', inputKey: 'nii_non_employment_taxpayer' },
        spouse: { code: '089', resultKey: 'deductions.field_089', inputKey: 'nii_non_employment_spouse' },
      },
      {
        num: 35, description: 'הכנסה מבוטחת',
        taxpayer: { code: '244', resultKey: 'deductions.field_244' },
        spouse: { code: '245', resultKey: 'deductions.field_245' },
      },
      {
        num: 36, description: 'הפקדות מעביד לקופות גמל',
        taxpayer: { code: '248', resultKey: 'deductions.field_248' },
        spouse: { code: '249', resultKey: 'deductions.field_249' },
      },
      {
        num: 37, description: 'הפחתת דמי הבראה',
        taxpayer: { code: '011', resultKey: 'deductions.field_011' },
        spouse: { code: '012', resultKey: 'deductions.field_012' },
      },
    ],
  },
  // ===== יג — נקודות זיכוי =====
  {
    partId: 'יג',
    title: 'יג. נקודות זיכוי',
    rows: [
      {
        num: 38, description: 'נקודות זיכוי',
        taxpayer: { code: '020', resultKey: 'credit_points.credit_points_taxpayer', inputKey: 'credit_points_taxpayer', placeholder: 'אוטו׳ 2.25', step: '0.25' },
        spouse: { code: '021', resultKey: 'credit_points.credit_points_spouse', inputKey: 'credit_points_spouse', placeholder: 'אוטו׳ 2.75', step: '0.25' },
      },
      {
        num: 39, description: 'נקודות זיכוי בגין ילדים',
        taxpayer: { code: '260', resultKey: 'credit_points.field_260', inputKey: 'children_credit_points_taxpayer', step: '0.5' },
        spouse: { code: '262', resultKey: 'credit_points.field_262', inputKey: 'children_credit_points_spouse', step: '0.5' },
      },
      {
        num: 40, description: 'הורה חד-הורי',
        taxpayer: { code: '026', resultKey: 'credit_points.field_026', inputKey: 'single_parent_points', step: '0.5' },
      },
    ],
  },
  // ===== יד — זיכויים מהמס =====
  {
    partId: 'יד',
    title: 'יד. זיכויים מהמס',
    rows: [
      {
        num: 41, description: 'ביטוח חיים — זיכוי 25%',
        taxpayer: { code: '036', resultKey: 'tax_credits.field_036', inputKey: 'life_insurance_taxpayer' },
        spouse: { code: '081', resultKey: 'tax_credits.field_081', inputKey: 'life_insurance_spouse' },
      },
      {
        num: 42, description: 'ביטוח קצבת שאירים',
        taxpayer: { code: '140', resultKey: 'tax_credits.field_140', inputKey: 'survivors_insurance_taxpayer' },
        spouse: { code: '240', resultKey: 'tax_credits.field_240', inputKey: 'survivors_insurance_spouse' },
      },
      {
        num: 43, description: 'הפרשות עובד לפנסיה — זיכוי 35%',
        taxpayer: { code: '045', resultKey: 'tax_credits.field_045' },
        spouse: { code: '086', resultKey: 'tax_credits.field_086' },
      },
      {
        num: 44, description: 'קצבה כעמית עצמאי',
        taxpayer: { code: '268', resultKey: 'tax_credits.field_268', inputKey: 'pension_self_credit_taxpayer' },
        spouse: { code: '269', resultKey: 'tax_credits.field_269', inputKey: 'pension_self_credit_spouse' },
      },
      {
        num: 45, description: 'החזקת בן משפחה במוסד',
        taxpayer: { code: '132', resultKey: 'tax_credits.field_132', inputKey: 'institution_care_taxpayer' },
        spouse: { code: '232', resultKey: 'tax_credits.field_232', inputKey: 'institution_care_spouse' },
      },
      {
        num: 46, description: 'תרומות למוסדות מוכרים — 35%',
        taxpayer: { code: '037', resultKey: 'tax_credits.field_037', inputKey: 'donation_taxpayer' },
        spouse: { code: '237', resultKey: 'tax_credits.field_237', inputKey: 'donation_spouse' },
      },
      {
        num: 47, description: 'תרומות למוסדות מוכרים — ארה"ב',
        taxpayer: { code: '046', resultKey: 'tax_credits.field_046', inputKey: 'donation_us_taxpayer' },
        spouse: { code: '048', resultKey: 'tax_credits.field_048', inputKey: 'donation_us_spouse' },
      },
      {
        num: 48, description: 'השקעות במחקר ופיתוח',
        taxpayer: { code: '155', resultKey: 'tax_credits.field_155', inputKey: 'rnd_investment_taxpayer' },
        spouse: { code: '199', resultKey: 'tax_credits.field_199', inputKey: 'rnd_investment_spouse' },
      },
      {
        num: 49, description: 'תושב אילת/אזור פיתוח',
        taxpayer: { code: '183', resultKey: 'tax_credits.field_183', inputKey: 'eilat_income_taxpayer' },
      },
    ],
  },
  // ===== טו — ניכויים במקור ותשלומים =====
  {
    partId: 'טו',
    title: 'טו. ניכויים במקור ותשלומים',
    rows: [
      {
        num: 50, description: 'מס שנוכה ממשכורת',
        taxpayer: { code: '042', resultKey: 'withholdings.field_042' },
      },
      {
        num: 51, description: 'ניכוי במקור — ריבית ודיבידנד',
        taxpayer: { code: '043', resultKey: 'withholdings.field_043' },
      },
      {
        num: 52, description: 'ניכוי מס מהכנסות אחרות',
        taxpayer: { code: '040', resultKey: 'withholdings.field_040', inputKey: 'withholding_other' },
      },
      {
        num: 53, description: 'מס שבח',
        taxpayer: { code: '041', resultKey: 'withholdings.field_041', inputKey: 'land_appreciation_tax' },
      },
      {
        num: 54, description: 'מס שכירות ששולם',
        taxpayer: { code: '220', resultKey: 'withholdings.field_220', inputKey: 'rental_tax_paid' },
      },
      {
        num: 55, description: 'מקדמות מדוח שנתי',
        taxpayer: { code: '---', resultKey: 'withholdings.field_tax_advance' },
      },
    ],
  },
  // ===== נתונים נוספים =====
  {
    partId: 'נוסף',
    title: 'נתונים נוספים',
    rows: [
      {
        num: 56, description: 'הוצאות הפקת הכנסה',
        taxpayer: { code: '034', resultKey: '_production_tp', inputKey: 'production_expenses_taxpayer', placeholder: 'למשל 1,170' },
        spouse: { code: '034', resultKey: '_production_sp', inputKey: 'production_expenses_spouse' },
      },
      {
        num: 57, description: 'הפרשי הצמדה וריבית',
        taxpayer: { code: '---', resultKey: '_cpi', inputKey: 'interest_cpi_adjustment', placeholder: 'מתוך השומה' },
      },
    ],
  },
]

// --- helpers ---

function getFieldValue(result: Form1301Result, path: string): number {
  if (path.startsWith('_')) return 0
  const parts = path.split('.')
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = result
  for (const p of parts) {
    obj = obj?.[p]
  }
  return typeof obj === 'number' ? obj : 0
}

function getCheckedGroupValues(form: Record<string, string>, key: string): string[] {
  const rawValue = form[key]
  if (!rawValue) return []
  return rawValue.split('|').filter(Boolean)
}

function hasIdSupplementValue(doc: DocumentInfo | undefined, field: string): boolean {
  return Boolean(doc?.extracted?.[field]?.value)
}

function countExtractedValues(doc: DocumentInfo): number {
  return Object.values(doc.extracted || {}).reduce((count, field) => {
    return field?.value === null || field?.value === '' ? count : count + 1
  }, 0)
}

function pickPreferredDocument(documents: DocumentInfo[], documentType: string): DocumentInfo | undefined {
  return documents
    .filter((doc) => doc.document_type === documentType)
    .sort((left, right) => {
      if (left.user_corrected !== right.user_corrected) {
        return left.user_corrected ? -1 : 1
      }
      return countExtractedValues(right) - countExtractedValues(left)
    })[0]
}

function normalizeSupplementDate(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed
  const dotMatch = trimmed.match(/^(\d{2})\.(\d{2})\.(\d{4})$/)
  if (dotMatch) {
    return `${dotMatch[3]}-${dotMatch[2]}-${dotMatch[1]}`
  }
  const slashMatch = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (slashMatch) {
    return `${slashMatch[3]}-${slashMatch[2]}-${slashMatch[1]}`
  }
  return ''
}

function isNumericFieldCode(code: string): boolean {
  return /^\d+$/.test(code)
}

function buildFieldAssistantQuestion(row: GeneralRow): string {
  return `הסבר לי בפשטות מה המשמעות של השדה "${row.label}", מתי בדרך כלל מסמנים כן או לא, ומה כדאי לבדוק לפני שממלאים אותו.`
}

function getDraftStorageKey(taxYear: number): string {
  return `form1301-draft-${taxYear}`
}

function buildAdvisorItems(params: {
  documents: DocumentInfo[]
  result: Form1301Result | null
  maritalStatus: string
  inputs: Record<string, string>
}): AdvisorItem[] {
  const { documents, result, maritalStatus, inputs } = params
  const items: AdvisorItem[] = []
  const docTypes = new Set(documents.map((doc) => doc.document_type))
  const preferredIdSupplement = pickPreferredDocument(documents, 'id_supplement')
  const hasSpouseContext = maritalStatus === 'נשוי' || Boolean(preferredIdSupplement?.extracted?.spouse_id?.value)

  if (documents.length === 0) {
    items.push({
      id: 'missing-all-docs',
      title: 'לא הועלו מסמכים לשנת המס',
      detail: 'כדאי להעלות לפחות טופס 106, ספח תעודת זהות ומסמכי השקעות או שכירות אם קיימים, כדי לצמצם הזנה ידנית ושגיאות.',
      level: 'missing',
    })
    return items
  }

  if (!docTypes.has('id_supplement')) {
    items.push({
      id: 'missing-id-supplement',
      title: 'חסר ספח תעודת זהות',
      detail: 'בלי הספח קשה להשלים אוטומטית בן או בת זוג, ילדים ונקודות זיכוי משפחתיות.',
      level: 'missing',
    })
  }

  if (!docTypes.has('form_106')) {
    items.push({
      id: 'missing-106',
      title: 'לא נמצא טופס 106',
      detail: 'אם הייתה הכנסה ממשכורת, זה בדרך כלל המסמך הראשון שצריך להעלות כדי לאכלס שכר, מס שנוכה, פנסיה ותרומות.',
      level: 'missing',
    })
  }

  if (hasSpouseContext && documents.filter((doc) => doc.document_type === 'form_106').length === 1) {
    items.push({
      id: 'check-spouse-106',
      title: 'נמצא רק טופס 106 אחד במשק בית זוגי',
      detail: 'אם גם לבן או לבת הזוג הייתה משכורת, כדאי להעלות גם את טופס 106 שלהם כדי להימנע מייחוס חלקי של הכנסות.',
      level: 'warn',
    })
  }

  if ((result?.special_rate.field_222 ?? 0) > 0 && !docTypes.has('rental_excel') && !docTypes.has('rental_payment')) {
    items.push({
      id: 'check-rent-docs',
      title: 'יש הכנסות משכירות במסלול 10% בלי מסמכי גיבוי',
      detail: 'כדאי להעלות קובץ שכירות או אישורי תשלום מס כדי לאמת את סכום ההכנסה ואת המס שכבר שולם.',
      level: 'warn',
    })
  }

  if (((result?.special_rate.field_141 ?? 0) > 0 || (result?.special_rate.field_142 ?? 0) > 0) && !docTypes.has('form_867') && !docTypes.has('annual_summary')) {
    items.push({
      id: 'missing-investment-docs',
      title: 'יש הכנסות הון ללא מסמך השקעות תומך',
      detail: 'כשיש דיבידנד או ריבית, רצוי להעלות טופס 867 או דוח שנתי מתאים כדי לאמת את ההכנסה והניכוי במקור.',
      level: 'missing',
    })
  }

  if ((Number(inputs.production_expenses_taxpayer || '0') > 0 || Number(inputs.production_expenses_spouse || '0') > 0) && !docTypes.has('receipt')) {
    items.push({
      id: 'missing-receipts',
      title: 'הוזנו הוצאות הפקת הכנסה ללא קבלות',
      detail: 'אם אתה מסתמך על שכ"ט רו"ח או הוצאות אחרות, כדאי להעלות קבלות כדי לשמור תיעוד תומך.',
      level: 'warn',
    })
  }

  if ((result?.credit_points.field_260 ?? 0) > 0 || (result?.credit_points.field_262 ?? 0) > 0) {
    items.push({
      id: 'children-points-check',
      title: 'נקודות זיכוי ילדים חושבו אוטומטית',
      detail: 'כדאי לעבור על שיוך הילדים בין בני הזוג ולוודא שהוא תואם לשומה בפועל, במיוחד בשנים עם שינויי חקיקה.',
      level: 'info',
    })
  }

  for (const [index, warning] of (result?.warnings ?? []).entries()) {
    items.push({
      id: `warning-${index}`,
      title: 'נדרשת בדיקה ידנית',
      detail: warning,
      level: 'warn',
    })
  }

  if (items.length === 0) {
    items.push({
      id: 'all-good',
      title: 'לא נמצאו כרגע פערי מסמכים ברורים',
      detail: 'החישוב מבוסס על המסמכים והנתונים הקיימים. עדיין מומלץ להשוות מול השומה או הדוח שהוגש בפועל.',
      level: 'info',
    })
  }

  return items
}

// --- component ---

export function Form1301Page() {
  const { taxYear } = useTaxYear()
  const [activeTab, setActiveTab] = useState<FormTab>('income')
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Form1301PreviewResponse | null>(null)
  const [error, setError] = useState('')
  const [tabValidationErrors, setTabValidationErrors] = useState<string[]>([])
  const [autoFilled, setAutoFilled] = useState<Set<string>>(new Set())
  const [fieldHelp, setFieldHelp] = useState<FieldHelpResponse | null>(null)
  const [fieldHelpOpen, setFieldHelpOpen] = useState(false)
  const [fieldHelpLoading, setFieldHelpLoading] = useState(false)
  const [draftStatus, setDraftStatus] = useState<'idle' | 'saved' | 'restored' | 'error'>('idle')
  const [draftSavedAt, setDraftSavedAt] = useState('')
  const resultRef = useRef<HTMLDivElement>(null)
  const chatRef = useRef<FloatingChatHandle>(null)
  const [personalForm, setPersonalForm] = useState<Record<string, string>>({})
  const [generalForm, setGeneralForm] = useState<Record<string, string>>({})

  const BLANK_INPUTS: Record<string, string> = useMemo(() => ({
    // ג
    business_income_taxpayer: '', business_income_spouse: '',
    nii_self_employed_taxpayer: '', nii_self_employed_spouse: '',
    nii_employee_taxpayer: '', nii_employee_spouse: '',
    shift_work_taxpayer: '', shift_work_spouse: '',
    retirement_grants_taxpayer: '', retirement_grants_spouse: '',
    unemployment_benefits_taxpayer: '', unemployment_benefits_spouse: '',
    other_personal_income_taxpayer: '', other_personal_income_spouse: '',
    // ד
    real_estate_income_taxpayer: '', real_estate_income_spouse: '',
    non_residential_rent_taxpayer: '', non_residential_rent_spouse: '',
    property_other_income_taxpayer: '', property_other_income_spouse: '',
    other_income_taxpayer: '', other_income_spouse: '', other_income_joint: '',
    // ה
    interest_securities_15_taxpayer: '', interest_securities_15_spouse: '',
    interest_securities_20_taxpayer: '', interest_securities_20_spouse: '',
    interest_securities_25_taxpayer: '', interest_securities_25_spouse: '',
    dividend_preferred_20_taxpayer: '', dividend_preferred_20_spouse: '',
    dividend_25_taxpayer: '', dividend_25_spouse: '',
    dividend_significant_30_taxpayer: '', dividend_significant_30_spouse: '',
    interest_deposits_15_taxpayer: '', interest_deposits_15_spouse: '',
    interest_deposits_20_taxpayer: '', interest_deposits_20_spouse: '',
    interest_deposits_25_taxpayer: '', interest_deposits_25_spouse: '',
    rental_10_taxpayer: '', rental_10_spouse: '',
    rental_abroad_15_taxpayer: '', rental_abroad_15_spouse: '',
    gambling_35_taxpayer: '', gambling_35_spouse: '',
    renewable_energy_31_taxpayer: '', renewable_energy_31_spouse: '',
    pension_distribution_20_taxpayer: '', pension_distribution_20_spouse: '',
    unauthorized_withdrawal_35_taxpayer: '', unauthorized_withdrawal_35_spouse: '',
    // ח
    capital_gains: '', crypto_income: '',
    capital_loss_carryforward_taxpayer: '', capital_loss_carryforward_spouse: '',
    // י
    exempt_rental_income: '', exempt_disability_taxpayer: '', exempt_disability_spouse: '',
    exempt_misc_taxpayer: '', exempt_misc_spouse: '',
    exempt_business_taxpayer: '', exempt_business_spouse: '',
    exempt_other_taxpayer: '', exempt_other_spouse: '',
    spread_gain_taxpayer: '', foreign_exempt_income_taxpayer: '', foreign_tax_paid_taxpayer: '', foreign_income_total_taxpayer: '',
    // יב
    disability_insurance_self_taxpayer: '', disability_insurance_self_spouse: '',
    disability_insurance_employee_taxpayer: '', disability_insurance_employee_spouse: '',
    education_fund_self_taxpayer: '', education_fund_self_spouse: '',
    pension_self_taxpayer: '', pension_self_spouse: '',
    nii_non_employment_taxpayer: '', nii_non_employment_spouse: '',
    // יג
    credit_points_taxpayer: '', credit_points_spouse: '',
    children_credit_points_taxpayer: '', children_credit_points_spouse: '',
    single_parent_points: '',
    // יד
    life_insurance_taxpayer: '', life_insurance_spouse: '',
    survivors_insurance_taxpayer: '', survivors_insurance_spouse: '',
    pension_self_credit_taxpayer: '', pension_self_credit_spouse: '',
    institution_care_taxpayer: '', institution_care_spouse: '',
    donation_taxpayer: '', donation_spouse: '',
    donation_us_taxpayer: '', donation_us_spouse: '',
    rnd_investment_taxpayer: '', rnd_investment_spouse: '',
    eilat_income_taxpayer: '',
    // טו
    rental_tax_paid: '', withholding_other: '', land_appreciation_tax: '',
    // נוסף
    production_expenses_taxpayer: '', production_expenses_spouse: '',
    interest_cpi_adjustment: '',
  }), [])

  const [inputs, setInputs] = useState<Record<string, string>>(() => ({ ...BLANK_INPUTS }))

  const loadDocuments = useCallback(async () => {
    try {
      const data = await api<DocumentListResponse>('/documents')
      setDocuments(data.documents)
    } catch {
      // ignore
    }
  }, [])

  const saveDraft = useCallback(() => {
    try {
      const savedAt = new Date().toISOString()
      const draft: SavedDraft = {
        activeTab,
        personalForm,
        generalForm,
        inputs,
        savedAt,
        draftVersion: DRAFT_VERSION,
      }
      window.localStorage.setItem(getDraftStorageKey(taxYear), JSON.stringify(draft))
      setDraftStatus('saved')
      setDraftSavedAt(savedAt)
    } catch {
      setDraftStatus('error')
    }
  }, [activeTab, generalForm, inputs, personalForm, taxYear])

  useEffect(() => {
    void loadDocuments()
    setResult(null)
  }, [loadDocuments, taxYear])

  useEffect(() => {
    // Reset all form state when year changes — prevent cross-year contamination
    setInputs({ ...BLANK_INPUTS })
    setPersonalForm({})
    setGeneralForm({})
    setAutoFilled(new Set())
    setResult(null)
    setError('')

    try {
      const rawDraft = window.localStorage.getItem(getDraftStorageKey(taxYear))
      if (!rawDraft) {
        setDraftStatus('idle')
        setDraftSavedAt('')
        return
      }
      const draft = JSON.parse(rawDraft) as Partial<SavedDraft>
      if (draft.draftVersion !== DRAFT_VERSION) {
        // Discard drafts from before the year-isolation fix
        window.localStorage.removeItem(getDraftStorageKey(taxYear))
        setDraftStatus('idle')
        setDraftSavedAt('')
        return
      }
      if (draft.activeTab === 'personal' || draft.activeTab === 'general' || draft.activeTab === 'income') {
        setActiveTab(draft.activeTab)
      }
      if (draft.personalForm && typeof draft.personalForm === 'object') {
        setPersonalForm(draft.personalForm)
      }
      if (draft.generalForm && typeof draft.generalForm === 'object') {
        setGeneralForm(draft.generalForm)
      }
      if (draft.inputs && typeof draft.inputs === 'object') {
        setInputs({ ...BLANK_INPUTS, ...draft.inputs })
      }
      setDraftStatus('restored')
      setDraftSavedAt(typeof draft.savedAt === 'string' ? draft.savedAt : '')
    } catch {
      setDraftStatus('error')
    }
  }, [taxYear, BLANK_INPUTS])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      saveDraft()
    }, 400)

    return () => window.clearTimeout(timeoutId)
  }, [saveDraft])

  useEffect(() => {
    const handleVisibilityRefresh = () => {
      if (document.visibilityState === 'visible') {
        void loadDocuments()
      }
    }

    const handleFocusRefresh = () => {
      void loadDocuments()
    }

    window.addEventListener('focus', handleFocusRefresh)
    document.addEventListener('visibilitychange', handleVisibilityRefresh)

    return () => {
      window.removeEventListener('focus', handleFocusRefresh)
      document.removeEventListener('visibilitychange', handleVisibilityRefresh)
    }
  }, [loadDocuments])

  const handleInputChange = (field: string, value: string) => {
    setInputs((prev) => ({ ...prev, [field]: value }))
    setAutoFilled((prev) => {
      if (prev.has(field)) {
        const next = new Set(prev)
        next.delete(field)
        return next
      }
      return prev
    })
  }

  const openFieldHelp = useCallback(async (code: string) => {
    if (!code || code === '---') return
    setFieldHelpLoading(true)
    setFieldHelpOpen(true)
    try {
      const data = await api<FieldHelpResponse>(`/form-1301/field-help/${code}`)
      setFieldHelp(data)
    } catch {
      setFieldHelp({
        code,
        title: `שדה ${code}`,
        description: 'עדיין אין הסבר זמין לשדה זה.',
        part_id: '',
        part_name_he: '',
        section_num: null,
        section_name_he: '',
        guide_line: null,
        tax_rate: '',
        notes: [],
      })
    } finally {
      setFieldHelpLoading(false)
    }
  }, [])

  const maritalStatus = personalForm.marital_status ?? ''
  const taxpayerGender = personalForm.taxpayer_gender ?? ''
  const hasJointIncomeSource = generalForm['331'] === 'yes'
  const spouseAssistsIncome = generalForm['spouse_report_mode'] === 'yes' && generalForm['spouse_report_mode_detail'] === 'assisted_income'
  const taxpayerImmigrantStatus = generalForm['273'] ?? ''
  const taxpayerImmigrantArrivalDate = generalForm['273_date'] ?? ''
  const spouseImmigrantStatus = generalForm['274'] ?? ''
  const spouseImmigrantArrivalDate = generalForm['274_date'] ?? ''

  const handleCalculate = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ year: String(taxYear) })
      if (maritalStatus) {
        params.set('marital_status', maritalStatus)
      }
      if (taxpayerGender) params.set('taxpayer_gender', taxpayerGender)
      if (hasJointIncomeSource) params.set('has_joint_income_source', 'true')
      if (spouseAssistsIncome) params.set('spouse_assists_income', 'true')
      if (taxpayerImmigrantStatus) params.set('immigrant_taxpayer_status', taxpayerImmigrantStatus)
      if (taxpayerImmigrantArrivalDate) params.set('immigrant_taxpayer_arrival_date', taxpayerImmigrantArrivalDate)
      if (spouseImmigrantStatus) params.set('immigrant_spouse_status', spouseImmigrantStatus)
      if (spouseImmigrantArrivalDate) params.set('immigrant_spouse_arrival_date', spouseImmigrantArrivalDate)
      for (const [key, val] of Object.entries(inputs)) {
        if (val) params.set(key, val)
      }
      const data = await api<Form1301PreviewResponse>(`/form-1301/preview?${params}`)
      setResult(data)
      const eff = data.result.effective_inputs
      const filled = new Set<string>()
      setInputs((prev) => {
        const updated = { ...prev }
        // Clear previously auto-filled fields that are no longer effective
        for (const key of autoFilled) {
          if (!eff || !(key in eff)) {
            updated[key] = ''
          }
        }
        // Apply new effective inputs
        if (eff) {
          for (const [field, val] of Object.entries(eff)) {
            if (!updated[field] || updated[field] === '') {
              updated[field] = String(val)
              filled.add(field)
            }
          }
        }
        return updated
      })
      setAutoFilled(filled)
      // Auto-fill personal form from detected document data (only if not already set by user)
      if (eff) {
        setPersonalForm((prev) => {
          const updated = { ...prev }
          if (!updated.taxpayer_gender && eff.detected_gender) {
            updated.taxpayer_gender = String(eff.detected_gender)
          }
          return updated
        })
      }
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'שגיאה בחישוב')
    } finally {
      setLoading(false)
    }
  }, [taxYear, inputs, maritalStatus, taxpayerGender, hasJointIncomeSource, spouseAssistsIncome, taxpayerImmigrantStatus, taxpayerImmigrantArrivalDate, spouseImmigrantStatus, spouseImmigrantArrivalDate])

  const yearDocs = documents.filter((d) => {
    const docYear = d.extracted?.tax_year?.value
    return !docYear || Number(docYear) === taxYear
  })

  const docsByType = yearDocs.reduce<Record<string, DocumentInfo[]>>((acc, doc) => {
    const type = doc.document_type || 'form_106'
    if (!acc[type]) acc[type] = []
    acc[type].push(doc)
    return acc
  }, {})

  const r = result?.result
  const advisorItems = buildAdvisorItems({
    documents: yearDocs,
    result: r ?? null,
    maritalStatus,
    inputs,
  })
  const idSupplement = pickPreferredDocument(yearDocs, 'id_supplement')
  const interestAdj = r?.calculation.interest_cpi_adjustment ?? 0
  const balance = interestAdj !== 0
    ? (r?.calculation.balance_after_interest ?? 0)
    : (r?.calculation.balance ?? 0)

  // Build field code → Hebrew label map for the chat context
  const fieldLabels = useMemo(() => {
    const labels: Record<string, string> = {}
    for (const section of GENERAL_INFO_SECTIONS) {
      for (const row of section.rows) {
        labels[row.code] = row.label
      }
    }
    for (const section of IRS_SECTIONS) {
      for (const row of section.rows) {
        if (row.taxpayer) labels[row.taxpayer.inputKey ?? row.taxpayer.code] = row.description
        if (row.spouse) labels[row.spouse.inputKey ?? row.spouse.code] = row.description + ' — בן/ת זוג'
      }
    }
    return labels
  }, [])

  const chatSnapshot: FormSnapshot = {
    taxYear,
    activeTab,
    personalForm,
    generalForm,
    inputs,
    sourceDocuments: r?.source_documents ?? yearDocs.map((d) => d.original_filename),
    warnings: r?.warnings ?? [],
    balance,
    netTax: r?.calculation.net_tax ?? 0,
    fieldLabels,
  }

  const renderCell = (cell: CellDef) => {
    if (cell.inputKey) {
      return (
        <input
          type="number"
          className={cn(
            'w-full h-7 px-1.5 text-sm border rounded-sm text-left tabular-nums',
            autoFilled.has(cell.inputKey)
              ? 'bg-green-50 border-green-400'
              : 'bg-white border-gray-300',
          )}
          dir="ltr"
          value={inputs[cell.inputKey]}
          placeholder={cell.placeholder || ''}
          step={cell.step || '1'}
          onChange={(e) => handleInputChange(cell.inputKey!, e.target.value)}
        />
      )
    }
    if (r) {
      const val = getFieldValue(r, cell.resultKey)
      if (val > 0) {
        return (
          <span className="text-sm tabular-nums font-medium text-green-800 block text-left" dir="ltr">
            {formatNIS(val)}
          </span>
        )
      }
    }
    return null
  }

  const renderFieldCodeButton = (code?: string) => {
    if (!code) return null
    if (code === '---') {
      return <span className="text-gray-300">---</span>
    }
    return (
      <button
        type="button"
        className="rounded px-1 py-0.5 font-mono text-[11px] font-bold text-[#1a3a5c] underline decoration-dotted underline-offset-2 hover:bg-[#eef4fb]"
        onClick={() => void openFieldHelp(code)}
      >
        {code}
      </button>
    )
  }

  const renderDraftActions = () => {
    const savedLabel = draftSavedAt
      ? new Date(draftSavedAt).toLocaleString('he-IL', { dateStyle: 'short', timeStyle: 'short' })
      : ''

    return (
      <div className="mb-4 flex flex-wrap items-center gap-2 rounded-md border border-[#cfe0f0] bg-[#f7fbff] px-3 py-2 text-sm text-[#23496d]">
        <button
          type="button"
          onClick={saveDraft}
          className="inline-flex items-center gap-2 rounded bg-[#2f658d] px-4 py-1 text-sm text-white"
        >
          <Save className="h-4 w-4" />
          שמירה
        </button>
        {draftStatus === 'saved' ? <span>הטיוטה נשמרה{savedLabel ? `: ${savedLabel}` : ''}</span> : null}
        {draftStatus === 'restored' ? <span>הטיוטה האחרונה שוחזרה{savedLabel ? `: ${savedLabel}` : ''}</span> : null}
        {draftStatus === 'error' ? <span className="text-red-700">שמירת הטיוטה נכשלה בדפדפן הזה</span> : null}
      </div>
    )
  }

  const renderGeneralCodeBadge = (row: GeneralRow) => {
    if (isNumericFieldCode(row.code)) {
      return renderFieldCodeButton(row.code)
    }
    return (
      <span className="rounded bg-[#eef4fb] px-2 py-0.5 text-[11px] font-bold text-[#23496d]">
        {row.displayCode || 'מידע'}
      </span>
    )
  }

  const nextTab = () => {
    setTabValidationErrors([])
    setError('')
    setActiveTab((prev) => {
      if (prev === 'personal') return 'general'
      if (prev === 'general') return 'income'
      return 'income'
    })
  }

  const clearCurrentTab = () => {
    setTabValidationErrors([])
    setError('')
    if (activeTab === 'personal') {
      setPersonalForm({})
      return
    }
    if (activeTab === 'general') {
      setGeneralForm({})
      return
    }
    setInputs((prev) => Object.fromEntries(Object.keys(prev).map((key) => [key, ''])))
    setAutoFilled(new Set())
  }

  const validateCurrentTab = () => {
    const errors: string[] = []

    if (activeTab === 'personal') {
      const requiredFields = [
        ['taxpayer_id', 'חסר מספר זהות של בן הזוג הרשום'],
        ['taxpayer_first_name', 'חסר שם פרטי של בן הזוג הרשום'],
        ['taxpayer_last_name', 'חסר שם משפחה של בן הזוג הרשום'],
        ['taxpayer_birth_date', 'חסר תאריך לידה של בן הזוג הרשום'],
        ['marital_status', 'חסר מצב משפחתי בשנת המס'],
      ] as const

      for (const [field, message] of requiredFields) {
        if (!readPersonalValue(field).trim()) errors.push(message)
      }

      const taxpayerId = readPersonalValue('taxpayer_id').replace(/\D/g, '')
      const spouseId = readPersonalValue('spouse_id').replace(/\D/g, '')
      if (taxpayerId && taxpayerId.length < 8) errors.push('מספר זהות של בן הזוג הרשום קצר מדי')
      if (spouseId && spouseId.length < 8) errors.push('מספר זהות של בן/בת הזוג קצר מדי')
      const email = readPersonalValue('email')
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.push('כתובת הדוא"ל אינה תקינה')
    }

    if (activeTab === 'general') {
      const importantCodes = ['foreign_income_file', 'foreign_income_household', 'settlement_type', '331', '297', '365']
      for (const code of importantCodes) {
        if (!generalForm[code]) errors.push(`חסר מענה לשדה ${code} בפרטים כלליים`)
      }
      for (const code of ['273', '274']) {
        if (generalForm[code] && !generalForm[`${code}_date`]) {
          errors.push(`חסר תאריך עבור שדה ${code}`)
        }
      }
      if (generalForm['331'] === 'yes' && !generalForm['331_detail']) {
        errors.push('נדרש לבחור פירוט עבור שדה 331')
      }
      if (generalForm['spouse_report_mode'] === 'yes' && !generalForm['spouse_report_mode_detail']) {
        errors.push('נדרש לבחור פירוט עבור שדה בן/בת זוג')
      }
      if (generalForm['263'] === 'yes' && !generalForm['263_reference']) {
        errors.push('נדרש לציין אסמכתה עבור שדה 263')
      }
      if (generalForm['108'] === 'true' && getCheckedGroupValues(generalForm, '108_roles').length === 0) {
        errors.push('נדרש לבחור לפחות פירוט אחד עבור שדה 108')
      }
    }

    if (activeTab === 'income') {
      const hasAnyValue = Object.values(inputs).some((value) => value.trim() !== '') || yearDocs.length > 0
      if (!hasAnyValue) errors.push('לא מולאו נתונים בפירוט הכנסות ואין מסמכים שהועלו')
    }

    setTabValidationErrors(errors)
    setError(errors.length === 0 ? '' : '')
  }

  const personalPrefill = {
    tax_file_number: '',
    tax_year: String(taxYear),
    taxpayer_id: String(idSupplement?.extracted?.holder_id?.value || ''),
    taxpayer_first_name: String(idSupplement?.extracted?.holder_name?.value || '').split(' ')[0] || '',
    taxpayer_last_name: String(idSupplement?.extracted?.holder_name?.value || '').split(' ').slice(1).join(' '),
    taxpayer_birth_date: normalizeSupplementDate(String(idSupplement?.extracted?.holder_birth_date?.value || '')),
    taxpayer_occupation: '',
    branch_code: '',
    spouse_id: String(idSupplement?.extracted?.spouse_id?.value || ''),
    spouse_first_name: String(idSupplement?.extracted?.spouse_name?.value || '').split(' ')[0] || '',
    spouse_last_name: String(idSupplement?.extracted?.spouse_name?.value || '').split(' ').slice(1).join(' ') || String(idSupplement?.extracted?.holder_name?.value || '').split(' ').slice(1).join(' '),
    spouse_birth_date: normalizeSupplementDate(String(idSupplement?.extracted?.spouse_birth_date?.value || '')),
    marital_status: idSupplement?.extracted?.spouse_id?.value ? 'נשוי' : '',
    filing_status: '',
    spouse_has_separate_file: 'false',
    address_street: String(idSupplement?.extracted?.address_street?.value || ''),
    address_house_number: String(idSupplement?.extracted?.address_house_number?.value || ''),
    address_city: String(idSupplement?.extracted?.address_city?.value || ''),
    address_zip: String(idSupplement?.extracted?.address_zip?.value || ''),
    address_po_box: '',
    email: '',
    phone: '',
    cellphone: '',
    fax: '',
    business_activity: '',
    business_name: '',
    business_address: '',
    business_city: '',
    business_tax_file: '',
    employees_count: '',
    bank_number: '',
    branch_number: '',
    account_number: '',
    account_owner_name: '',
    representative_name: '',
    representative_license: '',
    representative_phone: '',
    representative_email: '',
  }

  const readPersonalValue = (key: string) => personalForm[key] ?? personalPrefill[key as keyof typeof personalPrefill] ?? ''

  const isAutoFilledFromId = (key: string) => {
    if (!idSupplement) return false
    const map: Record<string, string> = {
      taxpayer_id: 'holder_id',
      taxpayer_first_name: 'holder_name',
      taxpayer_last_name: 'holder_name',
      taxpayer_birth_date: 'holder_birth_date',
      spouse_id: 'spouse_id',
      spouse_first_name: 'spouse_name',
      spouse_last_name: 'spouse_name',
      spouse_birth_date: 'spouse_birth_date',
      address_street: 'address_street',
      address_house_number: 'address_house_number',
      address_city: 'address_city',
      address_zip: 'address_zip',
    }
    const sourceField = map[key]
    return sourceField ? hasIdSupplementValue(idSupplement, sourceField) : false
  }

  const renderPersonalInput = (key: string, placeholder = '', type = 'text', className = '') => (
    <input
      type={type}
      value={readPersonalValue(key)}
      placeholder={placeholder}
      onChange={(e) => setPersonalForm((prev) => ({ ...prev, [key]: e.target.value }))}
      className={cn(
        'h-7 w-full rounded-xs border border-[#b8c9dc] bg-white px-2 text-sm',
        isAutoFilledFromId(key) && 'border-green-300 bg-green-50 text-[#1f5132]',
        className,
      )}
      autoComplete="off"
    />
  )

  const renderSectionTitle = (title: string) => (
    <div className="bg-[#dfeaf5] border-y border-[#c3d3e4] px-3 py-1.5 text-sm font-bold text-[#23496d]">
      {title}
    </div>
  )

  const renderPersonalTab = () => (
    <div className="border border-[#efb443] bg-white shadow-sm">
      <div className="p-3">
        {renderDraftActions()}
        {idSupplement ? (
          <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-[#1f5132]">
            פרטים מזהים שזוהו מספח תעודת הזהות מולאו אוטומטית. נדרש להשלים כאן רק פרטים שלא מופיעים בספח, כמו תאריכי לידה, כתובת ופרטי קשר.
          </div>
        ) : null}

        <div className="mb-4 flex flex-wrap gap-2">
          <button onClick={nextTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">הבא &lt;</button>
          <button onClick={clearCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">ניקוי</button>
          <button onClick={validateCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">בדיקה</button>
          <button className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">חזרה</button>
        </div>

        {tabValidationErrors.length > 0 && activeTab === 'personal' && (
          <div className="mb-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <ul className="space-y-1">
              {tabValidationErrors.map((validationError) => (
                <li key={validationError}>{validationError}</li>
              ))}
            </ul>
          </div>
        )}

        <table className="mb-4 w-full border-collapse text-sm">
          <tbody>
            <tr className="bg-[#dfeaf5] text-[#23496d] font-bold">
              {PERSONAL_SUMMARY_FIELDS.map((field) => (
                <td key={field.key} className="border border-[#c3d3e4] px-2 py-1 text-center">{field.label}</td>
              ))}
            </tr>
            <tr>
              {PERSONAL_SUMMARY_FIELDS.map((field) => (
                <td key={field.key} className="border border-[#c3d3e4] px-1 py-1">{renderPersonalInput(field.key)}</td>
              ))}
            </tr>
          </tbody>
        </table>
        <div className="mb-4 border border-[#c3d3e4] bg-[#f8fbff] px-3 py-2 text-sm">
          <div className="mb-2 font-bold text-[#23496d]">מצב משפחתי בשנת המס</div>
          <div className="flex flex-wrap items-center gap-4">
            {PERSONAL_STATUS_OPTIONS.map((status) => (
              <label key={status} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="marital_status"
                  checked={readPersonalValue('marital_status') === status}
                  onChange={() => setPersonalForm((prev) => ({ ...prev, marital_status: status }))}
                />
                {status}
              </label>
            ))}
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={readPersonalValue('spouse_has_separate_file') === 'true'}
                onChange={(e) => setPersonalForm((prev) => ({ ...prev, spouse_has_separate_file: String(e.target.checked) }))}
              />
              בן זוג עם תיק נפרד
            </label>
            <select
              className="h-7 rounded-xs border border-[#b8c9dc] bg-white px-2 text-sm"
              value={readPersonalValue('filing_status')}
              onChange={(e) => setPersonalForm((prev) => ({ ...prev, filing_status: e.target.value }))}
            >
              <option value="">שיוך לתושב חוץ</option>
              <option value="none">לא</option>
              <option value="yes">כן</option>
            </select>
          </div>
        </div>

        {renderSectionTitle('בן הזוג הרשום / בת זוג')}
        <div className="grid grid-cols-1 gap-4 border-x border-b border-[#c3d3e4] p-3 md:grid-cols-2">
          <div>
            <div className="mb-2 text-sm font-bold text-[#23496d]">בן הזוג הרשום</div>
            <div className="grid grid-cols-[120px_1fr] gap-2 text-sm">
              <div className="self-center">מספר זהות</div>{renderPersonalInput('taxpayer_id')}
              <div className="self-center">שם משפחה</div>{renderPersonalInput('taxpayer_last_name')}
              <div className="self-center">שם פרטי</div>{renderPersonalInput('taxpayer_first_name')}
              <div className="self-center">תאריך לידה</div>{renderPersonalInput('taxpayer_birth_date', '', 'date')}
              <div className="self-center">מין</div>
              <div className="flex gap-3">
                {([['male', 'זכר'], ['female', 'נקבה']] as const).map(([val, lbl]) => (
                  <label key={val} className="flex items-center gap-1">
                    <input type="radio" name="taxpayer_gender" checked={readPersonalValue('taxpayer_gender') === val} onChange={() => setPersonalForm((prev) => ({ ...prev, taxpayer_gender: val }))} />
                    {lbl}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div>
            <div className="mb-2 text-sm font-bold text-[#23496d]">בן/בת זוג</div>
            <div className="grid grid-cols-[120px_1fr] gap-2 text-sm">
              <div className="self-center">מספר זהות</div>{renderPersonalInput('spouse_id')}
              <div className="self-center">שם משפחה</div>{renderPersonalInput('spouse_last_name')}
              <div className="self-center">שם פרטי</div>{renderPersonalInput('spouse_first_name')}
              <div className="self-center">תאריך לידה</div>{renderPersonalInput('spouse_birth_date', '', 'date')}
            </div>
          </div>
        </div>

        {renderSectionTitle('פרטי התקשרות')}
        <div className="grid grid-cols-1 gap-3 border-x border-b border-[#c3d3e4] p-3 md:grid-cols-[1fr_1fr]">
          <div className="grid grid-cols-[120px_1fr] gap-2 text-sm">
            <div className="self-center">רחוב</div>{renderPersonalInput('address_street')}
            <div className="self-center">מספר בית</div>{renderPersonalInput('address_house_number')}
            <div className="self-center">יישוב</div>{renderPersonalInput('address_city')}
            <div className="self-center">מיקוד</div>{renderPersonalInput('address_zip')}
            <div className="self-center">ת.ד.</div>{renderPersonalInput('address_po_box')}
          </div>
          <div className="grid grid-cols-[120px_1fr] gap-2 text-sm">
            <div className="self-center">טלפון</div>{renderPersonalInput('phone')}
            <div className="self-center">טלפון נייד</div>{renderPersonalInput('cellphone')}
            <div className="self-center">פקס</div>{renderPersonalInput('fax')}
            <div className="self-center">כתובת דוא"ל</div>{renderPersonalInput('email')}
          </div>
        </div>

        {renderSectionTitle('פרטי העסק')}
        <div className="grid grid-cols-1 gap-3 border-x border-b border-[#c3d3e4] p-3 md:grid-cols-2">
          <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
            <div className="self-center">העיסוק העיקרי</div>{renderPersonalInput('business_activity')}
            <div className="self-center">שם העסק</div>{renderPersonalInput('business_name')}
            <div className="self-center">כתובת העסק</div>{renderPersonalInput('business_address')}
            <div className="self-center">יישוב העסק</div>{renderPersonalInput('business_city')}
          </div>
          <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
            <div className="self-center">מספר תיק העסק</div>{renderPersonalInput('business_tax_file')}
            <div className="self-center">שמות המעבידים</div>{renderPersonalInput('employees_count')}
          </div>
        </div>

        {renderSectionTitle('פרטי בנק')}
        <div className="grid grid-cols-1 gap-3 border-x border-b border-[#c3d3e4] p-3 md:grid-cols-[120px_1fr_120px_1fr_120px_1fr] text-sm">
          <div className="self-center">קוד בנק</div>{renderPersonalInput('bank_number')}
          <div className="self-center">סמל סניף</div>{renderPersonalInput('branch_number')}
          <div className="self-center">מספר חשבון</div>{renderPersonalInput('account_number')}
          <div className="self-center">שם בעל החשבון</div>{renderPersonalInput('account_owner_name')}
        </div>

        {renderSectionTitle('פרטי מגיש הדו"ח')}
        <div className="grid grid-cols-1 gap-3 border-x border-b border-[#c3d3e4] p-3 md:grid-cols-2">
          <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
            <div className="self-center">שם המשרד</div>{renderPersonalInput('representative_name')}
            <div className="self-center">מספר עוסק מורשה</div>{renderPersonalInput('representative_license')}
          </div>
          <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
            <div className="self-center">טלפון</div>{renderPersonalInput('representative_phone')}
            <div className="self-center">כתובת דוא"ל</div>{renderPersonalInput('representative_email')}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={nextTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">הבא &lt;</button>
          <button onClick={clearCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">ניקוי</button>
          <button onClick={validateCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">בדיקה</button>
          <button className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">חזרה</button>
        </div>
      </div>
    </div>
  )

  const updateGeneralValue = (key: string, value: string) => {
    setGeneralForm((prev) => ({ ...prev, [key]: value }))
  }

  const toggleGeneralGroupValue = (key: string, option: string, checked: boolean) => {
    setGeneralForm((prev) => {
      const values = new Set(getCheckedGroupValues(prev, key))
      if (checked) values.add(option)
      else values.delete(option)
      return { ...prev, [key]: Array.from(values).join('|') }
    })
  }

  const renderGeneralControl = (row: GeneralRow) => {
    const value = generalForm[row.code] ?? ''
    if (row.type === 'checkbox') {
      return <input type="checkbox" checked={value === 'true'} onChange={(e) => updateGeneralValue(row.code, String(e.target.checked))} />
    }
    if (row.type === 'select') {
      return (
        <select className="h-8 rounded-sm border border-gray-300 bg-white px-2 text-sm" value={value} onChange={(e) => updateGeneralValue(row.code, e.target.value)}>
          <option value="">בחר</option>
          {(row.options ?? [
            { value: 'no', label: 'לא' },
            { value: 'yes', label: 'כן' },
          ]).map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      )
    }
    if (row.type === 'immigrant-status-date') {
      return (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'new_immigrant'} onChange={() => updateGeneralValue(row.code, 'new_immigrant')} />עולה חדש</label>
          <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'veteran_returning_resident'} onChange={() => updateGeneralValue(row.code, 'veteran_returning_resident')} />תושב חוזר ותיק</label>
          <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'returning_resident'} onChange={() => updateGeneralValue(row.code, 'returning_resident')} />תושב חוזר</label>
          <button
            type="button"
            className="rounded border border-gray-300 px-2 py-1 text-xs text-[#23496d]"
            onClick={() => {
              updateGeneralValue(row.code, '')
              updateGeneralValue(`${row.code}_date`, '')
            }}
          >ניקוי</button>
          <input type="date" className="h-8 rounded-sm border border-gray-300 bg-white px-2 disabled:bg-gray-100" disabled={!value} value={generalForm[`${row.code}_date`] || ''} onChange={(e) => updateGeneralValue(`${row.code}_date`, e.target.value)} />
        </div>
      )
    }
    if (row.type === 'radio-with-select') {
      const detailValue = generalForm[`${row.code}_detail`] ?? ''
      return (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'no'} onChange={() => {
            updateGeneralValue(row.code, 'no')
            updateGeneralValue(`${row.code}_detail`, '')
          }} />לא</label>
          <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'yes'} onChange={() => updateGeneralValue(row.code, 'yes')} />כן</label>
          <select className="h-8 rounded-sm border border-gray-300 bg-white px-2 text-sm disabled:bg-gray-100" disabled={value !== 'yes'} value={detailValue} onChange={(e) => updateGeneralValue(`${row.code}_detail`, e.target.value)}>
            <option value="">בחר</option>
            {(row.options ?? []).map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      )
    }
    if (row.type === 'radio-with-text') {
      const referenceValue = generalForm[`${row.code}_reference`] ?? ''
      return (
        <div className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'no'} onChange={() => {
              updateGeneralValue(row.code, 'no')
              updateGeneralValue(`${row.code}_reference`, '')
            }} />לא</label>
            <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'yes'} onChange={() => updateGeneralValue(row.code, 'yes')} />כן</label>
            <input type="text" className="h-8 min-w-45 rounded-sm border border-gray-300 px-2 disabled:bg-gray-100" disabled={value !== 'yes'} value={referenceValue} placeholder="לדוגמה: טופס 1213" onChange={(e) => updateGeneralValue(`${row.code}_reference`, e.target.value)} />
          </div>
          {row.hint ? <div className="text-xs text-[#5d6f85]">{row.hint}</div> : null}
        </div>
      )
    }
    if (row.type === 'checkbox-group') {
      const checkedValues = getCheckedGroupValues(generalForm, `${row.code}_roles`)
      const isChecked = value === 'true'
      return (
        <div className="space-y-2 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={isChecked} onChange={(e) => {
            updateGeneralValue(row.code, String(e.target.checked))
            if (!e.target.checked) updateGeneralValue(`${row.code}_roles`, '')
          }} />יש נאמנות רלוונטית</label>
          <div className="flex flex-col gap-1 text-[#23496d]">
            {(row.options ?? []).map((option) => (
              <label key={option.value} className="flex items-center gap-2">
                <input type="checkbox" disabled={!isChecked} checked={checkedValues.includes(option.value)} onChange={(e) => toggleGeneralGroupValue(`${row.code}_roles`, option.value, e.target.checked)} />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>
      )
    }
    return (
      <div className="flex items-center gap-4 text-sm">
        <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'no'} onChange={() => updateGeneralValue(row.code, 'no')} />לא</label>
        <label className="flex items-center gap-1"><input type="radio" name={row.code} checked={value === 'yes'} onChange={() => updateGeneralValue(row.code, 'yes')} />כן</label>
      </div>
    )
  }

  const renderGeneralTab = () => (
    <div className="border border-[#efb443] bg-white shadow-sm">
      <div className="p-3">
        {renderDraftActions()}
        <div className="mb-4 rounded-md border border-[#cfe0f0] bg-[#f7fbff] px-3 py-3 text-sm text-[#23496d]">
          <div className="font-bold">עזרה במילוי הפרטים הכלליים</div>
          <div className="mt-1 text-[#5d6f85]">לכל שדה יש עכשיו הסבר קצר בעברית. אם משהו לא ברור, אפשר לבחור שדה ולשאול את העוזר לפני החישוב.</div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <button type="button" className="rounded border border-[#c3d3e4] bg-white px-2 py-1" onClick={() => chatRef.current?.askAndSend(buildFieldAssistantQuestion(GENERAL_INFO_SECTIONS[0].rows[0]))}>מה זו הכנסה מחו"ל?</button>
            <button type="button" className="rounded border border-[#c3d3e4] bg-white px-2 py-1" onClick={() => chatRef.current?.askAndSend(buildFieldAssistantQuestion(GENERAL_INFO_SECTIONS[0].rows[3]))}>מה זה בה"ח/י עולה?</button>
            <button type="button" className="rounded border border-[#c3d3e4] bg-white px-2 py-1" onClick={() => chatRef.current?.askAndSend(buildFieldAssistantQuestion(GENERAL_INFO_SECTIONS[1].rows[0]))}>מתי מסמנים שדה 331?</button>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          <button onClick={nextTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">הבא &lt;</button>
          <button onClick={clearCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">ניקוי</button>
          <button onClick={validateCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">בדיקה</button>
        </div>

        {tabValidationErrors.length > 0 && activeTab === 'general' && (
          <div className="mb-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <ul className="space-y-1">
              {tabValidationErrors.map((validationError) => (
                <li key={validationError}>{validationError}</li>
              ))}
            </ul>
          </div>
        )}

        {GENERAL_INFO_SECTIONS.map((section) => (
          <div key={section.title} className="mb-5">
            {renderSectionTitle(section.title)}
            <table className="w-full border-collapse text-sm">
              <tbody>
                {section.rows.map((row) => (
                  <tr key={row.code} className="border-x border-b border-[#c3d3e4] align-top">
                    <td className="w-16 bg-[#eef4fb] px-2 py-3 text-center font-mono font-bold text-[#23496d]">{renderGeneralCodeBadge(row)}</td>
                    <td className="px-3 py-3 text-right text-[#23496d]">
                      <div>{row.label}</div>
                      <div className="mt-1 text-xs leading-5 text-[#5d6f85]">{row.explanation}</div>
                      {row.hint ? <div className="mt-1 text-xs text-[#6a7b90]">{row.hint}</div> : null}
                      <button
                        type="button"
                        className="mt-2 rounded border border-[#c3d3e4] bg-white px-2 py-1 text-xs text-[#23496d] hover:bg-[#eef4fb]"
                        onClick={() => chatRef.current?.askAndSend(buildFieldAssistantQuestion(row))}
                      >
                        לא בטוח? שאל את העוזר
                      </button>
                    </td>
                    <td className="w-[320px] px-3 py-3">{renderGeneralControl(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

        <div className="flex flex-wrap gap-2">
          <button onClick={nextTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">הבא &lt;</button>
          <button onClick={clearCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">ניקוי</button>
          <button onClick={validateCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">בדיקה</button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="max-w-5xl mx-auto space-y-4 pb-12">
      {/* ===== HEADER ===== */}
      <div className="bg-[#1a3a5c] text-white px-6 py-4 rounded-t-lg">
        <h1 className="text-lg font-bold text-center">
          דוח שנתי על ההכנסה — טופס 1301 — שנת המס {taxYear}
        </h1>
      </div>

      <div className="flex items-end justify-end gap-1 border-b border-[#d7e2f0]">
        <button onClick={() => setActiveTab('personal')} className={cn('px-4 py-2 text-sm border border-b-0 rounded-t-md', activeTab === 'personal' ? 'bg-[#f6b73c] text-[#1a3a5c] font-bold' : 'bg-[#eef4fb] text-[#4a6482]')}>פרטים אישיים</button>
        <button onClick={() => setActiveTab('general')} className={cn('px-4 py-2 text-sm border border-b-0 rounded-t-md', activeTab === 'general' ? 'bg-[#f6b73c] text-[#1a3a5c] font-bold' : 'bg-[#eef4fb] text-[#4a6482]')}>פרטים כלליים</button>
        <button onClick={() => setActiveTab('income')} className={cn('px-4 py-2 text-sm border border-b-0 rounded-t-md', activeTab === 'income' ? 'bg-[#f6b73c] text-[#1a3a5c] font-bold' : 'bg-[#eef4fb] text-[#4a6482]')}>פירוט הכנסות</button>
      </div>

      {/* ===== DOCUMENTS BAR ===== */}
      <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-md border text-sm">
        <FileText className="h-4 w-4 text-gray-400 shrink-0" />
        {yearDocs.length === 0 ? (
          <span className="text-muted-foreground">
            לא הועלו מסמכים.{' '}
            <a href="/documents" className="text-primary underline">העלה מסמכים</a>
          </span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(docsByType).map(([type, docs]) => (
              <span key={type} className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-0.5 text-xs border">
                <CheckCircle2 className="h-3 w-3 text-green-600" />
                {DOC_TYPE_LABELS[type] || type} ({docs.length})
              </span>
            ))}
          </div>
        )}
      </div>

      {activeTab === 'personal' && renderPersonalTab()}
      {activeTab === 'general' && renderGeneralTab()}

      {/* ===== IRS FORM TABLE ===== */}
      {activeTab === 'income' && <div className="border rounded-lg overflow-hidden shadow-sm">
        <div className="border-b bg-white px-4 py-3">
          {renderDraftActions()}
          <div className="flex flex-wrap gap-2">
            <button onClick={nextTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">הבא &lt;</button>
            <button onClick={clearCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">ניקוי</button>
            <button onClick={validateCurrentTab} className="rounded bg-[#2f658d] px-4 py-1 text-sm text-white">בדיקה</button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm min-w-175">
            <thead>
              <tr className="bg-[#1a3a5c] text-white">
                <th rowSpan={2} className="py-2 px-2 text-center w-10 border-l border-[#2a4a6c]">מס׳</th>
                <th rowSpan={2} className="py-2 px-3 text-right border-l border-[#2a4a6c]">תיאור</th>
                <th colSpan={2} className="py-1.5 px-2 text-center border-l border-b border-[#2a4a6c]">בן הזוג הרשום</th>
                <th colSpan={2} className="py-1.5 px-2 text-center border-b border-[#2a4a6c]">בן/בת הזוג</th>
              </tr>
              <tr className="bg-[#24476a] text-white/80 text-xs">
                <th className="py-1 px-1 text-center w-10 border-l border-[#2a4a6c]">שדה</th>
                <th className="py-1 px-1 text-center w-30 border-l border-[#2a4a6c]">סכום</th>
                <th className="py-1 px-1 text-center w-10 border-l border-[#2a4a6c]">שדה</th>
                <th className="py-1 px-1 text-center w-30">סכום</th>
              </tr>
            </thead>
            <tbody>
              {IRS_SECTIONS.map((section) => (
                <Fragment key={section.partId}>
                  <tr className="bg-[#dce7f5]">
                    <td colSpan={6} className="py-2 px-3 font-bold text-[#1a3a5c] border-b border-[#b5c8e0]">
                      {section.title}
                    </td>
                  </tr>
                  {section.rows.map((row) => (
                    <tr key={row.num} className="border-b border-gray-200 hover:bg-blue-50/30">
                      <td className="py-1 px-2 text-center text-xs text-gray-400 border-l border-gray-100">
                        {row.num}
                      </td>
                      <td className="py-1 px-3 border-l border-gray-100">
                        <div>{row.description}</div>
                        {row.notes?.length ? (
                          <div className="mt-0.5 space-y-0.5 text-[11px] text-[#60738b]">
                            {row.notes.map((note) => (
                              <div key={note}>{note}</div>
                            ))}
                          </div>
                        ) : null}
                      </td>
                      <td className="py-1 px-1 text-center font-mono text-[11px] font-bold text-[#1a3a5c] border-l border-gray-100">
                        {renderFieldCodeButton(row.taxpayer?.code)}
                      </td>
                      <td className="py-0.5 px-1.5 border-l border-gray-100">
                        {row.taxpayer && renderCell(row.taxpayer)}
                      </td>
                      <td className="py-1 px-1 text-center font-mono text-[11px] font-bold text-[#1a3a5c] border-l border-gray-100">
                        {renderFieldCodeButton(row.spouse?.code)}
                      </td>
                      <td className="py-0.5 px-1.5">
                        {row.spouse && renderCell(row.spouse)}
                      </td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {/* Calculate button inside form container */}
        <div className="bg-gray-50 border-t px-4 py-3 flex justify-center">
          <Button onClick={handleCalculate} disabled={loading} size="lg" className="gap-2 px-10">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
            חשב
          </Button>
        </div>
      </div>}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 p-3 text-destructive text-sm">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      <Dialog open={fieldHelpOpen} onClose={() => setFieldHelpOpen(false)}>
        <DialogHeader onClose={() => setFieldHelpOpen(false)}>
          <div>
            <DialogTitle>{fieldHelp?.title || 'הסבר שדה'}</DialogTitle>
            <div className="mt-1 text-sm text-muted-foreground">
              {fieldHelp?.code ? `שדה ${fieldHelp.code}` : ''}
              {fieldHelp?.part_name_he ? ` | ${fieldHelp.part_name_he}` : ''}
              {fieldHelp?.section_num ? ` | סעיף ${fieldHelp.section_num}` : ''}
            </div>
          </div>
        </DialogHeader>
        <DialogContent className="space-y-4 text-sm leading-6">
          {fieldHelpLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              טוען הסבר שדה...
            </div>
          ) : (
            <>
              <p>{fieldHelp?.description}</p>
              {fieldHelp?.tax_rate ? (
                <div className="rounded border bg-[#f8fbff] px-3 py-2 text-[#23496d]">
                  שיעור מס רלוונטי: {fieldHelp.tax_rate}
                </div>
              ) : null}
              {fieldHelp?.guide_line ? (
                <div className="text-xs text-[#60738b]">
                  הפניה בקובץ ההנחיות: שורה {fieldHelp.guide_line}
                </div>
              ) : null}
              {fieldHelp?.notes?.length ? (
                <div>
                  <div className="mb-1 font-semibold text-[#23496d]">הערות</div>
                  <ul className="space-y-1 text-[#4f6279]">
                    {fieldHelp.notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {fieldHelp && !fieldHelpLoading && (
                <button
                  type="button"
                  className="mt-2 flex w-full items-center justify-center gap-2 rounded-md border border-[#2f658d] bg-[#f0f6fc] px-3 py-2 text-sm font-medium text-[#2f658d] hover:bg-[#ddeaf6] transition-colors"
                  onClick={() => {
                    setFieldHelpOpen(false)
                    chatRef.current?.askAndSend(
                      `הסבר לי בשפה פשוטה מה המשמעות של שדה ${fieldHelp.code} (${fieldHelp.title}), מתי ממלאים אותו, ומה כדאי לבדוק לפי הנתונים שלי.`
                    )
                  }}
                >
                  <MessageCircle className="h-4 w-4" />
                  שאל את העוזר על שדה זה
                </button>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* ===== RESULTS ===== */}
      {r && (
        <div ref={resultRef} className="space-y-4 mt-6">
          {/* Balance */}
          <Card className={cn(
            'border-2',
            balance > 0 ? 'border-red-300 bg-red-50' : 'border-green-300 bg-green-50',
          )}>
            <CardContent className="flex items-center justify-between py-6">
              <div className="flex items-center gap-3">
                {balance > 0
                  ? <TrendingUp className="h-8 w-8 text-red-600" />
                  : <TrendingDown className="h-8 w-8 text-green-600" />}
                <div>
                  <p className="text-lg font-bold">{balance > 0 ? 'יתרה לתשלום' : 'החזר מס'}</p>
                  <p className={cn(
                    'text-3xl font-bold',
                    balance > 0 ? 'text-red-700' : 'text-green-700',
                  )}>
                    {formatNIS(Math.abs(balance))}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {balance > 0
                      ? 'שילמת פחות מס ממה שנדרש — עליך לשלם את ההפרש למס הכנסה'
                      : balance < 0
                        ? 'שילמת יותר מס ממה שנדרש — מגיע לך החזר ממס הכנסה'
                        : 'אין הפרש — המס שנוכה תואם בדיוק את המס הנדרש'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tax Breakdown */}
          <Card>
            <CardHeader><CardTitle>חישוב מס</CardTitle></CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <ResultRow label="מס פרוגרסיבי — נישום" value={r.calculation.tax_regular_taxpayer} />
                  <ResultRow label="מס פרוגרסיבי — בן/בת זוג" value={r.calculation.tax_regular_spouse} />
                  <ResultRow label="מס 10% (שכ״ד למגורים)" value={r.calculation.tax_rental_10pct} />
                  <ResultRow label="מס 15% (ריבית/שכ״ד חו״ל)" value={r.calculation.tax_15pct} />
                  <ResultRow label="מס 20% (דיבידנד מועדף/ריבית)" value={r.calculation.tax_20pct} />
                  <ResultRow label="מס 25% (דיבידנד/ריבית)" value={r.calculation.tax_25pct} />
                  <ResultRow label="מס 30% (דיבידנד מהותי)" value={r.calculation.tax_30pct} />
                  <ResultRow label="מס 31% (אנרגיות מתחדשות)" value={r.calculation.tax_31pct} />
                  <ResultRow label="מס 35% (הימורים/משיכה שלא כדין)" value={r.calculation.tax_35pct} />
                  <ResultRow label="מס רווח הון" value={r.calculation.tax_capital_gains} />
                  <ResultRow label="מס יסף (3%)" value={r.calculation.surtax} highlight />
                  <ResultRow label="סה״כ מס ברוטו" value={r.calculation.gross_tax} bold />
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Credits */}
          <Card>
            <CardHeader><CardTitle>זיכויים</CardTitle></CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <ResultRow label="נקודות זיכוי — נישום" value={r.calculation.credit_points_amount_taxpayer} negative />
                  <ResultRow label="נקודות זיכוי — בן/בת זוג" value={r.calculation.credit_points_amount_spouse} negative />
                  <ResultRow label="זיכוי פנסיה 45א — נישום" value={r.calculation.pension_employee_credit_taxpayer} negative />
                  <ResultRow label="זיכוי פנסיה 45א — בן/בת זוג" value={r.calculation.pension_employee_credit_spouse} negative />
                  <ResultRow label="זיכוי תרומות (35%)" value={r.calculation.donation_credit} negative />
                  <ResultRow label="זיכוי ביטוח חיים — נישום" value={r.calculation.life_insurance_credit_taxpayer} negative />
                  <ResultRow label="זיכוי ביטוח חיים — בן/בת זוג" value={r.calculation.life_insurance_credit_spouse} negative />
                  <ResultRow label="סה״כ זיכויים נישום" value={r.calculation.total_credits_taxpayer} negative />
                  <ResultRow label="סה״כ זיכויים בן/בת זוג" value={r.calculation.total_credits_spouse} negative />
                  <ResultRow label="סה״כ זיכויים" value={r.calculation.total_credits} bold negative />
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardHeader><CardTitle>סיכום</CardTitle></CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <tbody>
                  <ResultRow label="מס נטו (אחרי זיכויים)" value={r.calculation.net_tax} bold />
                  {r.calculation.foreign_tax_credit > 0 && (
                    <ResultRow label="  כולל זיכוי חו״ל" value={r.calculation.foreign_tax_credit} negative />
                  )}
                  <ResultRow label="מס שנוכה ממשכורת (סעיף 84)" value={r.calculation.total_withheld} negative />
                  <ResultRow label="ניכוי ריבית/דיבידנד (סעיף 85)" value={r.withholdings.field_043} negative />
                  <ResultRow label="ניכוי מהכנסות אחרות (סעיף 87)" value={r.withholdings.field_040} negative />
                  <ResultRow label="מס שבח (סעיף 88)" value={r.withholdings.field_041} negative />
                  <ResultRow label="מקדמות מדוח שנתי" value={r.withholdings.field_tax_advance} negative />
                  <ResultRow label="מס שכירות ששולם" value={r.withholdings.field_220} negative />
                  <ResultRow label="סה״כ ששולם" value={r.calculation.total_paid} bold negative />
                  <tr className="border-t-2 border-foreground">
                    <td className="py-2 font-bold text-base">
                      {balance > 0 ? 'יתרה לתשלום' : 'החזר מס'}
                    </td>
                    <td className={cn(
                      'py-2 text-left font-bold text-base',
                      balance > 0 ? 'text-red-600' : 'text-green-600',
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

          <Card>
            <CardHeader>
              <CardTitle>השלמות ובדיקות מומלצות</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {advisorItems.map((item) => (
                  <div
                    key={item.id}
                    className={cn(
                      'rounded-lg border px-3 py-2',
                      item.level === 'missing' && 'border-red-200 bg-red-50',
                      item.level === 'warn' && 'border-yellow-200 bg-yellow-50',
                      item.level === 'info' && 'border-blue-200 bg-blue-50',
                    )}
                  >
                    <div className="font-medium text-[#1a3a5c]">{item.title}</div>
                    <div className="mt-1 text-sm text-[#4f6279]">{item.detail}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {r.source_documents.length > 0 && (
            <p className="text-xs text-muted-foreground">
              מקור: {r.source_documents.join(', ')}
            </p>
          )}
        </div>
      )}

      <FloatingChat ref={chatRef} snapshot={chatSnapshot} />
    </div>
  )
}

// --- Helper Component ---

function ResultRow({
  label, value, bold, highlight, negative,
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
