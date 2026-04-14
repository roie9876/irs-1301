"""Tests for Form 1301 calculator service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.form1301 import compute_form1301


def _with_empty_docs(fn):
    """Decorator to run test with an empty documents directory."""
    def wrapper(*args, **kwargs):
        with tempfile.TemporaryDirectory() as d:
            with patch("app.services.form1301.DOCUMENTS_DIR", Path(d)):
                return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@_with_empty_docs
def test_compute_form1301_empty():
    """Compute with no documents and no manual inputs."""
    result = compute_form1301(year=2024)
    assert result.tax_year == 2024
    assert result.income.field_158 == 0
    assert result.calculation.gross_tax == 0
    assert result.calculation.balance == 0
    assert len(result.warnings) > 0  # Should warn about no documents


@_with_empty_docs
def test_compute_form1301_with_manual_inputs():
    """Compute with only manual inputs (rental, dividends)."""
    result = compute_form1301(
        year=2024,
        rental_10_taxpayer=100_000,
        rental_tax_paid=10_000,
        dividend_25_taxpayer=40_000,
    )
    # 10% of 100,000 = 10,000
    assert result.calculation.tax_rental_10pct == 10_000
    # 25% of 40,000 = 10,000
    assert abs(result.calculation.tax_25pct - 10_000) <= 1
    # Withholdings should include rental tax paid
    assert result.withholdings.field_220 == 10_000


@_with_empty_docs
def test_compute_form1301_credit_points_auto():
    """Auto-calculated credit points for basic resident."""
    result = compute_form1301(year=2024)
    # Taxpayer: 2.25 points * 2904 = 6,534
    assert result.calculation.credit_points_amount_taxpayer == 6_534
    # Spouse: 2.75 points * 2904 = 7,986
    assert result.calculation.credit_points_amount_spouse == 7_986


@_with_empty_docs
def test_compute_form1301_credit_points_manual():
    """Manual credit points override auto-calculation."""
    result = compute_form1301(
        year=2024,
        credit_points_taxpayer=6.0,
        credit_points_spouse=4.5,
    )
    # 6 * 2904 = 17,424
    assert result.calculation.credit_points_amount_taxpayer == 17_424
    # 4.5 * 2904 = 13,068
    assert result.calculation.credit_points_amount_spouse == 13_068


@_with_empty_docs
def test_compute_form1301_single_has_no_default_spouse_credit_points():
    """When taxpayer is not married, spouse default credit points should not be added."""
    result = compute_form1301(year=2024, marital_status="רווק")
    assert result.calculation.credit_points_amount_spouse == 0


@_with_empty_docs
def test_compute_form1301_new_immigrant_credit_points_taxpayer():
    """A new immigrant should receive additional auto-calculated credit points in the tax year."""
    result = compute_form1301(
        year=2024,
        immigrant_taxpayer_status="new_immigrant",
        immigrant_taxpayer_arrival_date="2024-01-10",
        marital_status="רווק",
    )
    assert result.calculation.credit_points_amount_taxpayer == 9_438


@_with_empty_docs
def test_compute_form1301_donation_credit():
    """Donation credit at 35%."""
    result = compute_form1301(
        year=2024,
        donation_taxpayer=5_000,
        donation_spouse=3_000,
    )
    # (5000 + 3000) * 0.35 = 2,800
    assert result.calculation.donation_credit == 2_800


@_with_empty_docs
def test_compute_form1301_shift_work_credit_2024():
    """Shift work generates a 15% credit subject to annual caps."""
    result = compute_form1301(
        year=2024,
        shift_work_taxpayer=40_000,
        business_income_taxpayer=0,
    )
    assert result.calculation.shift_work_credit_taxpayer == 6_000


@_with_empty_docs
def test_compute_form1301_shift_work_credit_cap_2022():
    """2022 shift-work credit should honor the yearly maximum credit."""
    result = compute_form1301(
        year=2022,
        shift_work_taxpayer=200_000,
    )
    assert result.calculation.shift_work_credit_taxpayer == 11_520


@_with_empty_docs
def test_compute_form1301_discharged_soldier_credit_points():
    """Discharged soldier points are monthly and start after release month."""
    result = compute_form1301(
        year=2024,
        marital_status="רווק",
        soldier_release_date_taxpayer="2021-08",
        soldier_service_months_taxpayer=30,
    )
    assert result.credit_points.field_024 == 8 / 6
    assert result.calculation.credit_points_amount_taxpayer == 10_406


@_with_empty_docs
def test_compute_form1301_academic_credit_points_ba():
    """Bachelor's degree gives one credit point in each eligible year after completion."""
    result = compute_form1301(
        year=2024,
        marital_status="רווק",
        academic_code_taxpayer="1",
        academic_completion_year_taxpayer=2023,
        academic_study_years_taxpayer=3,
    )
    assert result.calculation.credit_points_amount_taxpayer == 9_438


