"""Form 1301 calculator — builds the tax return from source documents."""

import json
from datetime import date
from pathlib import Path

from app.schemas.documents import (
    EXTRACTION_MODELS,
    DocumentInfo,
    FieldValue,
    Form106Extraction,
)
from app.schemas.form1301 import (
    CapitalGainsFields,
    CreditPointsFields,
    DeductionFields,
    ExemptIncomeFields,
    Form1301Result,
    IncomeFields,
    OtherIncomeFields,
    SpecialRateIncomeFields,
    TaxCalculation,
    TaxCreditFields,
    WithholdingFields,
)
from app.services.tax_rules import compute_progressive_tax, compute_surtax, get_rules

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "user_data" / "documents"

SIDECAR_SUFFIX = ".doc.json"


def _fv(field) -> float:
    """Extract numeric value from FieldValue or dict, defaulting to 0."""
    if isinstance(field, FieldValue):
        val = field.value
    elif isinstance(field, dict):
        val = field.get("value")
    else:
        val = field
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _monthly_immigrant_credit_points(status: str, arrival_date: date | None, tax_year: int) -> float:
    """Compute annual immigrant credit points for a given tax year."""
    if status not in {"new_immigrant", "veteran_returning_resident"} or arrival_date is None:
        return 0.0

    pre_2022_schedule = (
        (18, 1 / 4),
        (12, 1 / 6),
        (12, 1 / 12),
    )
    post_2022_schedule = (
        (12, 1 / 12),
        (18, 1 / 4),
        (12, 1 / 6),
        (12, 1 / 12),
    )
    schedule = post_2022_schedule if arrival_date >= date(2022, 1, 1) else pre_2022_schedule

    total_points = 0.0
    for month_index in range(1, 13):
        current_month = date(tax_year, month_index, 1)
        if current_month < date(arrival_date.year, arrival_date.month, 1):
            continue

        months_since_arrival = (current_month.year - arrival_date.year) * 12 + (current_month.month - arrival_date.month)
        lower_bound = 0
        for duration, monthly_points in schedule:
            upper_bound = lower_bound + duration
            if lower_bound <= months_since_arrival < upper_bound:
                total_points += monthly_points
                break
            lower_bound = upper_bound

    return total_points


def _parse_year_month(value: str) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.split("-")
    if len(parts) != 2:
        return None
    try:
        year = int(parts[0])
        month = int(parts[1])
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None
    return year, month


def _compute_shift_work_credit(shift_income: float, employer_income: float, rules) -> float:
    if shift_income <= 0:
        return 0.0
    non_shift_income = max(0.0, employer_income - shift_income)
    eligible_shift_income = max(0.0, rules.shift_work_employer_income_ceiling - non_shift_income)
    qualifying_shift_income = min(shift_income, eligible_shift_income)
    return round(min(qualifying_shift_income * 0.15, rules.shift_work_max_credit))


def _compute_discharged_soldier_credit_points(release_year_month: str, service_months: int, tax_year: int) -> float:
    parsed = _parse_year_month(release_year_month)
    if parsed is None or service_months <= 0:
        return 0.0

    release_year, release_month = parsed
    if tax_year < release_year or tax_year > release_year + 3:
        return 0.0

    months_in_tax_year = 12
    if tax_year == release_year:
        months_in_tax_year = max(0, 12 - release_month)
    elif tax_year == release_year + 3:
        months_in_tax_year = release_month

    monthly_points = (1 / 6) if service_months >= 23 else (1 / 12)
    return months_in_tax_year * monthly_points


def _compute_academic_credit_points(code: str, completion_year: int, study_years: int, tax_year: int) -> float:
    if not code or completion_year <= 0 or study_years <= 0:
        return 0.0
    years_since_completion = tax_year - completion_year
    if years_since_completion <= 0:
        return 0.0

    if code == "1":
        return 1.0 if years_since_completion <= min(study_years, 3) else 0.0
    if code == "2":
        return 0.5 if years_since_completion <= min(study_years, 2) else 0.0
    if code == "3":
        if years_since_completion <= 3:
            return 1.0
        if years_since_completion <= 5:
            return 0.5
        return 0.0
    if code == "12":
        return 2.5 if years_since_completion == 1 else 0.0
    return 0.0


def _compute_spouse_helper_credit_points(
    has_spouse_for_tax: bool,
    has_joint_income_source: bool,
    spouse_assists_income: bool,
    has_children: bool,
) -> float:
    if not (has_spouse_for_tax and has_joint_income_source and spouse_assists_income):
        return 0.0
    return 1.75 if has_children else 1.5


def load_documents_for_year(year: int) -> list[DocumentInfo]:
    """Load all uploaded documents, filtering to those matching the tax year."""
    if not DOCUMENTS_DIR.exists():
        return []

    documents: list[DocumentInfo] = []
    # Check both new and legacy sidecar files
    paths = list(DOCUMENTS_DIR.glob(f"*{SIDECAR_SUFFIX}"))
    paths += [p for p in DOCUMENTS_DIR.glob("*.106.json") if not p.name.endswith(SIDECAR_SUFFIX)]

    for sidecar_path in sorted(set(paths)):
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            doc_type = data.get("document_type", "form_106")
            extracted = data["extracted"]

            # Check year from extracted data
            doc_year = _fv(extracted.get("tax_year", {}))
            if doc_year and int(doc_year) != year:
                continue

            documents.append(DocumentInfo(
                doc_id=data["doc_id"],
                original_filename=data["original_filename"],
                document_type=doc_type,
                extracted=extracted,
                user_corrected=data.get("user_corrected", False),
            ))
        except (json.JSONDecodeError, KeyError):
            continue

    return documents

