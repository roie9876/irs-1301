"""Pydantic models for Form 1301 calculation results.

Field codes match the official Israeli Tax Authority Form 1301.
"""

from pydantic import BaseModel


class IncomeFields(BaseModel):
    """חלק ג — הכנסות מיגיעה אישית (סעיפים 1-7)."""
    # סעיף 1: מעסק או משלח יד
    field_150: float = 0  # עסק/משלח יד — רשום
    field_170: float = 0  # עסק/משלח יד — בן/בת זוג
    # סעיף 2א: תקבולי ביט"ל כעצמאי
    field_250: float = 0  # ביט"ל עצמאי — רשום
    field_270: float = 0  # ביט"ל עצמאי — בן/בת זוג
    # סעיף 2ב: תקבולי ביט"ל כשכיר
    field_194: float = 0  # ביט"ל שכיר — רשום
    field_196: float = 0  # ביט"ל שכיר — בן/בת זוג
    # סעיף 3: ממשכורת
    field_158: float = 0  # משכורת — רשום
    field_172: float = 0  # משכורת — בן/בת זוג
    # סעיף 4: עבודה במשמרות
    field_069: float = 0  # משמרות — רשום
    field_068: float = 0  # משמרות — בן/בת זוג
    # סעיף 5: מענקי פרישה וקצבאות
    field_258: float = 0  # מענקי פרישה/קצבאות — רשום
    field_272: float = 0  # מענקי פרישה/קצבאות — בן/בת זוג


class OtherIncomeFields(BaseModel):
    """חלק ד — הכנסות בשיעורי מס רגילים (סעיפים 8-11)."""
    # סעיף 8: מנכס בית
    field_059: float = 0  # נכס בית — רשום
    field_201: float = 0  # נכס בית — בן/בת זוג
    # סעיף 11: הכנסות אחרות שאינן מיגיעה אישית
    field_167: float = 0  # אחרות — רשום
    field_205: float = 0  # אחרות — בן/בת זוג
    field_305: float = 0  # אחרות — שני בני הזוג


class SpecialRateIncomeFields(BaseModel):
    """חלק ה — הכנסות בשיעורי מס מיוחדים (סעיפים 12-32)."""
    # סעיף 13: ריבית ני"ע, קופ"ג, דיבידנד מפעל מאושר — 15%
    field_060: float = 0  # 15% — רשום
    field_211: float = 0  # 15% — בן/בת זוג
    # סעיף 14: ריבית ני"ע, קופ"ג — 20%
    field_067: float = 0  # 20% — רשום
    field_228: float = 0  # 20% — בן/בת זוג
    # סעיף 15: ריבית ני"ע, קופ"ג — 25%
    field_157: float = 0  # 25% — רשום
    field_257: float = 0  # 25% — בן/בת זוג
    # סעיף 16: דיבידנד מפעל מועדף/מאושר — 20%
    field_173: float = 0  # 20% — רשום
    field_275: float = 0  # 20% — בן/בת זוג
    # סעיף 17: דיבידנד — 25%
    field_141: float = 0  # 25% — רשום
    field_241: float = 0  # 25% — בן/בת זוג
    # סעיף 18: דיבידנד בעל מניות מהותי — 30%
    field_055: float = 0  # 30% — רשום
    field_212: float = 0  # 30% — בן/בת זוג
    # סעיף 21: ריבית פיקדונות/חסכונות — 15%
    field_078: float = 0  # 15% — רשום
    field_217: float = 0  # 15% — בן/בת זוג
    # סעיף 22: ריבית פיקדונות/חסכונות — 20%
    field_126: float = 0  # 20% — רשום
    field_226: float = 0  # 20% — בן/בת זוג
    # סעיף 23: ריבית פיקדונות/חסכונות — 25%
    field_142: float = 0  # 25% — רשום
    field_242: float = 0  # 25% — בן/בת זוג
    # סעיף 24: שכ"ד למגורים — 10%
    field_222: float = 0  # 10% — רשום
    field_284: float = 0  # 10% — בן/בת זוג
    # סעיף 25: שכ"ד מחו"ל — 15%
    field_225: float = 0  # 15% — רשום
    field_285: float = 0  # 15% — בן/בת זוג
    # סעיף 26: הימורים, הגרלות, פרסים — 35%
    field_227: float = 0  # 35% — רשום
    field_286: float = 0  # 35% — בן/בת זוג
    # סעיף 27: אנרגיות מתחדשות — 31%
    field_335: float = 0  # 31% — רשום
    field_337: float = 0  # 31% — בן/בת זוג
    # סעיף 28: חלוקה לחיסכון פנסיוני — 20%
    field_288: float = 0  # 20% — רשום
    field_338: float = 0  # 20% — בן/בת זוג
    # סעיף 29: משיכה שלא כדין מקופ"ג — 35%
    field_213: float = 0  # 35% — רשום
    field_313: float = 0  # 35% — בן/בת זוג


