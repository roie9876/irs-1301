export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
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
  extracted: Form106Extraction
  user_corrected: boolean
}

export interface UploadResult {
  filename: string
  doc_id: string
  status: 'success' | 'error' | 'encrypted'
  error?: string
  extracted?: Form106Extraction
}

export interface UploadResponse {
  results: UploadResult[]
}

export interface DocumentListResponse {
  documents: DocumentInfo[]
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
