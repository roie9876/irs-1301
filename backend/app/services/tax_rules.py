"""Year-specific Israeli tax parameters for Form 1301 calculation."""

from dataclasses import dataclass


@dataclass
class TaxBracket:
    upper_limit: float  # Upper limit of bracket (use float('inf') for last)
    rate_personal: float  # Rate for personal labor income (יגיעה אישית)
    rate_other: float  # Rate for non-personal income (שלא מיגיעה אישית)


@dataclass
class TaxYearRules:
    year: int
    credit_point_value: float  # ₪ per credit point per year
    surtax_threshold: float  # מס נוסף threshold (per person in separate calc)
    surtax_rate: float  # 3% on all income above threshold
    surtax_capital_rate: float  # Extra surtax on capital income (2% from 2025, 0% before)
    brackets: list[TaxBracket]
    # Rental income
    rental_flat_rate: float  # 10% flat rate on residential rental
    rental_exemption_ceiling: float  # תקרת פטור שכ"ד (for exempt track)
    # Capital gains / dividends
    dividend_rate: float  # 25% or 30% depending on significant holder
    interest_rate: float  # 25%
    # Credit points
    resident_credit_points: float  # 2.25 for all residents
    woman_credit_points: float  # 0.5 extra for women
    # Standard deductions
    max_pension_deduction_pct: float  # Max % of income for pension deduction
    max_education_fund_deduction_employer_pct: float  # 7.5%
    max_education_fund_deduction_employee_pct: float  # 2.5%
    # Social insurance ceilings
    nii_max_insured_income: float  # Max monthly insured income for NII


TAX_RULES: dict[int, TaxYearRules] = {
    2022: TaxYearRules(
        year=2022,
        credit_point_value=2_676,
        surtax_threshold=663_240,
        surtax_rate=0.03,
        surtax_capital_rate=0.0,
        brackets=[
            TaxBracket(upper_limit=77_400, rate_personal=0.10, rate_other=0.31),
            TaxBracket(upper_limit=110_880, rate_personal=0.14, rate_other=0.31),
            TaxBracket(upper_limit=178_080, rate_personal=0.20, rate_other=0.31),
            TaxBracket(upper_limit=247_440, rate_personal=0.31, rate_other=0.31),
            TaxBracket(upper_limit=514_920, rate_personal=0.35, rate_other=0.35),
            TaxBracket(upper_limit=float("inf"), rate_personal=0.47, rate_other=0.47),
        ],
        rental_flat_rate=0.10,
        rental_exemption_ceiling=5_196,
        dividend_rate=0.25,
        interest_rate=0.25,
        resident_credit_points=2.25,
        woman_credit_points=0.5,
        max_pension_deduction_pct=0.07,
        max_education_fund_deduction_employer_pct=0.075,
        max_education_fund_deduction_employee_pct=0.025,
        nii_max_insured_income=45_075,
    ),
    2023: TaxYearRules(
        year=2023,
        credit_point_value=2_820,
        surtax_threshold=698_280,
        surtax_rate=0.03,
        surtax_capital_rate=0.0,
        brackets=[
            TaxBracket(upper_limit=81_480, rate_personal=0.10, rate_other=0.31),
            TaxBracket(upper_limit=116_760, rate_personal=0.14, rate_other=0.31),
            TaxBracket(upper_limit=187_440, rate_personal=0.20, rate_other=0.31),
            TaxBracket(upper_limit=260_520, rate_personal=0.31, rate_other=0.31),
            TaxBracket(upper_limit=542_160, rate_personal=0.35, rate_other=0.35),
            TaxBracket(upper_limit=float("inf"), rate_personal=0.47, rate_other=0.47),
        ],
        rental_flat_rate=0.10,
        rental_exemption_ceiling=5_471,
        dividend_rate=0.25,
        interest_rate=0.25,
        resident_credit_points=2.25,
        woman_credit_points=0.5,
        max_pension_deduction_pct=0.07,
        max_education_fund_deduction_employer_pct=0.075,
        max_education_fund_deduction_employee_pct=0.025,
        nii_max_insured_income=47_465,
    ),
    2024: TaxYearRules(
        year=2024,
        credit_point_value=2_904,
        surtax_threshold=721_560,
        surtax_rate=0.03,
        surtax_capital_rate=0.0,
        brackets=[
            TaxBracket(upper_limit=84_120, rate_personal=0.10, rate_other=0.31),
            TaxBracket(upper_limit=120_720, rate_personal=0.14, rate_other=0.31),
            TaxBracket(upper_limit=193_800, rate_personal=0.20, rate_other=0.31),
            TaxBracket(upper_limit=269_280, rate_personal=0.31, rate_other=0.31),
            TaxBracket(upper_limit=560_280, rate_personal=0.35, rate_other=0.35),
            TaxBracket(upper_limit=float("inf"), rate_personal=0.47, rate_other=0.47),
        ],
        rental_flat_rate=0.10,
        rental_exemption_ceiling=5_654,
        dividend_rate=0.25,
        interest_rate=0.25,
        resident_credit_points=2.25,
        woman_credit_points=0.5,
        max_pension_deduction_pct=0.07,
        max_education_fund_deduction_employer_pct=0.075,
        max_education_fund_deduction_employee_pct=0.025,
        nii_max_insured_income=49_030,
    ),
    2025: TaxYearRules(
        year=2025,
        credit_point_value=2_904,  # Frozen at 2024 level
        surtax_threshold=721_560,  # Frozen at 2024 level
        surtax_rate=0.03,
        surtax_capital_rate=0.02,  # NEW: 2% extra on capital income above threshold
        brackets=[
            TaxBracket(upper_limit=84_120, rate_personal=0.10, rate_other=0.31),
            TaxBracket(upper_limit=120_720, rate_personal=0.14, rate_other=0.31),
            TaxBracket(upper_limit=193_800, rate_personal=0.20, rate_other=0.31),
            TaxBracket(upper_limit=269_280, rate_personal=0.31, rate_other=0.31),
            TaxBracket(upper_limit=560_280, rate_personal=0.35, rate_other=0.35),
            TaxBracket(upper_limit=float("inf"), rate_personal=0.47, rate_other=0.47),
        ],
        rental_flat_rate=0.10,
        rental_exemption_ceiling=5_654,  # Frozen at 2024 level
        dividend_rate=0.25,
        interest_rate=0.25,
        resident_credit_points=2.25,
        woman_credit_points=0.5,
        max_pension_deduction_pct=0.07,
        max_education_fund_deduction_employer_pct=0.075,
        max_education_fund_deduction_employee_pct=0.025,
        nii_max_insured_income=49_030,  # Same as 2024
    ),
}