class CapitalGainsFields(BaseModel):
    """חלק ח — רווח הון ושבח מקרקעין."""
    field_054: int = 0    # מספר טופסי רווח הון שצורפו
    field_056: float = 0  # סכום מכירות רווח הון (לא כולל ני"ע)
    field_256: float = 0  # סכום מכירות מני"ע סחירים
    field_139: float = 0  # רווח הון 25% — חישוב


class ExemptIncomeFields(BaseModel):
    """חלק י — הכנסות פטורות ובלתי חייבות במס."""
    field_109: float = 0  # פטור נכות 9(5) — רשום
    field_309: float = 0  # פטור נכות 9(5) — בן/בת זוג
    field_332: float = 0  # פטור שכ"ד למגורים
    field_209: float = 0  # סה"כ פטורים


class DeductionFields(BaseModel):
    """חלק יב — ניכויים אישיים (סעיפים 49-60)."""
    # הוצאות הפקת הכנסה (דמי רו"ח)
    production_expenses_taxpayer: float = 0
    production_expenses_spouse: float = 0
    # סעיף 49: ביטוח אבדן כושר עבודה — עצמאי
    field_112: float = 0  # אבדן כושר עצמאי — רשום
    field_113: float = 0  # אבדן כושר עצמאי — בן/בת זוג
    # סעיף 50: ביטוח אבדן כושר עבודה — שכיר
    field_206: float = 0  # אבדן כושר שכיר — רשום
    field_207: float = 0  # אבדן כושר שכיר — בן/בת זוג
    # סעיף 51: קרן השתלמות לעצמאי
    field_136: float = 0  # קרן השתלמות עצמאי — רשום
    field_137: float = 0  # קרן השתלמות עצמאי — בן/בת זוג
    # סעיף 52: משכורת לקרן השתלמות (מ-106)
    field_218: float = 0  # קרן השתלמות שכיר — רשום
    field_219: float = 0  # קרן השתלמות שכיר — בן/בת זוג
    # סעיף 53: קופ"ג כעמית עצמאי
    field_135: float = 0  # קופ"ג עצמאי — רשום
    field_180: float = 0  # קופ"ג עצמאי — בן/בת זוג
    # סעיף 54: דמי ביט"ל על הכנסה שאינה עבודה
    field_030: float = 0  # ביט"ל לא-עבודה — רשום
    field_089: float = 0  # ביט"ל לא-עבודה — בן/בת זוג
    # סעיף 58: הכנסה מבוטחת (מ-106)
    field_244: float = 0  # הכנסה מבוטחת — רשום
    field_245: float = 0  # הכנסה מבוטחת — בן/בת זוג
    # סעיף 59: הפקדות מעביד לקופ"ג (מ-106)
    field_248: float = 0  # הפקדות מעביד — רשום
    field_249: float = 0  # הפקדות מעביד — בן/בת זוג
    # סעיף 60: הפחתת דמי הבראה (מ-106)
    field_011: float = 0  # דמי הבראה — רשום
    field_012: float = 0  # דמי הבראה — בן/בת זוג


class CreditPointsFields(BaseModel):
    """חלק יג — נקודות זיכוי (סעיפים 61-72)."""
    # סעיף 61: תושב
    field_020: float = 0  # נקודות תושב — רשום
    # סעיף 62: בן/בת זוג
    field_021: float = 0  # נקודות בן/בת זוג
    # סעיף 64: ילדים
    field_260: float = 0  # ילדים — רשום
    field_262: float = 0  # ילדים — בן/בת זוג
    # סעיף 65: הורה חד-הורי
    field_026: float = 0  # הורה חד-הורי
    # סעיף 71: חייל משוחרר
    field_024: float = 0  # חייל — רשום (חודשים)
    field_124: float = 0  # חייל — בן/בת זוג (חודשים)
    # סעיף 72: תואר אקדמאי
    field_181: str = ""   # קוד לימודים — רשום
    field_182: str = ""   # קוד לימודים — בן/בת זוג
    # Totals (computed)
    credit_points_taxpayer: float = 0
    credit_points_spouse: float = 0


