from fastapi import APIRouter, Query

from app.schemas.form1301 import Form1301PreviewResponse
from app.services.form1301 import compute_form1301

router = APIRouter(tags=["form1301"])


@router.get("/form-1301/preview", response_model=Form1301PreviewResponse)
async def preview_form1301(
    year: int = Query(2024, description="Tax year"),
    rental_income: float = Query(0, description="Rental income at 10%"),
    rental_tax_paid: float = Query(0, description="Rental tax already paid"),
    dividend_income: float = Query(0, description="Dividend income"),
    interest_income: float = Query(0, description="Interest income"),
    capital_gains: float = Query(0, description="Capital gains"),
    donation_taxpayer: float = Query(0, description="Donations — taxpayer"),
    donation_spouse: float = Query(0, description="Donations — spouse"),
    life_insurance_taxpayer: float = Query(0, description="Life insurance premium — taxpayer"),
    life_insurance_spouse: float = Query(0, description="Life insurance premium — spouse"),
    credit_points_taxpayer: float = Query(0, description="Credit points — taxpayer (0=auto)"),
    credit_points_spouse: float = Query(0, description="Credit points — spouse (0=auto)"),
):
    result = compute_form1301(
        year=year,
        rental_income=rental_income,
        rental_tax_paid=rental_tax_paid,
        dividend_income=dividend_income,
        interest_income=interest_income,
        capital_gains=capital_gains,
        donation_amount_taxpayer=donation_taxpayer,
        donation_amount_spouse=donation_spouse,
        life_insurance_taxpayer=life_insurance_taxpayer,
        life_insurance_spouse=life_insurance_spouse,
        credit_points_taxpayer=credit_points_taxpayer,
        credit_points_spouse=credit_points_spouse,
    )

    return Form1301PreviewResponse(result=result)