def classify_documents(
    documents: list[DocumentInfo],
    has_spouse_hint: bool = False,
) -> tuple[list[DocumentInfo], list[DocumentInfo], list[str]]:
    """Split Form 106 documents into taxpayer (רשום) and spouse (בן/בת זוג) groups.

    Heuristic: if filename explicitly marks spouse, classify as spouse.
    Otherwise keep the document under the registered taxpayer bucket.
    """
    taxpayer_docs: list[DocumentInfo] = []
    spouse_docs: list[DocumentInfo] = []
    warnings: list[str] = []

    # Only classify Form 106 documents
    form106_docs = [d for d in documents if d.document_type == "form_106"]
    unlabeled_docs: list[DocumentInfo] = []

    for doc in form106_docs:
        filename_lower = doc.original_filename.lower()
        is_spouse = any([
            "spouse" in filename_lower,
            "בת זוג" in filename_lower,
            "בן זוג" in filename_lower,
        ])

        if is_spouse:
            spouse_docs.append(doc)
        else:
            unlabeled_docs.append(doc)

    if spouse_docs:
        taxpayer_docs.extend(unlabeled_docs)
        return taxpayer_docs, spouse_docs, warnings

    if has_spouse_hint and len(unlabeled_docs) > 1:
        ordered_docs = sorted(
            unlabeled_docs,
            key=lambda doc: _fv(doc.extracted.get("gross_salary", {})),
            reverse=True,
        )
        taxpayer_docs.append(ordered_docs[0])
        spouse_docs.extend(ordered_docs[1:])
        warnings.append("סיווג טפסי 106 בין בני הזוג בוצע לפי היקף שכר, כי שם הקובץ לא סימן במפורש בן/בת זוג")
        return taxpayer_docs, spouse_docs, warnings

    taxpayer_docs.extend(unlabeled_docs)

    return taxpayer_docs, spouse_docs, warnings


def aggregate_form106(docs: list[DocumentInfo]) -> dict[str, float]:
    """Aggregate Form 106 fields across multiple employers."""
    totals: dict[str, float] = {
        "gross_salary": 0,
        "tax_withheld": 0,
        "pension_employer": 0,
        "pension_employee": 0,
        "insured_income": 0,
        "convalescence_pay": 0,
        "education_fund": 0,
        "national_insurance": 0,
        "health_insurance": 0,
        "donations": 0,
        "life_insurance": 0,
        "capital_gains_102": 0,
    }

    for doc in docs:
        ext = doc.extracted
        totals["gross_salary"] += _fv(ext.get("gross_salary", {}))
        totals["tax_withheld"] += _fv(ext.get("tax_withheld", {}))
        totals["pension_employer"] += _fv(ext.get("pension_employer", {}))
        totals["pension_employee"] += _fv(ext.get("pension_employee", {}))
        totals["insured_income"] += _fv(ext.get("insured_income", {}))
        totals["convalescence_pay"] += _fv(ext.get("convalescence_pay", {}))
        totals["education_fund"] += _fv(ext.get("education_fund", {}))
        totals["national_insurance"] += _fv(ext.get("national_insurance", {}))
        totals["health_insurance"] += _fv(ext.get("health_insurance", {}))
        totals["donations"] += _fv(ext.get("donations", {}))
        totals["life_insurance"] += _fv(ext.get("life_insurance", {}))
        totals["capital_gains_102"] += _fv(ext.get("capital_gains_102", {}))

    return totals


def aggregate_form867(documents: list[DocumentInfo]) -> dict[str, float]:
    """Aggregate Form 867 data (dividends/interest) from all 867 documents."""
    totals: dict[str, float] = {
        "dividend_income": 0,
        "dividend_tax_withheld": 0,
        "foreign_tax_paid": 0,
        "interest_income": 0,
        "interest_tax_withheld": 0,
    }

    for doc in documents:
        if doc.document_type != "form_867":
            continue
        ext = doc.extracted
        totals["dividend_income"] += _fv(ext.get("dividend_income", {}))
        totals["dividend_tax_withheld"] += _fv(ext.get("dividend_tax_withheld", {}))
        totals["foreign_tax_paid"] += _fv(ext.get("foreign_tax_paid", {}))
        totals["interest_income"] += _fv(ext.get("interest_income", {}))
        totals["interest_tax_withheld"] += _fv(ext.get("interest_tax_withheld", {}))

    return totals


def aggregate_rental_payments(documents: list[DocumentInfo]) -> float:
    """Sum rental tax payments from all rental payment confirmation documents."""
    total = 0.0
    for doc in documents:
        if doc.document_type != "rental_payment":
            continue
        total += _fv(doc.extracted.get("payment_amount", {}))
    return total


def aggregate_receipts(documents: list[DocumentInfo]) -> float:
    """Sum CPA fee receipts (deductible expenses)."""
    total = 0.0
    for doc in documents:
        if doc.document_type != "receipt":
            continue
        total += _fv(doc.extracted.get("total_amount", {}))
    return total


def aggregate_rental_excel(documents: list[DocumentInfo]) -> tuple[float, float]:
    """Extract total rental income and tax from rental_excel documents.

    Returns (total_annual_income, tax_amount).
    """
    income = 0.0
    tax = 0.0
    for doc in documents:
        if doc.document_type != "rental_excel":
            continue
        income += _fv(doc.extracted.get("total_annual_income", {}))
        tax += _fv(doc.extracted.get("tax_amount", {}))
    return income, tax


