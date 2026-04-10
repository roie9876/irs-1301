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
    CreditFields,
    DeductionFields,
    Form1301Result,
    IncomeFields,
    TaxCalculation,
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
        "insured_income": 0,
        "convalescence_pay": 0,
        "education_fund": 0,
        "national_insurance": 0,
        "health_insurance": 0,
    }

    for doc in docs:
        ext = doc.extracted
        totals["gross_salary"] += _fv(ext.get("gross_salary", {}))
        totals["tax_withheld"] += _fv(ext.get("tax_withheld", {}))
        totals["pension_employer"] += _fv(ext.get("pension_employer", {}))
        totals["insured_income"] += _fv(ext.get("insured_income", {}))
        totals["convalescence_pay"] += _fv(ext.get("convalescence_pay", {}))
        totals["education_fund"] += _fv(ext.get("education_fund", {}))
        totals["national_insurance"] += _fv(ext.get("national_insurance", {}))
        totals["health_insurance"] += _fv(ext.get("health_insurance", {}))

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


def compute_pension_credit(pension_employer: float, insured_income: float, rules) -> float:
    """Compute pension contribution credit (35% of qualifying amount).

    Credit is 35% of employer pension contribution, up to 7% of insured income.
    """
    max_qualifying = insured_income * rules.max_pension_deduction_pct
    qualifying = min(pension_employer, max_qualifying)
    return round(qualifying * 0.35)


