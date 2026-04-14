"""Year-specific Israeli tax parameters for Form 1301 calculation."""

import json
from dataclasses import dataclass
from pathlib import Path


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
    # Pension credit (section 45a)
    pension_credit_income_ceiling: float  # Max annual insured income for 45a credit
    # Credit qualifying income ceiling (section 45b — "הכנסה מזכה")
    credit_qualifying_income_ceiling: float  # For combined pension+insurance credit path
    # Social insurance ceilings
    nii_max_insured_income: float  # Max monthly insured income for NII
    # Shift work credit
    shift_work_employer_income_ceiling: float
    shift_work_max_credit: float


TAX_RULES_JSON = Path(__file__).resolve().parent.parent.parent / "tax_rules.json"


def _load_rules_from_json(path: Path) -> dict[int, TaxYearRules]:
    """Load tax rules from a JSON config file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    rules: dict[int, TaxYearRules] = {}
    for year_str, cfg in data.items():
        if year_str.startswith("_"):
            continue  # skip comments
        year = int(year_str)
        brackets = [
            TaxBracket(
                upper_limit=float(b["upper_limit"]),
                rate_personal=b["rate_personal"],
                rate_other=b["rate_other"],
            )
            for b in cfg["brackets"]
        ]
        rules[year] = TaxYearRules(
            year=year,
            credit_point_value=cfg["credit_point_value"],
            surtax_threshold=cfg["surtax_threshold"],
            surtax_rate=cfg["surtax_rate"],
            surtax_capital_rate=cfg.get("surtax_capital_rate", 0.0),
            brackets=brackets,
            rental_flat_rate=cfg["rental_flat_rate"],
            rental_exemption_ceiling=cfg["rental_exemption_ceiling"],
            dividend_rate=cfg["dividend_rate"],
            interest_rate=cfg["interest_rate"],
            resident_credit_points=cfg["resident_credit_points"],
            woman_credit_points=cfg["woman_credit_points"],
            max_pension_deduction_pct=cfg["max_pension_deduction_pct"],
            max_education_fund_deduction_employer_pct=cfg["max_education_fund_deduction_employer_pct"],
            max_education_fund_deduction_employee_pct=cfg["max_education_fund_deduction_employee_pct"],
            pension_credit_income_ceiling=cfg["pension_credit_income_ceiling"],
            credit_qualifying_income_ceiling=cfg["credit_qualifying_income_ceiling"],
            nii_max_insured_income=cfg["nii_max_insured_income"],
            shift_work_employer_income_ceiling=cfg["shift_work_employer_income_ceiling"],
            shift_work_max_credit=cfg["shift_work_max_credit"],
        )
    return rules


# Load from JSON config file
TAX_RULES: dict[int, TaxYearRules] = _load_rules_from_json(TAX_RULES_JSON)


def reload_rules() -> None:
    """Reload tax rules from disk (call after editing tax_rules.json)."""
    global TAX_RULES
    TAX_RULES.clear()
    TAX_RULES.update(_load_rules_from_json(TAX_RULES_JSON))


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

    return int(surtax)
