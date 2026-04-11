"""Form 1301 calculator — builds the tax return from source documents."""

import json
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

def classify_documents(documents: list[DocumentInfo]) -> tuple[list[DocumentInfo], list[DocumentInfo]]:
    """Split Form 106 documents into taxpayer (רשום) and spouse (בן/בת זוג) groups.

    Heuristic: if employer name contains known spouse employers or filename
    contains 'michal'/'spouse', classify as spouse. Otherwise taxpayer.
    """
    taxpayer_docs: list[DocumentInfo] = []
    spouse_docs: list[DocumentInfo] = []

    # Only classify Form 106 documents
    form106_docs = [d for d in documents if d.document_type == "form_106"]

    for doc in form106_docs:
        filename_lower = doc.original_filename.lower()
        employer_name = str(_fv(doc.extracted.get("employer_name", {})) if isinstance(doc.extracted.get("employer_name"), dict) and doc.extracted["employer_name"].get("value") else "").lower()
        if isinstance(doc.extracted.get("employer_name"), dict):
            employer_name = str(doc.extracted["employer_name"].get("value", "")).lower()

        is_spouse = any([
            "michal" in filename_lower,
            "מיכל" in filename_lower,
            "spouse" in filename_lower,
            "בת זוג" in filename_lower,
            "בן זוג" in filename_lower,
            "תדיראן" in employer_name,
            "tidiran" in employer_name,
        ])

        if is_spouse:
            spouse_docs.append(doc)
        else:
            taxpayer_docs.append(doc)

    return taxpayer_docs, spouse_docs


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


def compute_pension_credit(pension_employer: float, insured_income: float, rules) -> float:
    """Compute pension contribution credit (35% of qualifying amount).

    Credit is 35% of employer pension contribution, up to 7% of insured income.
    """
    max_qualifying = insured_income * rules.max_pension_deduction_pct
    qualifying = min(pension_employer, max_qualifying)
    return round(qualifying * 0.35)


def compute_pension_employee_credit(pension_employee: float) -> float:
    """Compute credit for employee pension deposits (section 75 — 35%)."""
    return round(pension_employee * 0.35)


def compute_form1301(
    year: int,
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
    academic_code_taxpayer: str = "",
    academic_code_spouse: str = "",
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
) -> Form1301Result:
    """Compute the full Form 1301 from uploaded documents and manual inputs."""
    rules = get_rules(year)
    warnings: list[str] = []

    # Load and classify documents
    all_docs = load_documents_for_year(year)
    if not all_docs:
        warnings.append(f"לא נמצאו מסמכים לשנת {year}")

    taxpayer_docs, spouse_docs = classify_documents(all_docs)
    source_files = [d.original_filename for d in all_docs]

    # Auto-populate from Form 867
    form867 = aggregate_form867(all_docs)
    if dividend_25_taxpayer == 0 and form867["dividend_income"] > 0:
        dividend_25_taxpayer = form867["dividend_income"]
    if interest_deposits_25_taxpayer == 0 and form867["interest_income"] > 0:
        interest_deposits_25_taxpayer = form867["interest_income"]

    # Annual Sales Report (ESOP) — capital income goes to dividends
    annual_summary = aggregate_annual_summary(all_docs)
    if annual_summary["capital_income"] > 0:
        if annual_summary["capital_income"] > dividend_25_taxpayer:
            dividend_25_taxpayer = annual_summary["capital_income"]

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

    # Auto-populate pension_employee credit from 106
    if pension_employee_credit_taxpayer == 0 and tp["pension_employee"] > 0:
        pension_employee_credit_taxpayer = tp["pension_employee"]
    if pension_employee_credit_spouse == 0 and sp["pension_employee"] > 0:
        pension_employee_credit_spouse = sp["pension_employee"]

    # Crypto income → capital gains (25%)
    capital_gains += crypto_income

    taxpayer_salary = tp["gross_salary"]
    spouse_salary = sp["gross_salary"]

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
    if credit_points_taxpayer <= 0:
        credit_points_taxpayer = rules.resident_credit_points
    if credit_points_spouse <= 0:
        credit_points_spouse = rules.resident_credit_points + rules.woman_credit_points
    credit_points_taxpayer += children_credit_points_taxpayer + single_parent_points
    credit_points_spouse += children_credit_points_spouse

    credit_points = CreditPointsFields(
        field_020=rules.resident_credit_points,
        field_021=rules.resident_credit_points,
        field_260=children_credit_points_taxpayer,
        field_262=children_credit_points_spouse,
        field_026=single_parent_points,
        field_181=academic_code_taxpayer,
        field_182=academic_code_spouse,
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

    # === Credits ===
    cp_amount_tp = round(credit_points_taxpayer * rules.credit_point_value)
    cp_amount_sp = round(credit_points_spouse * rules.credit_point_value)

    pension_credit_tp = compute_pension_credit(tp["pension_employer"], tp["insured_income"], rules)
    pension_credit_sp = compute_pension_credit(sp["pension_employer"], sp["insured_income"], rules)

    pension_emp_credit_tp = compute_pension_employee_credit(pension_employee_credit_taxpayer)
    pension_emp_credit_sp = compute_pension_employee_credit(pension_employee_credit_spouse)

    all_donations = donation_taxpayer + donation_spouse + donation_us_taxpayer + donation_us_spouse
    donation_credit = round(all_donations * 0.35)

    all_insurance = (
        life_insurance_taxpayer + life_insurance_spouse
        + survivors_insurance_taxpayer + survivors_insurance_spouse
    )
    life_ins_credit = round(all_insurance * 0.25)

    total_credits = (
        cp_amount_tp + cp_amount_sp
        + pension_credit_tp + pension_credit_sp
        + pension_emp_credit_tp + pension_emp_credit_sp
        + donation_credit + life_ins_credit
    )

    net_tax = max(0, gross_tax - total_credits)

    total_paid = (
        tp["tax_withheld"] + sp["tax_withheld"]
        + rental_tax_paid
        + dividend_interest_withheld
        + withholding_other
        + land_appreciation_tax
    )
    balance = net_tax - total_paid

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
        pension_credit_taxpayer=pension_credit_tp,
        pension_credit_spouse=pension_credit_sp,
        pension_employee_credit_taxpayer=pension_emp_credit_tp,
        pension_employee_credit_spouse=pension_emp_credit_sp,
        donation_credit=donation_credit,
        life_insurance_credit=life_ins_credit,
        total_credits=total_credits,
        net_tax=net_tax,
        total_withheld=tp["tax_withheld"] + sp["tax_withheld"],
        total_paid=total_paid,
        balance=balance,
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
    )