class TaxCreditFields(BaseModel):
    """חלק יד — זיכויים מהמס (סעיפים 73-82)."""
    # סעיף 73: ביטוח חיים
    field_036: float = 0  # ביטוח חיים — רשום
    field_081: float = 0  # ביטוח חיים — בן/בת זוג
    # סעיף 74: ביטוח קצבת שאירים
    field_140: float = 0  # שאירים — רשום
    field_240: float = 0  # שאירים — בן/בת זוג
    # סעיף 75: קצבה כעמית שכיר
    field_045: float = 0  # עמית שכיר — רשום
    field_086: float = 0  # עמית שכיר — בן/בת זוג
    # סעיף 76: קצבה כעמית עצמאי
    field_268: float = 0  # עמית עצמאי — רשום
    field_269: float = 0  # עמית עצמאי — בן/בת זוג
    # סעיף 77: החזקת בן משפחה במוסד
    field_132: float = 0  # מוסד — רשום
    field_232: float = 0  # מוסד — בן/בת זוג
    # סעיף 78: תרומות
    field_037: float = 0  # תרומות ישראל — רשום
    field_237: float = 0  # תרומות ישראל — בן/בת זוג
    field_046: float = 0  # תרומות ארה"ב — רשום
    field_048: float = 0  # תרומות ארה"ב — בן/בת זוג
    # סעיף 80: השקעות מו"פ
    field_155: float = 0  # מו"פ — רשום
    field_199: float = 0  # מו"פ — בן/בת זוג
    # סעיף 81: תושב אילת
    field_183: float = 0  # אילת — רשום (הכנסה)


class WithholdingFields(BaseModel):
    """חלק טו — ניכויים במקור ומקדמות (סעיפים 83-89)."""
    # סעיף 84: מס שנוכה ממשכורת (מ-106)
    field_042: float = 0  # מס ממשכורת — רשום
    # סעיף 85: ניכוי מריבית (פיקדונות, סעיפים 21-23)
    field_043: float = 0  # מס מריבית
    # סעיף 87: ניכוי מהכנסות אחרות
    field_040: float = 0  # מס מהכנסות אחרות
    # סעיף 88: מס שבח
    field_041: float = 0  # מס שבח
    # שכירות
    field_220: float = 0  # מס שכירות ששולם
    # מקדמות מדוח שנתי (ESOP)
    field_tax_advance: float = 0


class TaxCalculation(BaseModel):
    """Computed tax breakdown."""
    # Progressive tax (parts ג + ד)
    tax_regular_taxpayer: float = 0
    tax_regular_spouse: float = 0
    # Special-rate taxes (part ה)
    tax_15pct: float = 0   # סעיפים 13, 21, 25
    tax_20pct: float = 0   # סעיפים 14, 16, 22, 28
    tax_25pct: float = 0   # סעיפים 15, 17, 23 — dividends + interest
    tax_30pct: float = 0   # סעיף 18 — significant-holder dividends
    tax_31pct: float = 0   # סעיף 27 — renewable energy
    tax_35pct: float = 0   # סעיפים 26, 29 — gambling, unauthorized withdrawal
    tax_rental_10pct: float = 0  # סעיף 24
    tax_capital_gains: float = 0  # חלק ח
    surtax: float = 0  # מס יסף 3%
    gross_tax: float = 0

    # Credits
    credit_points_amount_taxpayer: float = 0
    credit_points_amount_spouse: float = 0
    pension_employee_credit_taxpayer: float = 0  # סעיף 75
    pension_employee_credit_spouse: float = 0
    life_insurance_credit_taxpayer: float = 0  # סעיף 73
    life_insurance_credit_spouse: float = 0
    donation_credit: float = 0
    total_credits_taxpayer: float = 0
    total_credits_spouse: float = 0
    total_credits: float = 0

    # Per-person gross tax (for separate-calculation capping)
    gross_tax_taxpayer: float = 0
    gross_tax_spouse: float = 0

    # Net
    net_tax: float = 0
    total_withheld: float = 0
    total_paid: float = 0
    balance: float = 0
    interest_cpi_adjustment: float = 0
    balance_after_interest: float = 0


class Form1301Result(BaseModel):
    """Complete Form 1301 computation result."""
    tax_year: int
    income: IncomeFields = IncomeFields()
    other_income: OtherIncomeFields = OtherIncomeFields()
    special_rate: SpecialRateIncomeFields = SpecialRateIncomeFields()
    capital_gains: CapitalGainsFields = CapitalGainsFields()
    exempt: ExemptIncomeFields = ExemptIncomeFields()
    deductions: DeductionFields = DeductionFields()
    credit_points: CreditPointsFields = CreditPointsFields()
    tax_credits: TaxCreditFields = TaxCreditFields()
    withholdings: WithholdingFields = WithholdingFields()
    calculation: TaxCalculation = TaxCalculation()
    # Source tracking
    source_documents: list[str] = []
    warnings: list[str] = []


class Form1301PreviewResponse(BaseModel):
    """API response for form preview."""
    result: Form1301Result
    reference_available: bool = False
