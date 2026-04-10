"""Tests for Form 1301 calculator service."""

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
        rental_income=100_000,
        rental_tax_paid=10_000,
        dividend_income=40_000,
    )
    # 10% of 100,000 = 15,220
    assert result.calculation.tax_rental_10pct == 10_000
    # 25% of 40,000 = 18,374.5 → 18,375
    assert abs(result.calculation.tax_dividend_25pct - 10_000) <= 1
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
def test_compute_form1301_donation_credit():
    """Donation credit at 35%."""
    result = compute_form1301(
        year=2024,
        donation_amount_taxpayer=5_000,
        donation_amount_spouse=3_000,
    )
    # (5000 + 3000) * 0.35 = 2,800
    assert result.calculation.donation_credit == 2_800
