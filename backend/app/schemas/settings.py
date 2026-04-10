from pydantic import BaseModel


class SettingsRequest(BaseModel):
    provider: str  # "openai" | "azure" | "gemini" | "anthropic"
    model: str     # e.g. "gpt-4o", "claude-sonnet-4-20250514"
    api_key: str
    api_base: str = ""  # Azure OpenAI only
    tax_year: int = 2024


class SettingsResponse(BaseModel):
    provider: str
    model: str
    has_api_key: bool  # NEVER expose the actual key per INF-04
    api_base: str = ""
    tax_year: int = 2024


class TestResult(BaseModel):
    success: bool
    message: str


class TaxYearRequest(BaseModel):
    tax_year: int
