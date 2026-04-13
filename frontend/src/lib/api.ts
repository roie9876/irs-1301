export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface FieldValue {
  value: number | string | null
  confidence: number
}

export interface Form106Extraction {
  employer_name: FieldValue
  employer_id: FieldValue
  tax_year: FieldValue
  gross_salary: FieldValue
  tax_withheld: FieldValue
  pension_employer: FieldValue
  insured_income: FieldValue
  convalescence_pay: FieldValue
  education_fund: FieldValue
  work_days: FieldValue
  national_insurance: FieldValue
  health_insurance: FieldValue
}

export interface DocumentInfo {
  doc_id: string
  original_filename: string
  document_type: string
  extracted: Record<string, FieldValue>
  user_corrected: boolean
  extraction_warnings?: string[]
}

export interface UploadResult {
  filename: string
  doc_id: string
  status: 'success' | 'error' | 'encrypted' | 'skipped'
  error?: string
  document_type?: string
  extracted?: Record<string, FieldValue>
}

export interface UploadResponse {
  results: UploadResult[]
}

export interface DocumentListResponse {
  documents: DocumentInfo[]
}

// Form 1301 types — חלק ג: הכנסות מיגיעה אישית
export interface IncomeFields {
  field_150: number  // עסק/משלח יד — רשום
  field_170: number  // עסק/משלח יד — בן/בת זוג
  field_250: number  // ביט"ל עצמאי — רשום
  field_270: number  // ביט"ל עצמאי — בן/בת זוג
  field_194: number  // ביט"ל שכיר — רשום
  field_196: number  // ביט"ל שכיר — בן/בת זוג
  field_158: number  // משכורת — רשום
  field_172: number  // משכורת — בן/בת זוג
  field_069: number  // משמרות — רשום
  field_068: number  // משמרות — בן/בת זוג
  field_258: number  // מענקי פרישה/קצבאות — רשום
  field_272: number  // מענקי פרישה/קצבאות — בן/בת זוג
}

// חלק ד: הכנסות בשיעורי מס רגילים
export interface OtherIncomeFields {
  field_059: number  // נכס בית — רשום
  field_201: number  // נכס בית — בן/בת זוג
  field_167: number  // אחרות — רשום
  field_205: number  // אחרות — בן/בת זוג
  field_305: number  // אחרות — שני בני הזוג
}

// חלק ה: הכנסות בשיעורי מס מיוחדים
export interface SpecialRateIncomeFields {
  field_060: number  // ריבית ני"ע 15% — רשום
  field_211: number  // ריבית ני"ע 15% — בן/בת זוג
  field_067: number  // ריבית ני"ע 20% — רשום
  field_228: number  // ריבית ני"ע 20% — בן/בת זוג
  field_157: number  // ריבית ני"ע 25% — רשום
  field_257: number  // ריבית ני"ע 25% — בן/בת זוג
  field_173: number  // דיבידנד מועדף 20% — רשום
  field_275: number  // דיבידנד מועדף 20% — בן/בת זוג
  field_141: number  // דיבידנד 25% — רשום
  field_241: number  // דיבידנד 25% — בן/בת זוג
  field_055: number  // דיבידנד מהותי 30% — רשום
  field_212: number  // דיבידנד מהותי 30% — בן/בת זוג
  field_078: number  // ריבית פיקדונות 15% — רשום
  field_217: number  // ריבית פיקדונות 15% — בן/בת זוג
  field_126: number  // ריבית פיקדונות 20% — רשום
  field_226: number  // ריבית פיקדונות 20% — בן/בת זוג
  field_142: number  // ריבית פיקדונות 25% — רשום
  field_242: number  // ריבית פיקדונות 25% — בן/בת זוג
  field_222: number  // שכ"ד למגורים 10% — רשום
  field_284: number  // שכ"ד למגורים 10% — בן/בת זוג
  field_225: number  // שכ"ד מחו"ל 15% — רשום
  field_285: number  // שכ"ד מחו"ל 15% — בן/בת זוג
  field_227: number  // הימורים 35% — רשום
  field_286: number  // הימורים 35% — בן/בת זוג
  field_335: number  // אנרגיות מתחדשות 31% — רשום
  field_337: number  // אנרגיות מתחדשות 31% — בן/בת זוג
  field_288: number  // חלוקה לפנסיה 20% — רשום
  field_338: number  // חלוקה לפנסיה 20% — בן/בת זוג
  field_213: number  // משיכה שלא כדין 35% — רשום
  field_313: number  // משיכה שלא כדין 35% — בן/בת זוג
}

// חלק ח: רווח הון
export interface CapitalGainsFields {
  field_054: number  // מספר טופסי רווח הון
  field_056: number  // סכום מכירות רווח הון
  field_256: number  // סכום מכירות מני"ע
  field_139: number  // רווח הון 25%
}

// חלק י: הכנסות פטורות
export interface ExemptIncomeFields {
  field_109: number  // פטור נכות — רשום
  field_309: number  // פטור נכות — בן/בת זוג
  field_332: number  // פטור שכ"ד
  field_209: number  // סה"כ פטורים
}

