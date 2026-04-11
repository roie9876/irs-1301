from pydantic import BaseModel


class FieldValue(BaseModel):
    value: float | str | int | None = None
    confidence: float = 0.0


class Form106Extraction(BaseModel):
    employer_name: FieldValue = FieldValue()
    employer_id: FieldValue = FieldValue()
    tax_year: FieldValue = FieldValue()
    gross_salary: FieldValue = FieldValue()
    tax_withheld: FieldValue = FieldValue()
    pension_employer: FieldValue = FieldValue()
    pension_employee: FieldValue = FieldValue()
    insured_income: FieldValue = FieldValue()
    convalescence_pay: FieldValue = FieldValue()
    education_fund: FieldValue = FieldValue()
    work_days: FieldValue = FieldValue()
    national_insurance: FieldValue = FieldValue()
    health_insurance: FieldValue = FieldValue()
    donations: FieldValue = FieldValue()


class Form867Extraction(BaseModel):
    broker_name: FieldValue = FieldValue()
    broker_id: FieldValue = FieldValue()
    account_name: FieldValue = FieldValue()
    tax_year: FieldValue = FieldValue()
    dividend_income: FieldValue = FieldValue()
    dividend_foreign: FieldValue = FieldValue()
    dividend_tax_rate: FieldValue = FieldValue()
    dividend_tax_withheld: FieldValue = FieldValue()
    foreign_tax_paid: FieldValue = FieldValue()
    interest_income: FieldValue = FieldValue()
    interest_tax_withheld: FieldValue = FieldValue()


class RentalPaymentExtraction(BaseModel):
    taxpayer_name: FieldValue = FieldValue()
    taxpayer_id: FieldValue = FieldValue()
    tax_year: FieldValue = FieldValue()
    payment_amount: FieldValue = FieldValue()
    payment_type: FieldValue = FieldValue()
    payment_date: FieldValue = FieldValue()
    reference_number: FieldValue = FieldValue()


class AnnualSummaryExtraction(BaseModel):
    employee_name: FieldValue = FieldValue()
    employee_id: FieldValue = FieldValue()
    tax_year: FieldValue = FieldValue()
    total_shares_sold: FieldValue = FieldValue()
    ordinary_income_ils: FieldValue = FieldValue()
    capital_income_ils: FieldValue = FieldValue()
    tax_advance_payment: FieldValue = FieldValue()
    gross_proceed_usd: FieldValue = FieldValue()
    tax_plan: FieldValue = FieldValue()


class ReceiptExtraction(BaseModel):
    vendor_name: FieldValue = FieldValue()
    receipt_number: FieldValue = FieldValue()
    date: FieldValue = FieldValue()
    amount_before_vat: FieldValue = FieldValue()
    vat_amount: FieldValue = FieldValue()
    total_amount: FieldValue = FieldValue()
    description: FieldValue = FieldValue()
    payer_name: FieldValue = FieldValue()
    payer_id: FieldValue = FieldValue()


class RentalExcelExtraction(BaseModel):
    tax_year: FieldValue = FieldValue()
    properties: FieldValue = FieldValue()  # comma-separated property names
    total_annual_income: FieldValue = FieldValue()
    tax_rate_pct: FieldValue = FieldValue()
    tax_amount: FieldValue = FieldValue()


# Map of document type to extraction model
EXTRACTION_MODELS = {
    "form_106": Form106Extraction,
    "form_867": Form867Extraction,
    "rental_payment": RentalPaymentExtraction,
    "annual_summary": AnnualSummaryExtraction,
    "receipt": ReceiptExtraction,
    "rental_excel": RentalExcelExtraction,
}


class DocumentInfo(BaseModel):
    doc_id: str
    original_filename: str
    document_type: str = "form_106"
    extracted: dict  # type-specific extraction data
    user_corrected: bool = False


class UploadResult(BaseModel):
    filename: str
    doc_id: str = ""
    status: str  # "success" | "error" | "encrypted"
    error: str = ""
    document_type: str = ""
    extracted: dict | None = None


class UploadResponse(BaseModel):
    results: list[UploadResult]


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class UpdateFieldsRequest(BaseModel):
    fields: dict[str, FieldValue]