def aggregate_annual_summary(documents: list[DocumentInfo]) -> dict[str, float]:
    """Aggregate Annual Sales Report (ESOP) data.

    Returns capital_income (field 141) and tax_advance_payment.
    The ordinary_income is already included in the Form 106, so we don't add it.
    """
    totals: dict[str, float] = {
        "capital_income": 0,
        "tax_advance_payment": 0,
    }
    for doc in documents:
        if doc.document_type != "annual_summary":
            continue
        totals["capital_income"] += _fv(doc.extracted.get("capital_income_ils", {}))
        totals["tax_advance_payment"] += _fv(doc.extracted.get("tax_advance_payment", {}))
    return totals


def compute_pension_employee_credit(pension_employee: float, insured_income: float, rules) -> float:
    """Compute section 45a credit for employee pension deposits (section 75).

    Formula: 35% × min(deposits, 7% × min(insured_income, ceiling))
    For salaried employees, the ceiling is year-specific (average wage × 12).
    """
    max_qualifying = rules.max_pension_deduction_pct * min(insured_income, rules.pension_credit_income_ceiling)
    qualifying = min(pension_employee, max_qualifying)
    return round(qualifying * 0.35)


def compute_children_credit_points(
    children_birth_years: list[int],
    tax_year: int,
    is_woman: bool,
) -> float:
    """Compute credit points for children based on birth years.

    Israeli tax law (section 40/60) — married couple table:
      Birth year:  1.5 each parent
      Ages 1-5:    2.5 each parent
      Ages 6-12:   woman 2, man 1
      Ages 13-17:  woman 1, man 0   (until 2023)
                   woman 2, man 1   (from 2024 — law amendment)
      Age 18:      woman 0.5, man 0
    """
    points = 0.0
    for birth_year in children_birth_years:
        age = tax_year - birth_year
        if age == 0:
            points += 1.5
        elif 1 <= age <= 5:
            points += 2.5
        elif 6 <= age <= 12:
            points += 2.0 if is_woman else 1.0
        elif 13 <= age <= 17:
            if tax_year >= 2024:
                points += 2.0 if is_woman else 1.0
            else:
                points += 1.0 if is_woman else 0.0
        elif age == 18:
            points += 0.5 if is_woman else 0.0
    return points


def aggregate_id_supplement(documents: list[DocumentInfo]) -> dict:
    """Extract children info and gender from ID supplement documents."""
    result: dict = {
        "children_birth_years": [],
        "holder_gender": "",
        "holder_name": "",
        "spouse_name": "",
    }

    for doc in documents:
        if doc.document_type != "id_supplement":
            continue
        ext = doc.extracted
        children = ext.get("children", [])
        for child in children:
            if isinstance(child, dict):
                by = child.get("birth_year", 0)
                if isinstance(by, int) and 1990 < by < 2030:
                    result["children_birth_years"].append(by)
        gender_field = ext.get("holder_gender", {})
        if isinstance(gender_field, dict):
            result["holder_gender"] = str(gender_field.get("value", "")).lower()
        name_field = ext.get("holder_name", {})
        if isinstance(name_field, dict):
            result["holder_name"] = str(name_field.get("value", ""))
        sp_field = ext.get("spouse_name", {})
        if isinstance(sp_field, dict):
            result["spouse_name"] = str(sp_field.get("value", ""))

    return result