def get_rules(year: int) -> TaxYearRules:
    if year not in TAX_RULES:
        raise ValueError(f"Tax rules for year {year} not available. Supported: {sorted(TAX_RULES.keys())}")
    return TAX_RULES[year]


def compute_progressive_tax(taxable_income: float, rules: TaxYearRules, personal_labor: bool = True) -> float:
    """Compute progressive tax on income using year-specific brackets.

    Args:
        taxable_income: Annual taxable income in ₪
        rules: Tax year rules with brackets
        personal_labor: True for יגיעה אישית (10% start), False for other (31% start)
    """
    if taxable_income <= 0:
        return 0.0

    tax = 0.0
    prev_limit = 0.0

    for bracket in rules.brackets:
        if taxable_income <= prev_limit:
            break

        bracket_income = min(taxable_income, bracket.upper_limit) - prev_limit
        if bracket_income <= 0:
            prev_limit = bracket.upper_limit
            continue

        rate = bracket.rate_personal if personal_labor else bracket.rate_other
        tax += bracket_income * rate
        prev_limit = bracket.upper_limit

    return round(tax)


def compute_surtax(
    total_taxable_income: float,
    rules: TaxYearRules,
    capital_income: float = 0,
) -> float:
    """Compute מס יסף / מס נוסף (surtax on high income).

    Key rules:
    - Applied PER PERSON (not joint) when using חישוב נפרד
    - 3% on ALL taxable income above threshold (salary + rental + dividends + etc.)
    - Definition: "הכנסה חייבת למעט סכום אינפלציוני ולרבות שבח"
    - Includes special-rate income (dividends, interest, rental, capital gains)
    - From 2025: additional 2% on CAPITAL income above threshold
    """
    surtax = 0.0

    if total_taxable_income > rules.surtax_threshold:
        excess = total_taxable_income - rules.surtax_threshold
        surtax += excess * rules.surtax_rate

    # From 2025: extra 2% on capital income above threshold
    if rules.surtax_capital_rate > 0 and capital_income > 0:
        # Capital surtax applies on capital income portion above threshold
        capital_above = max(0, min(capital_income, total_taxable_income - rules.surtax_threshold))
        surtax += capital_above * rules.surtax_capital_rate

    return round(surtax)
