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
    insured_income: FieldValue = FieldValue()
    convalescence_pay: FieldValue = FieldValue()
    education_fund: FieldValue = FieldValue()
    work_days: FieldValue = FieldValue()
    national_insurance: FieldValue = FieldValue()
    health_insurance: FieldValue = FieldValue()


class DocumentInfo(BaseModel):
    doc_id: str
    original_filename: str
    extracted: Form106Extraction
    user_corrected: bool = False


class UploadResult(BaseModel):
    filename: str
    doc_id: str = ""
    status: str  # "success" | "error"
    error: str = ""
    extracted: Form106Extraction | None = None


class UploadResponse(BaseModel):
    results: list[UploadResult]


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class UpdateFieldsRequest(BaseModel):
    fields: dict[str, FieldValue]