@_with_empty_docs
def test_compute_form1301_spouse_helper_credit_points_with_children():
    """Joint income source plus spouse assistance should add spouse-helper credit points."""
    with tempfile.TemporaryDirectory() as d:
        docs_dir = Path(d)
        id_payload = {
            "doc_id": "ids",
            "original_filename": "id-supp.jpg",
            "document_type": "id_supplement",
            "extracted": {
                "holder_name": {"value": "Taxpayer", "confidence": 1.0},
                "spouse_name": {"value": "Spouse", "confidence": 1.0},
                "holder_gender": {"value": "male", "confidence": 1.0},
                "children": [{"birth_year": 2018}],
            },
            "user_corrected": False,
        }
        (docs_dir / "id.doc.json").write_text(json.dumps(id_payload), encoding="utf-8")
        with patch("app.services.form1301.DOCUMENTS_DIR", docs_dir):
            result = compute_form1301(
                year=2024,
                marital_status="נשוי",
                has_joint_income_source=True,
                spouse_assists_income=True,
            )
    assert result.credit_points.spouse_helper_points == 1.75


def test_compute_form1301_classifies_second_106_as_spouse_when_spouse_exists():
    """If there are two neutral 106 files and a spouse exists, fallback classification should split them."""
    with tempfile.TemporaryDirectory() as d:
        docs_dir = Path(d)
        docs = [
            {
                "doc_id": "a1",
                "original_filename": "106-primary.pdf",
                "document_type": "form_106",
                "extracted": {
                    "tax_year": {"value": 2024, "confidence": 1.0},
                    "gross_salary": {"value": 500_000, "confidence": 1.0},
                    "tax_withheld": {"value": 100_000, "confidence": 1.0},
                },
                "user_corrected": False,
            },
            {
                "doc_id": "a2",
                "original_filename": "106-secondary.pdf",
                "document_type": "form_106",
                "extracted": {
                    "tax_year": {"value": 2024, "confidence": 1.0},
                    "gross_salary": {"value": 150_000, "confidence": 1.0},
                    "tax_withheld": {"value": 5_000, "confidence": 1.0},
                },
                "user_corrected": False,
            },
            {
                "doc_id": "ids",
                "original_filename": "id-supp.jpg",
                "document_type": "id_supplement",
                "extracted": {
                    "holder_name": {"value": "Taxpayer", "confidence": 1.0},
                    "spouse_name": {"value": "Spouse", "confidence": 1.0},
                    "holder_gender": {"value": "male", "confidence": 1.0},
                    "children": [],
                },
                "user_corrected": False,
            },
        ]
        for index, payload in enumerate(docs):
            (docs_dir / f"doc{index}.doc.json").write_text(json.dumps(payload), encoding="utf-8")

        with patch("app.services.form1301.DOCUMENTS_DIR", docs_dir):
            result = compute_form1301(year=2024)

        assert result.income.field_158 == 500_000
        assert result.income.field_172 == 150_000
        assert any("סיווג טפסי 106" in warning for warning in result.warnings)