def compute_form1301(
    year: int,
    rental_income: float = 0,
    rental_tax_paid: float = 0,
    dividend_income: float = 0,
    interest_income: float = 0,
    capital_gains: float = 0,
    donation_amount_taxpayer: float = 0,
    donation_amount_spouse: float = 0,
    life_insurance_taxpayer: float = 0,
    life_insurance_spouse: float = 0,
    credit_points_taxpayer: float = 0,
    credit_points_spouse: float = 0,
) -> Form1301Result:
    """Compute the full Form 1301 from uploaded documents and manual inputs.

    Args:
        year: Tax year
        rental_income: Total annual rental income (10% track)
        rental_tax_paid: Rental tax already paid during year
        dividend_income: Dividend income (25% rate)
        interest_income: Interest income (25% rate)
        capital_gains: Capital gains (25% rate)
        donation_amount_taxpayer: Donation receipts — taxpayer
        donation_amount_spouse: Donation receipts — spouse
        life_insurance_taxpayer: Life insurance premium — taxpayer
        life_insurance_spouse: Life insurance premium — spouse
        credit_points_taxpayer: Total credit points — taxpayer (0 = auto-calculate basic)
        credit_points_spouse: Total credit points — spouse (0 = auto-calculate basic)
    """
    rules = get_rules(year)
    warnings: list[str] = []

    # Load and classify documents
    all_docs = load_documents_for_year(year)
    if not all_docs:
        warnings.append(f"לא נמצאו מסמכים לשנת {year}")

    taxpayer_docs, spouse_docs = classify_documents(all_docs)
    source_files = [d.original_filename for d in all_docs]

    # Auto-populate from Form 867 documents if not manually provided
    form867 = aggregate_form867(all_docs)
    if dividend_income == 0 and form867["dividend_income"] > 0:
        dividend_income = form867["dividend_income"]
    if interest_income == 0 and form867["interest_income"] > 0:
        interest_income = form867["interest_income"]

    # Auto-populate rental tax paid from payment confirmations if not manually provided
    if rental_tax_paid == 0:
        rental_tax_paid_from_docs = aggregate_rental_payments(all_docs)
        if rental_tax_paid_from_docs > 0:
            rental_tax_paid = rental_tax_paid_from_docs

    # CPA fee deduction from receipts
    cpa_fee_deduction = aggregate_receipts(all_docs)

    # Aggregate Form 106 data
    tp = aggregate_form106(taxpayer_docs)
    sp = aggregate_form106(spouse_docs)

    # Apply CPA fee deduction against taxpayer's gross salary
    # (deductible when taxpayer has non-salary income requiring filing)
    taxpayer_salary = tp["gross_salary"]
    if cpa_fee_deduction > 0 and (dividend_income > 0 or capital_gains > 0 or rental_income > 0):
        taxpayer_salary = max(0, taxpayer_salary - cpa_fee_deduction)

    # --- Income Fields ---
    income = IncomeFields(
        field_158=taxpayer_salary,
        field_172=sp["gross_salary"],
        field_222=rental_income,
        field_141=dividend_income,
        field_327=interest_income,
        field_139=capital_gains,
    )

    # --- Deduction Fields ---
    deductions = DeductionFields(
        field_244=tp["insured_income"],
        field_245=sp["insured_income"],
        field_248=tp["pension_employer"],
        field_249=sp["pension_employer"],
        field_086=life_insurance_taxpayer,
        field_087=life_insurance_spouse,
        field_040=tp["national_insurance"],
        field_036=sp["national_insurance"],
    )

    # --- Credit Points ---
    # Auto-calculate basic credits if not provided
    if credit_points_taxpayer <= 0:
        credit_points_taxpayer = rules.resident_credit_points  # 2.25 basic
    if credit_points_spouse <= 0:
        credit_points_spouse = rules.resident_credit_points + rules.woman_credit_points  # 2.75 basic

    credits = CreditFields(
        field_011=tp["convalescence_pay"],
        field_012=sp["convalescence_pay"],
        credit_points_taxpayer=credit_points_taxpayer,
        credit_points_spouse=credit_points_spouse,
        field_237=donation_amount_taxpayer,
        field_037=donation_amount_spouse,
        field_045=life_insurance_taxpayer,
        field_046=life_insurance_spouse,
    )

    # --- Withholdings ---
    total_tax_withheld = tp["tax_withheld"] + sp["tax_withheld"]
    withholdings = WithholdingFields(
        field_042=total_tax_withheld,
        field_043=sp["tax_withheld"],
        field_220=rental_tax_paid,
    )

    # --- Tax Calculation ---
    # Progressive tax on salary (personal labor)
    tax_regular_tp = compute_progressive_tax(taxpayer_salary, rules, personal_labor=True)
    tax_regular_sp = compute_progressive_tax(sp["gross_salary"], rules, personal_labor=True)

    # Special rate taxes
    tax_rental = round(rental_income * rules.rental_flat_rate)
    tax_dividend = round(dividend_income * rules.dividend_rate)
    tax_interest = round(interest_income * rules.interest_rate)
    tax_capital = round(capital_gains * rules.dividend_rate)  # Same rate for non-significant holder

    # Surtax (מס יסף) — computed PER PERSON in חישוב נפרד
    # Taxpayer: salary + rental + dividends + interest + capital gains (no spouse income)
    capital_income_tp = dividend_income + interest_income + capital_gains
    tp_total_income = taxpayer_salary + rental_income + capital_income_tp
    surtax_tp = compute_surtax(tp_total_income, rules, capital_income=capital_income_tp)
    # Spouse: only their salary
    surtax_sp = compute_surtax(sp["gross_salary"], rules)
    surtax = surtax_tp + surtax_sp

    gross_tax = (
        tax_regular_tp + tax_regular_sp
        + tax_rental + tax_dividend + tax_interest + tax_capital
        + surtax
    )

    # Credits
    cp_amount_tp = round(credit_points_taxpayer * rules.credit_point_value)
    cp_amount_sp = round(credit_points_spouse * rules.credit_point_value)

    pension_credit_tp = compute_pension_credit(tp["pension_employer"], tp["insured_income"], rules)
    pension_credit_sp = compute_pension_credit(sp["pension_employer"], sp["insured_income"], rules)

    donation_credit = round((donation_amount_taxpayer + donation_amount_spouse) * 0.35)

    life_ins_credit = round((life_insurance_taxpayer + life_insurance_spouse) * 0.25)

    total_credits = (
        cp_amount_tp + cp_amount_sp
        + pension_credit_tp + pension_credit_sp
        + donation_credit + life_ins_credit
    )

    net_tax = max(0, gross_tax - total_credits)
    total_paid = total_tax_withheld + rental_tax_paid
    balance = net_tax - total_paid  # Positive = owe, negative = refund

    calculation = TaxCalculation(
        tax_regular_taxpayer=tax_regular_tp,
        tax_regular_spouse=tax_regular_sp,
        tax_rental_10pct=tax_rental,
        tax_dividend_25pct=tax_dividend,
        tax_interest_25pct=tax_interest,
        tax_capital_gains=tax_capital,
        surtax=surtax,
        gross_tax=gross_tax,
        credit_points_amount_taxpayer=cp_amount_tp,
        credit_points_amount_spouse=cp_amount_sp,
        pension_credit_taxpayer=pension_credit_tp,
        pension_credit_spouse=pension_credit_sp,
        donation_credit=donation_credit,
        life_insurance_credit=life_ins_credit,
        total_credits=total_credits,
        net_tax=net_tax,
        total_withheld=total_tax_withheld,
        total_paid=total_paid,
        balance=balance,
    )

    return Form1301Result(
        tax_year=year,
        income=income,
        deductions=deductions,
        credits=credits,
        withholdings=withholdings,
        calculation=calculation,
        source_documents=source_files,
        warnings=warnings,
    )
