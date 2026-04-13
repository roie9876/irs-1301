import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.advisor import AdvisorAnswerResponse, AdvisorQuestionRequest, ChatRequest

logger = logging.getLogger(__name__)
from app.schemas.form1301 import Form1301PreviewResponse
from app.schemas.field_help import FieldHelpResponse
from app.services.advisor_ai import answer_advisor_question, answer_chat_question
from app.services.field_help import get_field_help
from app.services.form1301 import compute_form1301

router = APIRouter(tags=["form1301"])


@router.get("/form-1301/field-help/{code}", response_model=FieldHelpResponse)
async def field_help(code: str):
    return get_field_help(code)


@router.post("/form-1301/assistant", response_model=AdvisorAnswerResponse)
async def form1301_assistant(body: AdvisorQuestionRequest):
    answer = await answer_advisor_question(body)
    return AdvisorAnswerResponse(answer=answer)


@router.post("/form-1301/chat", response_model=AdvisorAnswerResponse)
async def form1301_chat(body: ChatRequest):
    try:
        answer = await answer_chat_question(
            question=body.question,
            tax_year=body.tax_year,
            form_summary=body.form_summary,
            source_documents=body.source_documents,
            warnings=body.warnings,
            balance=body.balance,
            net_tax=body.net_tax,
        )
        return AdvisorAnswerResponse(answer=answer)
    except ValueError as exc:
        logger.warning("Chat LLM config error: %s", exc)
        return JSONResponse(status_code=503, content={"detail": str(exc)})
    except Exception as exc:
        logger.exception("Chat LLM call failed")
        return JSONResponse(
            status_code=502,
            content={"detail": f"שגיאה בתקשורת עם מודל השפה: {type(exc).__name__}"},
        )