def compute_form1301(
    year: int,
    marital_status: str = "",
    has_joint_income_source: bool = False,
    spouse_assists_income: bool = False,
    immigrant_taxpayer_status: str = "",
    immigrant_taxpayer_arrival_date: str = "",
    immigrant_spouse_status: str = "",
    immigrant_spouse_arrival_date: str = "",
    # חלק ג — הכנסות מיגיעה אישית
    business_income_taxpayer: float = 0,
    business_income_spouse: float = 0,
    nii_self_employed_taxpayer: float = 0,
    nii_self_employed_spouse: float = 0,
    nii_employee_taxpayer: float = 0,
    nii_employee_spouse: float = 0,
    shift_work_taxpayer: float = 0,
    shift_work_spouse: float = 0,
    retirement_grants_taxpayer: float = 0,
    retirement_grants_spouse: float = 0,
    # חלק ד — הכנסות בשיעורי מס רגילים
    real_estate_income_taxpayer: float = 0,
    real_estate_income_spouse: float = 0,
    other_income_taxpayer: float = 0,
    other_income_spouse: float = 0,
    other_income_joint: float = 0,
    # חלק ה — הכנסות בשיעורי מס מיוחדים
    interest_securities_15_taxpayer: float = 0,
    interest_securities_15_spouse: float = 0,
    interest_securities_20_taxpayer: float = 0,
    interest_securities_20_spouse: float = 0,
    interest_securities_25_taxpayer: float = 0,
    interest_securities_25_spouse: float = 0,
    dividend_preferred_20_taxpayer: float = 0,
    dividend_preferred_20_spouse: float = 0,
    dividend_25_taxpayer: float = 0,
    dividend_25_spouse: float = 0,
    dividend_significant_30_taxpayer: float = 0,
    dividend_significant_30_spouse: float = 0,
    interest_deposits_15_taxpayer: float = 0,
    interest_deposits_15_spouse: float = 0,
    interest_deposits_20_taxpayer: float = 0,
    interest_deposits_20_spouse: float = 0,
    interest_deposits_25_taxpayer: float = 0,
    interest_deposits_25_spouse: float = 0,
    rental_10_taxpayer: float = 0,
    rental_10_spouse: float = 0,
    rental_abroad_15_taxpayer: float = 0,
    rental_abroad_15_spouse: float = 0,
    gambling_35_taxpayer: float = 0,
    gambling_35_spouse: float = 0,
    renewable_energy_31_taxpayer: float = 0,
    renewable_energy_31_spouse: float = 0,
    pension_distribution_20_taxpayer: float = 0,
    pension_distribution_20_spouse: float = 0,
    unauthorized_withdrawal_35_taxpayer: float = 0,
    unauthorized_withdrawal_35_spouse: float = 0,
    # חלק ח — רווח הון
    capital_gains: float = 0,
    crypto_income: float = 0,
    # חלק י — הכנסות פטורות
    exempt_rental_income: float = 0,
    exempt_disability_taxpayer: float = 0,
    exempt_disability_spouse: float = 0,
    # חלק יב — ניכויים (manual)
    disability_insurance_self_taxpayer: float = 0,
    disability_insurance_self_spouse: float = 0,
    disability_insurance_employee_taxpayer: float = 0,
    disability_insurance_employee_spouse: float = 0,
    education_fund_self_taxpayer: float = 0,
    education_fund_self_spouse: float = 0,
    pension_self_taxpayer: float = 0,
    pension_self_spouse: float = 0,
    nii_non_employment_taxpayer: float = 0,
    nii_non_employment_spouse: float = 0,
    # חלק יג — נקודות זיכוי
    credit_points_taxpayer: float = 0,
    credit_points_spouse: float = 0,
    children_credit_points_taxpayer: float = 0,
    children_credit_points_spouse: float = 0,
    single_parent_points: float = 0,
    soldier_release_date_taxpayer: str = "",
    soldier_release_date_spouse: str = "",
    soldier_service_months_taxpayer: int = 0,
    soldier_service_months_spouse: int = 0,
    academic_code_taxpayer: str = "",
    academic_code_spouse: str = "",
    academic_completion_year_taxpayer: int = 0,
    academic_completion_year_spouse: int = 0,
    academic_study_years_taxpayer: int = 0,
    academic_study_years_spouse: int = 0,
    # חלק יד — זיכויים
    life_insurance_taxpayer: float = 0,
    life_insurance_spouse: float = 0,
    survivors_insurance_taxpayer: float = 0,
    survivors_insurance_spouse: float = 0,
    pension_employee_credit_taxpayer: float = 0,
    pension_employee_credit_spouse: float = 0,
    pension_self_credit_taxpayer: float = 0,
    pension_self_credit_spouse: float = 0,
    institution_care_taxpayer: float = 0,
    institution_care_spouse: float = 0,
    donation_taxpayer: float = 0,
    donation_spouse: float = 0,
    donation_us_taxpayer: float = 0,
    donation_us_spouse: float = 0,
    rnd_investment_taxpayer: float = 0,
    rnd_investment_spouse: float = 0,
    eilat_income_taxpayer: float = 0,
    # חלק טו — ניכויים במקור (manual overrides)
    rental_tax_paid: float = 0,
    withholding_other: float = 0,
    land_appreciation_tax: float = 0,
    # הוצאות הפקת הכנסה (דמי רו"ח)
    production_expenses_taxpayer: float = 0,
    production_expenses_spouse: float = 0,
    # הפרשי הצמדה וריבית
    interest_cpi_adjustment: float = 0,
) -> Form1301Result:
    """Compute the full Form 1301 from uploaded documents and manual inputs."""
    rules = get_rules(year)
    warnings: list[str] = []

    # Load and classify documents
    all_docs = load_documents_for_year(year)
    if not all_docs:
        warnings.append(f"לא נמצאו מסמכים לשנת {year}")

    id_supp = aggregate_id_supplement(all_docs)
    taxpayer_docs, spouse_docs, classification_warnings = classify_documents(
        all_docs,
        has_spouse_hint=bool(id_supp["spouse_name"]),
    )
    warnings.extend(classification_warnings)
    source_files = [d.original_filename for d in all_docs]

    # Auto-populate from Form 867
    form867 = aggregate_form867(all_docs)

    # Annual Sales Report (ESOP) — capital income goes to capital gains (field 139)
    annual_summary = aggregate_annual_summary(all_docs)
    if annual_summary["capital_income"] > 0:
        if annual_summary["capital_income"] > capital_gains:
            capital_gains = annual_summary["capital_income"]
        # Clear stale dividend_25 if it was previously auto-filled with this amount
        if dividend_25_taxpayer == annual_summary["capital_income"]:
            dividend_25_taxpayer = 0

    # Auto-populate rental from xlsx
    if rental_10_taxpayer == 0:
        rental_from_excel, tax_from_excel = aggregate_rental_excel(all_docs)
        if rental_from_excel > 0:
            rental_10_taxpayer = rental_from_excel
        if rental_tax_paid == 0 and tax_from_excel > 0:
            rental_tax_paid = tax_from_excel

    # Auto-populate rental tax from payment confirmations
    if rental_tax_paid == 0:
        rental_tax_paid = aggregate_rental_payments(all_docs)

    # Aggregate Form 106
    tp = aggregate_form106(taxpayer_docs)
    sp = aggregate_form106(spouse_docs)

    # Auto-populate donations from 106
    if donation_taxpayer == 0 and tp["donations"] > 0:
        donation_taxpayer = tp["donations"]
    if donation_spouse == 0 and sp["donations"] > 0:
        donation_spouse = sp["donations"]

    # Auto-populate life insurance from 106
    if life_insurance_taxpayer == 0 and tp["life_insurance"] > 0:
        life_insurance_taxpayer = tp["life_insurance"]
    if life_insurance_spouse == 0 and sp["life_insurance"] > 0:
        life_insurance_spouse = sp["life_insurance"]

    # Auto-populate capital gains (102) from 106 → capital gains (field 139)
    # This is "רווח הון מניירות ערך" from the 106, not a dividend
    if capital_gains == 0 and tp["capital_gains_102"] > 0:
        capital_gains += tp["capital_gains_102"]
        # Clear stale dividend_25 if it was previously auto-filled with this amount
        if dividend_25_taxpayer == tp["capital_gains_102"]:
            dividend_25_taxpayer = 0
    if capital_gains == 0 and sp["capital_gains_102"] > 0:
        capital_gains += sp["capital_gains_102"]
        if dividend_25_spouse == sp["capital_gains_102"]:
            dividend_25_spouse = 0

    # Only use 867 dividends/interest if no manual entry
    if dividend_25_taxpayer == 0 and form867["dividend_income"] > 0:
        dividend_25_taxpayer = form867["dividend_income"]
    if interest_deposits_25_taxpayer == 0 and form867["interest_income"] > 0:
        interest_deposits_25_taxpayer = form867["interest_income"]

    # Auto-populate children credit points from ID supplement (ספח)
    normalized_marital_status = marital_status.strip().lower()
    has_explicit_marital_status = normalized_marital_status != ""
    is_joint_married_household = normalized_marital_status in {"נשוי", "נשוי וחי ביחד", "married", "married_together"}
    has_spouse_for_tax = True

    if has_explicit_marital_status:
        has_spouse_for_tax = is_joint_married_household or bool(id_supp["spouse_name"])
        if normalized_marital_status in {"רווק", "גרוש", "אלמן", "פרוד", "single", "divorced", "widowed", "separated"}:
            has_spouse_for_tax = False

    if id_supp["children_birth_years"] and children_credit_points_taxpayer == 0 and children_credit_points_spouse == 0:
        # Determine who is the woman: if holder is male, spouse is the woman
        holder_is_woman = id_supp["holder_gender"] == "female"
        children_credit_points_taxpayer = compute_children_credit_points(
            id_supp["children_birth_years"], year, is_woman=holder_is_woman,
        )
        if has_spouse_for_tax:
            children_credit_points_spouse = compute_children_credit_points(
                id_supp["children_birth_years"], year, is_woman=not holder_is_woman,
            )

    if not has_spouse_for_tax:
        business_income_spouse = 0
        nii_self_employed_spouse = 0
        nii_employee_spouse = 0
        shift_work_spouse = 0
        retirement_grants_spouse = 0
        real_estate_income_spouse = 0
        other_income_spouse = 0
        interest_securities_15_spouse = 0
        interest_securities_20_spouse = 0
        interest_securities_25_spouse = 0
        dividend_preferred_20_spouse = 0
        dividend_25_spouse = 0
        dividend_significant_30_spouse = 0
        interest_deposits_15_spouse = 0
        interest_deposits_20_spouse = 0
        interest_deposits_25_spouse = 0
        rental_10_spouse = 0
        rental_abroad_15_spouse = 0
        gambling_35_spouse = 0
        renewable_energy_31_spouse = 0
        pension_distribution_20_spouse = 0
        unauthorized_withdrawal_35_spouse = 0
        exempt_disability_spouse = 0
        disability_insurance_self_spouse = 0
        disability_insurance_employee_spouse = 0
        education_fund_self_spouse = 0
        pension_self_spouse = 0
        nii_non_employment_spouse = 0
        children_credit_points_spouse = 0
        life_insurance_spouse = 0
        survivors_insurance_spouse = 0
        pension_employee_credit_spouse = 0
        pension_self_credit_spouse = 0
        institution_care_spouse = 0
        donation_spouse = 0
        donation_us_spouse = 0
        rnd_investment_spouse = 0
        production_expenses_spouse = 0
        spouse_docs = []
        sp = aggregate_form106(spouse_docs)

    # Auto-populate pension_employee credit from 106
    if pension_employee_credit_taxpayer == 0 and tp["pension_employee"] > 0:
        pension_employee_credit_taxpayer = tp["pension_employee"]
    if pension_employee_credit_spouse == 0 and sp["pension_employee"] > 0:
        pension_employee_credit_spouse = sp["pension_employee"]

    # Crypto income → capital gains (25%)
    capital_gains += crypto_income

    # Collect effective auto-populated values for frontend display
    effective_inputs: dict[str, float] = {}
    if dividend_25_taxpayer > 0:
        effective_inputs["dividend_25_taxpayer"] = dividend_25_taxpayer
    if dividend_25_spouse > 0:
        effective_inputs["dividend_25_spouse"] = dividend_25_spouse
    if interest_deposits_25_taxpayer > 0:
        effective_inputs["interest_deposits_25_taxpayer"] = interest_deposits_25_taxpayer
    if rental_10_taxpayer > 0:
        effective_inputs["rental_10_taxpayer"] = rental_10_taxpayer
    if rental_10_spouse > 0:
        effective_inputs["rental_10_spouse"] = rental_10_spouse
    if rental_tax_paid > 0:
        effective_inputs["rental_tax_paid"] = rental_tax_paid
    if donation_taxpayer > 0:
        effective_inputs["donation_taxpayer"] = donation_taxpayer
    if donation_spouse > 0:
        effective_inputs["donation_spouse"] = donation_spouse
    if life_insurance_taxpayer > 0:
        effective_inputs["life_insurance_taxpayer"] = life_insurance_taxpayer
    if life_insurance_spouse > 0:
        effective_inputs["life_insurance_spouse"] = life_insurance_spouse
    if pension_employee_credit_taxpayer > 0:
        effective_inputs["pension_employee_credit_taxpayer"] = pension_employee_credit_taxpayer
    if pension_employee_credit_spouse > 0:
        effective_inputs["pension_employee_credit_spouse"] = pension_employee_credit_spouse
    if children_credit_points_taxpayer > 0:
        effective_inputs["children_credit_points_taxpayer"] = children_credit_points_taxpayer
    if children_credit_points_spouse > 0:
        effective_inputs["children_credit_points_spouse"] = children_credit_points_spouse

    taxpayer_salary = tp["gross_salary"]
    spouse_salary = sp["gross_salary"]

    # Deduct production expenses (CPA fee) from salary
    taxpayer_salary -= production_expenses_taxpayer
    spouse_salary -= production_expenses_spouse

    # === Build all field structures ===

    income = IncomeFields(
        field_150=business_income_taxpayer,
        field_170=business_income_spouse,
        field_250=nii_self_employed_taxpayer,
        field_270=nii_self_employed_spouse,
        field_194=nii_employee_taxpayer,
        field_196=nii_employee_spouse,
        field_158=taxpayer_salary,
        field_172=spouse_salary,
        field_069=shift_work_taxpayer,
        field_068=shift_work_spouse,
        field_258=retirement_grants_taxpayer,
        field_272=retirement_grants_spouse,
    )

    other_income = OtherIncomeFields(
        field_059=real_estate_income_taxpayer,
        field_201=real_estate_income_spouse,
        field_167=other_income_joint,
        field_205=other_income_spouse,
        field_305=other_income_taxpayer,
    )

    special_rate = SpecialRateIncomeFields(
        field_060=interest_securities_15_taxpayer,
        field_211=interest_securities_15_spouse,
        field_067=interest_securities_20_taxpayer,
        field_228=interest_securities_20_spouse,
        field_157=interest_securities_25_taxpayer,
        field_257=interest_securities_25_spouse,
        field_173=dividend_preferred_20_taxpayer,
        field_275=dividend_preferred_20_spouse,
        field_141=dividend_25_taxpayer,
        field_241=dividend_25_spouse,
        field_055=dividend_significant_30_taxpayer,
        field_212=dividend_significant_30_spouse,
        field_078=interest_deposits_15_taxpayer,
        field_217=interest_deposits_15_spouse,
        field_126=interest_deposits_20_taxpayer,
        field_226=interest_deposits_20_spouse,
        field_142=interest_deposits_25_taxpayer,
        field_242=interest_deposits_25_spouse,
        field_222=rental_10_taxpayer,
        field_284=rental_10_spouse,
        field_225=rental_abroad_15_taxpayer,
        field_285=rental_abroad_15_spouse,
        field_227=gambling_35_taxpayer,
        field_286=gambling_35_spouse,
        field_335=renewable_energy_31_taxpayer,
        field_337=renewable_energy_31_spouse,
        field_288=pension_distribution_20_taxpayer,
        field_338=pension_distribution_20_spouse,
        field_213=unauthorized_withdrawal_35_taxpayer,
        field_313=unauthorized_withdrawal_35_spouse,
    )

    capital_gains_fields = CapitalGainsFields(
        field_139=capital_gains,
    )

    exempt = ExemptIncomeFields(
        field_109=exempt_disability_taxpayer,
        field_309=exempt_disability_spouse,
        field_332=exempt_rental_income,
    )

    deductions = DeductionFields(
        production_expenses_taxpayer=production_expenses_taxpayer,
        production_expenses_spouse=production_expenses_spouse,
        field_112=disability_insurance_self_taxpayer,
        field_113=disability_insurance_self_spouse,
        field_206=disability_insurance_employee_taxpayer,
        field_207=disability_insurance_employee_spouse,
        field_136=education_fund_self_taxpayer,
        field_137=education_fund_self_spouse,
        field_218=tp.get("education_fund", 0),
        field_219=sp.get("education_fund", 0),
        field_135=pension_self_taxpayer,
        field_180=pension_self_spouse,
        field_030=nii_non_employment_taxpayer,
        field_089=nii_non_employment_spouse,
        field_244=tp["insured_income"],
        field_245=sp["insured_income"],
        field_248=tp["pension_employer"],
        field_249=sp["pension_employer"],
        field_011=tp["convalescence_pay"],
        field_012=sp["convalescence_pay"],
    )

    # Credit points
    taxpayer_is_woman = id_supp["holder_gender"] == "female"
    immigrant_credit_points_taxpayer = _monthly_immigrant_credit_points(
        immigrant_taxpayer_status,
        _parse_iso_date(immigrant_taxpayer_arrival_date),
        year,
    )
    immigrant_credit_points_spouse = _monthly_immigrant_credit_points(
        immigrant_spouse_status,
        _parse_iso_date(immigrant_spouse_arrival_date),
        year,
    )
    discharged_soldier_points_taxpayer = _compute_discharged_soldier_credit_points(
        soldier_release_date_taxpayer,
        soldier_service_months_taxpayer,
        year,
    )
    discharged_soldier_points_spouse = _compute_discharged_soldier_credit_points(
        soldier_release_date_spouse,
        soldier_service_months_spouse,
        year,
    )
    academic_credit_points_taxpayer = _compute_academic_credit_points(
        academic_code_taxpayer,
        academic_completion_year_taxpayer,
        academic_study_years_taxpayer,
        year,
    )
    academic_credit_points_spouse = _compute_academic_credit_points(
        academic_code_spouse,
        academic_completion_year_spouse,
        academic_study_years_spouse,
        year,
    )
    spouse_helper_points = _compute_spouse_helper_credit_points(
        has_spouse_for_tax,
        has_joint_income_source,
        spouse_assists_income,
        bool(id_supp["children_birth_years"]),
    )
    if credit_points_taxpayer == 0:
        credit_points_taxpayer = rules.resident_credit_points + (rules.woman_credit_points if taxpayer_is_woman else 0) + immigrant_credit_points_taxpayer + discharged_soldier_points_taxpayer + academic_credit_points_taxpayer + spouse_helper_points
    if credit_points_spouse == 0:
        credit_points_spouse = (rules.resident_credit_points + rules.woman_credit_points + immigrant_credit_points_spouse + discharged_soldier_points_spouse + academic_credit_points_spouse) if has_spouse_for_tax else 0
    credit_points_taxpayer += children_credit_points_taxpayer + single_parent_points
    credit_points_spouse += children_credit_points_spouse

    credit_points = CreditPointsFields(
        field_020=rules.resident_credit_points,
        field_021=rules.resident_credit_points,
        field_260=children_credit_points_taxpayer,
        field_262=children_credit_points_spouse,
        field_026=single_parent_points,
        field_024=discharged_soldier_points_taxpayer,
        field_124=discharged_soldier_points_spouse,
        field_181=academic_code_taxpayer,
        field_182=academic_code_spouse,
        spouse_helper_points=spouse_helper_points,
        credit_points_taxpayer=credit_points_taxpayer,
        credit_points_spouse=credit_points_spouse,
    )

    tax_credits = TaxCreditFields(
        field_036=life_insurance_taxpayer,
        field_081=life_insurance_spouse,
        field_140=survivors_insurance_taxpayer,
        field_240=survivors_insurance_spouse,
        field_045=pension_employee_credit_taxpayer,
        field_086=pension_employee_credit_spouse,
        field_268=pension_self_credit_taxpayer,
        field_269=pension_self_credit_spouse,
        field_132=institution_care_taxpayer,
        field_232=institution_care_spouse,
        field_037=donation_taxpayer,
        field_237=donation_spouse,
        field_046=donation_us_taxpayer,
        field_048=donation_us_spouse,
        field_155=rnd_investment_taxpayer,
        field_199=rnd_investment_spouse,
        field_183=eilat_income_taxpayer,
    )

    # === Withholdings ===
    dividend_interest_withheld = form867.get("dividend_tax_withheld", 0) + form867.get("interest_tax_withheld", 0)
    withholdings = WithholdingFields(
        field_042=tp["tax_withheld"] + sp["tax_withheld"],
        field_043=dividend_interest_withheld,
        field_040=withholding_other,
        field_041=land_appreciation_tax,
        field_220=rental_tax_paid,
        field_tax_advance=annual_summary.get("tax_advance_payment", 0),
    )

    # === Tax Calculation ===

    # Progressive tax on personal labor income (חלק ג + ד)
    tp_progressive_income = (
        taxpayer_salary + business_income_taxpayer
        + nii_self_employed_taxpayer + nii_employee_taxpayer
        + shift_work_taxpayer + retirement_grants_taxpayer
        + real_estate_income_taxpayer + other_income_taxpayer
        + other_income_joint
    )
    sp_progressive_income = (
        spouse_salary + business_income_spouse
        + nii_self_employed_spouse + nii_employee_spouse
        + shift_work_spouse + retirement_grants_spouse
        + real_estate_income_spouse + other_income_spouse
    )

    tax_regular_tp = compute_progressive_tax(tp_progressive_income, rules, personal_labor=True)
    tax_regular_sp = compute_progressive_tax(sp_progressive_income, rules, personal_labor=True)

    # Special-rate taxes (חלק ה) — each rate group
    total_15 = (
        interest_securities_15_taxpayer + interest_securities_15_spouse
        + interest_deposits_15_taxpayer + interest_deposits_15_spouse
        + rental_abroad_15_taxpayer + rental_abroad_15_spouse
    )
    total_20 = (
        interest_securities_20_taxpayer + interest_securities_20_spouse
        + dividend_preferred_20_taxpayer + dividend_preferred_20_spouse
        + interest_deposits_20_taxpayer + interest_deposits_20_spouse
        + pension_distribution_20_taxpayer + pension_distribution_20_spouse
    )
    total_25 = (
        interest_securities_25_taxpayer + interest_securities_25_spouse
        + dividend_25_taxpayer + dividend_25_spouse
        + interest_deposits_25_taxpayer + interest_deposits_25_spouse
    )
    total_30 = dividend_significant_30_taxpayer + dividend_significant_30_spouse
    total_31 = renewable_energy_31_taxpayer + renewable_energy_31_spouse
    total_35 = (
        gambling_35_taxpayer + gambling_35_spouse
        + unauthorized_withdrawal_35_taxpayer + unauthorized_withdrawal_35_spouse
    )
    total_rental_10 = rental_10_taxpayer + rental_10_spouse

    tax_15 = round(total_15 * 0.15)
    tax_20 = round(total_20 * 0.20)
    tax_25 = round(total_25 * 0.25)
    tax_30 = round(total_30 * 0.30)
    tax_31 = round(total_31 * 0.31)
    tax_35 = round(total_35 * 0.35)
    tax_rental = round(total_rental_10 * rules.rental_flat_rate)
    tax_capital = round(capital_gains * rules.dividend_rate)
    shift_work_credit_taxpayer = _compute_shift_work_credit(shift_work_taxpayer, taxpayer_salary, rules)
    shift_work_credit_spouse = _compute_shift_work_credit(shift_work_spouse, spouse_salary, rules)

    # Surtax (מס יסף 3%) — per person
    all_capital_tp = (
        dividend_25_taxpayer + dividend_significant_30_taxpayer
        + dividend_preferred_20_taxpayer
        + interest_securities_15_taxpayer + interest_securities_20_taxpayer
        + interest_securities_25_taxpayer
        + interest_deposits_15_taxpayer + interest_deposits_20_taxpayer
        + interest_deposits_25_taxpayer
        + capital_gains
    )
    tp_total_for_surtax = tp_progressive_income + rental_10_taxpayer + all_capital_tp + rental_abroad_15_taxpayer + gambling_35_taxpayer
    surtax_tp = compute_surtax(tp_total_for_surtax, rules, capital_income=all_capital_tp)

    all_capital_sp = (
        dividend_25_spouse + dividend_significant_30_spouse
        + dividend_preferred_20_spouse
        + interest_securities_15_spouse + interest_securities_20_spouse
        + interest_securities_25_spouse
        + interest_deposits_15_spouse + interest_deposits_20_spouse
        + interest_deposits_25_spouse
    )
    sp_total_for_surtax = sp_progressive_income + rental_10_spouse + all_capital_sp + rental_abroad_15_spouse + gambling_35_spouse
    surtax_sp = compute_surtax(sp_total_for_surtax, rules, capital_income=all_capital_sp)
    surtax = surtax_tp + surtax_sp

    gross_tax = (
        tax_regular_tp + tax_regular_sp
        + tax_15 + tax_20 + tax_25 + tax_30 + tax_31 + tax_35
        + tax_rental + tax_capital
        + surtax
    )

    # === Credits (per-person with capping — חישוב נפרד) ===
    cp_amount_tp = round(credit_points_taxpayer * rules.credit_point_value)
    cp_amount_sp = round(credit_points_spouse * rules.credit_point_value)

    pension_emp_credit_tp = compute_pension_employee_credit(
        pension_employee_credit_taxpayer, tp["insured_income"], rules
    )
    pension_emp_credit_sp = compute_pension_employee_credit(
        pension_employee_credit_spouse, sp["insured_income"], rules
    )

    # Donation credit — split proportionally by donator
    donation_tp = donation_taxpayer + donation_us_taxpayer
    donation_sp = donation_spouse + donation_us_spouse
    donation_credit_tp = round(donation_tp * 0.35)
    donation_credit_sp = round(donation_sp * 0.35)
    donation_credit = donation_credit_tp + donation_credit_sp

    # Life insurance credit (25%) — per person
    life_ins_credit_tp = round((life_insurance_taxpayer + survivors_insurance_taxpayer) * 0.25)
    life_ins_credit_sp = round((life_insurance_spouse + survivors_insurance_spouse) * 0.25)

    # Section 76 credit — self-employed pension (35% of deposits)
    pension_self_credit_tp = round(pension_self_credit_taxpayer * 0.35)
    pension_self_credit_sp = round(pension_self_credit_spouse * 0.35)

    # Per-person credit totals
    total_credits_tp = (
        cp_amount_tp + pension_emp_credit_tp + pension_self_credit_tp
        + donation_credit_tp + life_ins_credit_tp + shift_work_credit_taxpayer
    )
    total_credits_sp = (
        cp_amount_sp + pension_emp_credit_sp + pension_self_credit_sp
        + donation_credit_sp + life_ins_credit_sp + shift_work_credit_spouse
    )
    total_credits = total_credits_tp + total_credits_sp

    # Per-person gross tax for capping
    # Taxpayer gets: their progressive tax + ALL special-rate taxes + surtax
    # (capital/rental income is typically the taxpayer's)
    gross_tax_tp = (
        tax_regular_tp
        + tax_15 + tax_20 + tax_25 + tax_30 + tax_31 + tax_35
        + tax_rental + tax_capital
        + surtax_tp
    )
    gross_tax_sp = tax_regular_sp + surtax_sp

    # Net tax: credits capped per person (excess credits are lost)
    net_tax = max(0, gross_tax_tp - total_credits_tp) + max(0, gross_tax_sp - total_credits_sp)

    total_paid = (
        tp["tax_withheld"] + sp["tax_withheld"]
        + rental_tax_paid
        + withholding_other
        + land_appreciation_tax
    )
    balance = net_tax - total_paid
    balance_after_interest = balance + interest_cpi_adjustment

    calculation = TaxCalculation(
        tax_regular_taxpayer=tax_regular_tp,
        tax_regular_spouse=tax_regular_sp,
        tax_15pct=tax_15,
        tax_20pct=tax_20,
        tax_25pct=tax_25,
        tax_30pct=tax_30,
        tax_31pct=tax_31,
        tax_35pct=tax_35,
        tax_rental_10pct=tax_rental,
        tax_capital_gains=tax_capital,
        surtax=surtax,
        gross_tax=gross_tax,
        credit_points_amount_taxpayer=cp_amount_tp,
        credit_points_amount_spouse=cp_amount_sp,
        shift_work_credit_taxpayer=shift_work_credit_taxpayer,
        shift_work_credit_spouse=shift_work_credit_spouse,
        pension_employee_credit_taxpayer=pension_emp_credit_tp,
        pension_employee_credit_spouse=pension_emp_credit_sp,
        donation_credit=donation_credit,
        life_insurance_credit_taxpayer=life_ins_credit_tp,
        life_insurance_credit_spouse=life_ins_credit_sp,
        total_credits_taxpayer=total_credits_tp,
        total_credits_spouse=total_credits_sp,
        total_credits=total_credits,
        gross_tax_taxpayer=gross_tax_tp,
        gross_tax_spouse=gross_tax_sp,
        net_tax=net_tax,
        total_withheld=tp["tax_withheld"] + sp["tax_withheld"],
        total_paid=total_paid,
        balance=balance,
        interest_cpi_adjustment=interest_cpi_adjustment,
        balance_after_interest=balance_after_interest,
    )

    return Form1301Result(
        tax_year=year,
        income=income,
        other_income=other_income,
        special_rate=special_rate,
        capital_gains=capital_gains_fields,
        exempt=exempt,
        deductions=deductions,
        credit_points=credit_points,
        tax_credits=tax_credits,
        withholdings=withholdings,
        calculation=calculation,
        source_documents=source_files,
        warnings=warnings,
        effective_inputs=effective_inputs,
    )
