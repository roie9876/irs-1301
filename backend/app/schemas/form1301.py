"""Pydantic models for Form 1301 calculation results."""

from pydantic import BaseModel


class IncomeFields(BaseModel):
    """חלק ג + ד — Income fields."""
    # Part ג — Personal labor income
    field_158: float = 0  # Salary — registered (משכורת - רשום)
    field_172: float = 0  # Salary — spouse (משכורת - בן/בת זוג)
    # Part ד — Other income at regular rates
    field_193: float = 0  # Other income — registered
    field_195: float = 0  # Other income — spouse
    # Part ה — Special rate income
    field_222: float = 0  # Rental at 10% (שכ"ד למגורים 10%)
    field_141: float = 0  # Dividends at 25% (דיבידנד)
    field_327: float = 0  # Interest at 25% (ריבית)
    field_139: float = 0  # Capital gains at 25% (רווח הון)


class DeductionFields(BaseModel):
    """חלק יב — Deductions (ניכויים)."""
    field_244: float = 0  # Insured income — registered (הכנסה מבוטחת)
    field_245: float = 0  # Insured income — spouse
    field_248: float = 0  # Employer pension — registered (הפרשות מעביד)
    field_249: float = 0  # Employer pension — spouse
    field_086: float = 0  # Life insurance premium — registered
    field_087: float = 0  # Life insurance premium — spouse
    field_040: float = 0  # NII deduction — registered
    field_036: float = 0  # NII deduction — spouse


class CreditFields(BaseModel):
    """חלק יג + יד — Credit points and tax credits."""
    field_011: float = 0  # Convalescence — registered (דמי הבראה)
    field_012: float = 0  # Convalescence — spouse
    credit_points_taxpayer: float = 0  # Total credit points — registered
    credit_points_spouse: float = 0  # Total credit points — spouse
    field_237: float = 0  # Donations — registered (תרומות)
    field_037: float = 0  # Donations — spouse
    field_045: float = 0  # Life insurance credit — registered
    field_046: float = 0  # Life insurance credit — spouse


class WithholdingFields(BaseModel):
    """חלק טו — Tax withheld at source (ניכויים במקור)."""
    field_042: float = 0  # Tax withheld from salary — total
    field_043: float = 0  # Tax withheld — spouse portion
    field_044: float = 0  # Tax withheld — other
    field_220: float = 0  # Rental tax paid (תשלום מס שכירות)


class TaxCalculation(BaseModel):
    """Computed tax breakdown."""
    # Gross tax components
    tax_regular_taxpayer: float = 0  # Tax at regular rates — registered
    tax_regular_spouse: float = 0  # Tax at regular rates — spouse
    tax_rental_10pct: float = 0  # 10% on rental income
    tax_dividend_25pct: float = 0  # 25% on dividends
    tax_interest_25pct: float = 0  # 25% on interest
    tax_capital_gains: float = 0  # Tax on capital gains
    surtax: float = 0  # מס נוסף (3% on income > threshold)
    gross_tax: float = 0  # Total gross tax

    # Credits
    credit_points_amount_taxpayer: float = 0  # ₪ value of credit points — registered
    credit_points_amount_spouse: float = 0  # ₪ value of credit points — spouse
    pension_credit_taxpayer: float = 0  # Pension contribution credit — registered
    pension_credit_spouse: float = 0  # Pension contribution credit — spouse
    donation_credit: float = 0  # Donation credit (35%)
    life_insurance_credit: float = 0  # Life insurance credit
    total_credits: float = 0  # Total credits

    # Net
    net_tax: float = 0  # After credits
    total_withheld: float = 0  # Total withheld at source
    total_paid: float = 0  # Total payments on account
    balance: float = 0  # Positive = owe, negative = refund


class Form1301Result(BaseModel):
    """Complete Form 1301 computation result."""
    tax_year: int
    income: IncomeFields = IncomeFields()
    deductions: DeductionFields = DeductionFields()
    credits: CreditFields = CreditFields()
    withholdings: WithholdingFields = WithholdingFields()
    calculation: TaxCalculation = TaxCalculation()
    # Source tracking
    source_documents: list[str] = []
    warnings: list[str] = []


class Form1301PreviewResponse(BaseModel):
    """API response for form preview."""
    result: Form1301Result
    reference_available: bool = False