@router.get("/form-1301/preview", response_model=Form1301PreviewResponse)
async def preview_form1301(
    year: int = Query(2024, description="Tax year"),
    marital_status: str = Query(""),
    has_joint_income_source: bool = Query(False),
    spouse_assists_income: bool = Query(False),
    taxpayer_gender: str = Query(""),
    immigrant_taxpayer_status: str = Query(""),
    immigrant_taxpayer_arrival_date: str = Query(""),
    immigrant_spouse_status: str = Query(""),
    immigrant_spouse_arrival_date: str = Query(""),
    # חלק ג — הכנסות מיגיעה אישית
    business_income_taxpayer: float = Query(0),
    business_income_spouse: float = Query(0),
    nii_self_employed_taxpayer: float = Query(0),
    nii_self_employed_spouse: float = Query(0),
    nii_employee_taxpayer: float = Query(0),
    nii_employee_spouse: float = Query(0),
    shift_work_taxpayer: float = Query(0),
    shift_work_spouse: float = Query(0),
    retirement_grants_taxpayer: float = Query(0),
    retirement_grants_spouse: float = Query(0),
    # חלק ד — הכנסות בשיעורי מס רגילים
    real_estate_income_taxpayer: float = Query(0),
    real_estate_income_spouse: float = Query(0),
    other_income_taxpayer: float = Query(0),
    other_income_spouse: float = Query(0),
    other_income_joint: float = Query(0),
    # חלק ה — הכנסות בשיעורי מס מיוחדים
    interest_securities_15_taxpayer: float = Query(0),
    interest_securities_15_spouse: float = Query(0),
    interest_securities_20_taxpayer: float = Query(0),
    interest_securities_20_spouse: float = Query(0),
    interest_securities_25_taxpayer: float = Query(0),
    interest_securities_25_spouse: float = Query(0),
    dividend_preferred_20_taxpayer: float = Query(0),
    dividend_preferred_20_spouse: float = Query(0),
    dividend_25_taxpayer: float = Query(0),
    dividend_25_spouse: float = Query(0),
    dividend_significant_30_taxpayer: float = Query(0),
    dividend_significant_30_spouse: float = Query(0),
    interest_deposits_15_taxpayer: float = Query(0),
    interest_deposits_15_spouse: float = Query(0),
    interest_deposits_20_taxpayer: float = Query(0),
    interest_deposits_20_spouse: float = Query(0),
    interest_deposits_25_taxpayer: float = Query(0),
    interest_deposits_25_spouse: float = Query(0),
    rental_10_taxpayer: float = Query(0),
    rental_10_spouse: float = Query(0),
    rental_abroad_15_taxpayer: float = Query(0),
    rental_abroad_15_spouse: float = Query(0),
    gambling_35_taxpayer: float = Query(0),
    gambling_35_spouse: float = Query(0),
    renewable_energy_31_taxpayer: float = Query(0),
    renewable_energy_31_spouse: float = Query(0),
    pension_distribution_20_taxpayer: float = Query(0),
    pension_distribution_20_spouse: float = Query(0),
    unauthorized_withdrawal_35_taxpayer: float = Query(0),
    unauthorized_withdrawal_35_spouse: float = Query(0),
    # חלק ח — רווח הון
    capital_gains: float = Query(0),
    crypto_income: float = Query(0),
    # חלק י — הכנסות פטורות
    exempt_rental_income: float = Query(0),
    exempt_disability_taxpayer: float = Query(0),
    exempt_disability_spouse: float = Query(0),
    # חלק יב — ניכויים
    disability_insurance_self_taxpayer: float = Query(0),
    disability_insurance_self_spouse: float = Query(0),
    disability_insurance_employee_taxpayer: float = Query(0),
    disability_insurance_employee_spouse: float = Query(0),
    education_fund_self_taxpayer: float = Query(0),
    education_fund_self_spouse: float = Query(0),
    pension_self_taxpayer: float = Query(0),
    pension_self_spouse: float = Query(0),
    nii_non_employment_taxpayer: float = Query(0),
    nii_non_employment_spouse: float = Query(0),
    # חלק יג — נקודות זיכוי
    credit_points_taxpayer: float = Query(0),
    credit_points_spouse: float = Query(0),
    children_credit_points_taxpayer: float = Query(0),
    children_credit_points_spouse: float = Query(0),
    single_parent_points: float = Query(0),
    soldier_release_date_taxpayer: str = Query(""),
    soldier_release_date_spouse: str = Query(""),
    soldier_service_months_taxpayer: int = Query(0),
    soldier_service_months_spouse: int = Query(0),
    academic_code_taxpayer: str = Query(""),
    academic_code_spouse: str = Query(""),
    academic_completion_year_taxpayer: int = Query(0),
    academic_completion_year_spouse: int = Query(0),
    academic_study_years_taxpayer: int = Query(0),
    academic_study_years_spouse: int = Query(0),
    # חלק יד — זיכויים
    life_insurance_taxpayer: float = Query(0),
    life_insurance_spouse: float = Query(0),
    survivors_insurance_taxpayer: float = Query(0),
    survivors_insurance_spouse: float = Query(0),
    pension_employee_credit_taxpayer: float = Query(0),
    pension_employee_credit_spouse: float = Query(0),
    pension_self_credit_taxpayer: float = Query(0),
    pension_self_credit_spouse: float = Query(0),
    institution_care_taxpayer: float = Query(0),
    institution_care_spouse: float = Query(0),
    donation_taxpayer: float = Query(0),
    donation_spouse: float = Query(0),
    donation_us_taxpayer: float = Query(0),
    donation_us_spouse: float = Query(0),
    rnd_investment_taxpayer: float = Query(0),
    rnd_investment_spouse: float = Query(0),
    eilat_income_taxpayer: float = Query(0),
    # חלק טו — ניכויים במקור
    rental_tax_paid: float = Query(0),
    withholding_other: float = Query(0),
    land_appreciation_tax: float = Query(0),
    # הוצאות הפקת הכנסה (דמי רו"ח)
    production_expenses_taxpayer: float = Query(0),
    production_expenses_spouse: float = Query(0),
    # הפרשי הצמדה וריבית
    interest_cpi_adjustment: float = Query(0),
):
    result = compute_form1301(
        year=year,
        marital_status=marital_status,
        has_joint_income_source=has_joint_income_source,
        spouse_assists_income=spouse_assists_income,
        taxpayer_gender=taxpayer_gender,
        immigrant_taxpayer_status=immigrant_taxpayer_status,
        immigrant_taxpayer_arrival_date=immigrant_taxpayer_arrival_date,
        immigrant_spouse_status=immigrant_spouse_status,
        immigrant_spouse_arrival_date=immigrant_spouse_arrival_date,
        business_income_taxpayer=business_income_taxpayer,
        business_income_spouse=business_income_spouse,
        nii_self_employed_taxpayer=nii_self_employed_taxpayer,
        nii_self_employed_spouse=nii_self_employed_spouse,
        nii_employee_taxpayer=nii_employee_taxpayer,
        nii_employee_spouse=nii_employee_spouse,
        shift_work_taxpayer=shift_work_taxpayer,
        shift_work_spouse=shift_work_spouse,
        retirement_grants_taxpayer=retirement_grants_taxpayer,
        retirement_grants_spouse=retirement_grants_spouse,
        real_estate_income_taxpayer=real_estate_income_taxpayer,
        real_estate_income_spouse=real_estate_income_spouse,
        other_income_taxpayer=other_income_taxpayer,
        other_income_spouse=other_income_spouse,
        other_income_joint=other_income_joint,
        interest_securities_15_taxpayer=interest_securities_15_taxpayer,
        interest_securities_15_spouse=interest_securities_15_spouse,
        interest_securities_20_taxpayer=interest_securities_20_taxpayer,
        interest_securities_20_spouse=interest_securities_20_spouse,
        interest_securities_25_taxpayer=interest_securities_25_taxpayer,
        interest_securities_25_spouse=interest_securities_25_spouse,
        dividend_preferred_20_taxpayer=dividend_preferred_20_taxpayer,
        dividend_preferred_20_spouse=dividend_preferred_20_spouse,
        dividend_25_taxpayer=dividend_25_taxpayer,
        dividend_25_spouse=dividend_25_spouse,
        dividend_significant_30_taxpayer=dividend_significant_30_taxpayer,
        dividend_significant_30_spouse=dividend_significant_30_spouse,
        interest_deposits_15_taxpayer=interest_deposits_15_taxpayer,
        interest_deposits_15_spouse=interest_deposits_15_spouse,
        interest_deposits_20_taxpayer=interest_deposits_20_taxpayer,
        interest_deposits_20_spouse=interest_deposits_20_spouse,
        interest_deposits_25_taxpayer=interest_deposits_25_taxpayer,
        interest_deposits_25_spouse=interest_deposits_25_spouse,
        rental_10_taxpayer=rental_10_taxpayer,
        rental_10_spouse=rental_10_spouse,
        rental_abroad_15_taxpayer=rental_abroad_15_taxpayer,
        rental_abroad_15_spouse=rental_abroad_15_spouse,
        gambling_35_taxpayer=gambling_35_taxpayer,
        gambling_35_spouse=gambling_35_spouse,
        renewable_energy_31_taxpayer=renewable_energy_31_taxpayer,
        renewable_energy_31_spouse=renewable_energy_31_spouse,
        pension_distribution_20_taxpayer=pension_distribution_20_taxpayer,
        pension_distribution_20_spouse=pension_distribution_20_spouse,
        unauthorized_withdrawal_35_taxpayer=unauthorized_withdrawal_35_taxpayer,
        unauthorized_withdrawal_35_spouse=unauthorized_withdrawal_35_spouse,
        capital_gains=capital_gains,
        crypto_income=crypto_income,
        exempt_rental_income=exempt_rental_income,
        exempt_disability_taxpayer=exempt_disability_taxpayer,
        exempt_disability_spouse=exempt_disability_spouse,
        disability_insurance_self_taxpayer=disability_insurance_self_taxpayer,
        disability_insurance_self_spouse=disability_insurance_self_spouse,
        disability_insurance_employee_taxpayer=disability_insurance_employee_taxpayer,
        disability_insurance_employee_spouse=disability_insurance_employee_spouse,
        education_fund_self_taxpayer=education_fund_self_taxpayer,
        education_fund_self_spouse=education_fund_self_spouse,
        pension_self_taxpayer=pension_self_taxpayer,
        pension_self_spouse=pension_self_spouse,
        nii_non_employment_taxpayer=nii_non_employment_taxpayer,
        nii_non_employment_spouse=nii_non_employment_spouse,
        credit_points_taxpayer=credit_points_taxpayer,
        credit_points_spouse=credit_points_spouse,
        children_credit_points_taxpayer=children_credit_points_taxpayer,
        children_credit_points_spouse=children_credit_points_spouse,
        single_parent_points=single_parent_points,
        soldier_release_date_taxpayer=soldier_release_date_taxpayer,
        soldier_release_date_spouse=soldier_release_date_spouse,
        soldier_service_months_taxpayer=soldier_service_months_taxpayer,
        soldier_service_months_spouse=soldier_service_months_spouse,
        academic_code_taxpayer=academic_code_taxpayer,
        academic_code_spouse=academic_code_spouse,
        academic_completion_year_taxpayer=academic_completion_year_taxpayer,
        academic_completion_year_spouse=academic_completion_year_spouse,
        academic_study_years_taxpayer=academic_study_years_taxpayer,
        academic_study_years_spouse=academic_study_years_spouse,
        life_insurance_taxpayer=life_insurance_taxpayer,
        life_insurance_spouse=life_insurance_spouse,
        survivors_insurance_taxpayer=survivors_insurance_taxpayer,
        survivors_insurance_spouse=survivors_insurance_spouse,
        pension_employee_credit_taxpayer=pension_employee_credit_taxpayer,
        pension_employee_credit_spouse=pension_employee_credit_spouse,
        pension_self_credit_taxpayer=pension_self_credit_taxpayer,
        pension_self_credit_spouse=pension_self_credit_spouse,
        institution_care_taxpayer=institution_care_taxpayer,
        institution_care_spouse=institution_care_spouse,
        donation_taxpayer=donation_taxpayer,
        donation_spouse=donation_spouse,
        donation_us_taxpayer=donation_us_taxpayer,
        donation_us_spouse=donation_us_spouse,
        rnd_investment_taxpayer=rnd_investment_taxpayer,
        rnd_investment_spouse=rnd_investment_spouse,
        eilat_income_taxpayer=eilat_income_taxpayer,
        rental_tax_paid=rental_tax_paid,
        withholding_other=withholding_other,
        land_appreciation_tax=land_appreciation_tax,
        production_expenses_taxpayer=production_expenses_taxpayer,
        production_expenses_spouse=production_expenses_spouse,
        interest_cpi_adjustment=interest_cpi_adjustment,
    )

    return Form1301PreviewResponse(result=result)
