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
}

export interface UploadResult {
  filename: string
  doc_id: string
  status: 'success' | 'error' | 'encrypted'
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

// Form 1301 types
export interface IncomeFields {
  field_158: number
  field_172: number
  field_222: number
  field_141: number
  field_327: number
  field_139: number
}

export interface TaxCalculation {
  tax_regular_taxpayer: number
  tax_regular_spouse: number
  tax_rental_10pct: number
  tax_dividend_25pct: number
  tax_interest_25pct: number
  tax_capital_gains: number
  surtax: number
  gross_tax: number
  credit_points_amount_taxpayer: number
  credit_points_amount_spouse: number
  pension_credit_taxpayer: number
  pension_credit_spouse: number
  donation_credit: number
  life_insurance_credit: number
  total_credits: number
  net_tax: number
  total_withheld: number
  total_paid: number
  balance: number
}

export interface Form1301Result {
  tax_year: number
  income: IncomeFields
  calculation: TaxCalculation
  source_documents: string[]
  warnings: string[]
}

export interface Form1301PreviewResponse {
  result: Form1301Result
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
