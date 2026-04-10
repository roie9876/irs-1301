from fastapi import APIRouter, HTTPException

from app.schemas.settings import SettingsRequest, SettingsResponse, TestResult
from app.services.llm import test_connection, load_settings, save_settings

router = APIRouter(tags=["settings"])


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
    )
    return SettingsResponse(**load_settings())
