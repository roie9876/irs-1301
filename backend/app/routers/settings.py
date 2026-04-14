from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.settings import SettingsRequest, SettingsResponse, TestResult, TaxYearRequest
from app.services.llm import test_connection, load_settings, save_settings
from app.services.tax_rules import TAX_RULES, TAX_RULES_JSON, reload_rules

router = APIRouter(tags=["settings"])


@router.get("/settings/supported-years")
async def get_supported_years():
    """Return the list of tax years with defined rules."""
    return {"years": sorted(TAX_RULES.keys(), reverse=True)}


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    settings = load_settings()
    return SettingsResponse(**settings)


@router.post("/settings/test", response_model=TestResult)
async def test_settings(request: SettingsRequest):
    try:
        await test_connection(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            api_base=request.api_base,
        )
        return TestResult(success=True, message="חיבור תקין")
    except Exception as e:
        return TestResult(success=False, message=str(e))


@router.post("/settings", response_model=SettingsResponse)
async def save_settings_endpoint(request: SettingsRequest):
    # Per D-10: validate connection before saving
    try:
        await test_connection(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            api_base=request.api_base,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"חיבור נכשל: {e}")

    save_settings(
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        api_base=request.api_base,
        tax_year=request.tax_year,
    )
    return SettingsResponse(**load_settings())


@router.put("/settings/tax-year", response_model=SettingsResponse)
async def update_tax_year(request: TaxYearRequest):
    save_settings(
        provider="", model="", api_key="", tax_year=request.tax_year
    )
    return SettingsResponse(**load_settings())


class CreateYearRequest(BaseModel):
    year: int


@router.post("/settings/create-tax-year")
async def create_tax_year(request: CreateYearRequest):
    """Create a new tax year by copying the latest existing year's rules."""
    import json

    year = request.year
    if year in TAX_RULES:
        raise HTTPException(status_code=400, detail=f"שנת {year} כבר קיימת")
    if year < 2020 or year > 2040:
        raise HTTPException(status_code=400, detail="שנה לא תקינה")

    # Load current JSON
    data = json.loads(TAX_RULES_JSON.read_text(encoding="utf-8"))

    # Copy from the latest existing year
    latest_year = max(int(k) for k in data if not k.startswith("_"))
    new_rules = json.loads(json.dumps(data[str(latest_year)]))

    # Save
    data[str(year)] = new_rules
    TAX_RULES_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Reload in-memory rules
    reload_rules()

    return {"years": sorted(TAX_RULES.keys(), reverse=True)}