// חלק יב: ניכויים אישיים
export interface DeductionFields {
  field_112: number  // אבדן כושר עצמאי — רשום
  field_113: number  // אבדן כושר עצמאי — בן/בת זוג
  field_206: number  // אבדן כושר שכיר — רשום
  field_207: number  // אבדן כושר שכיר — בן/בת זוג
  field_136: number  // קרן השתלמות עצמאי — רשום
  field_137: number  // קרן השתלמות עצמאי — בן/בת זוג
  field_218: number  // קרן השתלמות שכיר — רשום
  field_219: number  // קרן השתלמות שכיר — בן/בת זוג
  field_135: number  // קופ"ג עצמאי — רשום
  field_180: number  // קופ"ג עצמאי — בן/בת זוג
  field_030: number  // ביט"ל לא-עבודה — רשום
  field_089: number  // ביט"ל לא-עבודה — בן/בת זוג
  field_244: number  // הכנסה מבוטחת — רשום
  field_245: number  // הכנסה מבוטחת — בן/בת זוג
  field_248: number  // הפקדות מעביד — רשום
  field_249: number  // הפקדות מעביד — בן/בת זוג
  field_011: number  // דמי הבראה — רשום
  field_012: number  // דמי הבראה — בן/בת זוג
}

// חלק יג: נקודות זיכוי
export interface CreditPointsFields {
  field_020: number  // תושב — רשום
  field_021: number  // תושב — בן/בת זוג
  field_260: number  // ילדים — רשום
  field_262: number  // ילדים — בן/בת זוג
  field_026: number  // הורה חד-הורי
  field_024: number  // חייל — רשום
  field_124: number  // חייל — בן/בת זוג
  field_181: string  // קוד לימודים — רשום
  field_182: string  // קוד לימודים — בן/בת זוג
  credit_points_taxpayer: number
  credit_points_spouse: number
}

// חלק יד: זיכויים
export interface TaxCreditFields {
  field_036: number  // ביטוח חיים — רשום
  field_081: number  // ביטוח חיים — בן/בת זוג
  field_140: number  // שאירים — רשום
  field_240: number  // שאירים — בן/בת זוג
  field_045: number  // עמית שכיר — רשום
  field_086: number  // עמית שכיר — בן/בת זוג
  field_268: number  // עמית עצמאי — רשום
  field_269: number  // עמית עצמאי — בן/בת זוג
  field_132: number  // מוסד — רשום
  field_232: number  // מוסד — בן/בת זוג
  field_037: number  // תרומות ישראל — רשום
  field_237: number  // תרומות ישראל — בן/בת זוג
  field_046: number  // תרומות ארה"ב — רשום
  field_048: number  // תרומות ארה"ב — בן/בת זוג
  field_155: number  // מו"פ — רשום
  field_199: number  // מו"פ — בן/בת זוג
  field_183: number  // אילת
}

// חלק טו: ניכויים במקור
export interface WithholdingFields {
  field_042: number  // מס ממשכורת
  field_043: number  // מס מריבית
  field_040: number  // מס מהכנסות אחרות
  field_041: number  // מס שבח
  field_220: number  // מס שכירות
  field_tax_advance: number
}

export interface TaxCalculation {
  tax_regular_taxpayer: number
  tax_regular_spouse: number
  tax_15pct: number
  tax_20pct: number
  tax_25pct: number
  tax_30pct: number
  tax_31pct: number
  tax_35pct: number
  tax_rental_10pct: number
  tax_capital_gains: number
  surtax: number
  gross_tax: number
  credit_points_amount_taxpayer: number
  credit_points_amount_spouse: number
  pension_employee_credit_taxpayer: number
  pension_employee_credit_spouse: number
  donation_credit: number
  life_insurance_credit_taxpayer: number
  life_insurance_credit_spouse: number
  total_credits_taxpayer: number
  total_credits_spouse: number
  total_credits: number
  gross_tax_taxpayer: number
  gross_tax_spouse: number
  net_tax: number
  foreign_tax_credit: number
  total_withheld: number
  total_paid: number
  balance: number
  interest_cpi_adjustment: number
  balance_after_interest: number
}

export interface Form1301Result {
  tax_year: number
  income: IncomeFields
  other_income: OtherIncomeFields
  special_rate: SpecialRateIncomeFields
  capital_gains: CapitalGainsFields
  exempt: ExemptIncomeFields
  deductions: DeductionFields
  credit_points: CreditPointsFields
  tax_credits: TaxCreditFields
  withholdings: WithholdingFields
  calculation: TaxCalculation
  source_documents: string[]
  warnings: string[]
  effective_inputs: Record<string, number | string>
}

export interface Form1301PreviewResponse {
  result: Form1301Result
}

export interface FieldHelpResponse {
  code: string
  title: string
  description: string
  part_id: string
  part_name_he: string
  section_num: number | null
  section_name_he: string
  guide_line: number | null
  tax_rate: string
  notes: string[]
}

export interface AdvisorItemPayload {
  title: string
  detail: string
  level: string
}

export interface AdvisorAnswerResponse {
  answer: string
}

export async function api<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`/api${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, error.detail || response.statusText)
  }

  return response.json()
}

export async function uploadFiles(files: File[], passwords?: Record<string, string>): Promise<UploadResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  if (passwords && Object.keys(passwords).length > 0) {
    formData.append('passwords', JSON.stringify(passwords))
  }

  const response = await fetch('/api/documents/upload', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, error.detail || response.statusText)
  }

  return response.json()
}
