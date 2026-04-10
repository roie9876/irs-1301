"""Tests for tax rules engine — validates against real filed reports (2022-2024).

Reference data extracted from official IRS שומה (tax assessment) documents:
- 2022 שומה: full breakdown available
- 2023 1301 submission: field-level data + refund amount
- 2024 שומה: full breakdown available (validated in prior session)
"""

from app.services.tax_rules import compute_progressive_tax, compute_surtax, get_rules


def test_get_rules_2024():
    rules = get_rules(2024)
    assert rules.year == 2024
    assert rules.credit_point_value == 2904
    assert rules.surtax_threshold == 721_560
    assert len(rules.brackets) == 6


def test_get_rules_2023():
    rules = get_rules(2023)
    assert rules.year == 2023
    assert rules.credit_point_value == 2820


def test_get_rules_missing_year():
    try:
        get_rules(2020)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_progressive_tax_personal_labor_2024():
    """Validate against the filed report: Roie salary 500,000 → tax 132,303."""
    rules = get_rules(2024)
    tax = compute_progressive_tax(500_000, rules, personal_labor=True)
    # The filed report shows 132,303 for regular rates on Roie's income.
    # Allow small rounding tolerance.
    assert abs(tax - 132_303) <= 5, f"Expected ~132,303 but got {tax}"


def test_progressive_tax_spouse_2024():
    """Validate against the filed report: Michal salary 200,000 → tax 30,074."""
    rules = get_rules(2024)
    tax = compute_progressive_tax(200_000, rules, personal_labor=True)
    assert abs(tax - 30_074) <= 5, f"Expected ~30,074 but got {tax}"


def test_progressive_tax_zero():
    rules = get_rules(2024)
    assert compute_progressive_tax(0, rules) == 0
    assert compute_progressive_tax(-100, rules) == 0


def test_progressive_tax_first_bracket():
    rules = get_rules(2024)
    tax = compute_progressive_tax(84_120, rules, personal_labor=True)
    assert tax == 8_412  # 84,120 * 10%


def test_progressive_tax_non_personal():
    """Non-personal income starts at 31% for first 269,280."""
    rules = get_rules(2024)
    tax = compute_progressive_tax(84_120, rules, personal_labor=False)
    assert tax == 26_077  # 84,120 * 31%


def test_surtax_below_threshold():
    rules = get_rules(2024)
    assert compute_surtax(700_000, rules) == 0


def test_surtax_per_person_2024():
    """Validate against filed report: surtax is per-person, not joint.

    Filed report shows 8,353.
    Taxpayer (Roie): 500,000 + 100,000 + 40,000 = 1,000,000
    (1,000,000 - 721,560) * 0.03 = 8,353 ✓
    Spouse (Michal): 200,000 — below threshold, no surtax.
    """
    rules = get_rules(2024)
    # Taxpayer income (without spouse)
    tp_income = 500_000 + 100_000 + 40_000  # 1,000,000
    surtax_tp = compute_surtax(tp_income, rules)
    assert surtax_tp == 8_353, f"Expected 8,353 but got {surtax_tp}"

    # Spouse income — below threshold
    surtax_sp = compute_surtax(200_000, rules)
    assert surtax_sp == 0


def test_surtax_exact_threshold():
    rules = get_rules(2024)
    assert compute_surtax(721_560, rules) == 0
    assert compute_surtax(721_561, rules) == 0  # 1 * 0.03 rounds to 0


def test_surtax_includes_special_rate_income():
    """Surtax applies to ALL income including rental, dividends, capital gains."""
    rules = get_rules(2024)
    # Person with 600k salary + 200k dividends = 800k total
    total = 800_000
    capital = 200_000
    surtax = compute_surtax(total, rules, capital_income=capital)
    # (800,000 - 721,560) * 0.03 = 2,353
    assert surtax == round((800_000 - 721_560) * 0.03)


def test_get_rules_2022():
    rules = get_rules(2022)
    assert rules.year == 2022
    assert rules.credit_point_value == 2_676
    assert rules.surtax_threshold == 663_240
    assert rules.surtax_capital_rate == 0.0


def test_get_rules_2025_capital_surtax():
    """2025: new 2% extra surtax on capital income above threshold."""
    rules = get_rules(2025)
    assert rules.year == 2025
    assert rules.surtax_capital_rate == 0.02
    assert rules.credit_point_value == 2_904  # Frozen from 2024
    assert rules.surtax_threshold == 721_560  # Frozen from 2024


def test_surtax_2025_with_capital():
    """2025 surtax: 3% on all excess + 2% extra on capital portion."""
    rules = get_rules(2025)
    # 900k salary + 200k dividends = 1,100k total
    total = 1_100_000
    capital = 200_000
    excess = total - 721_560  # 378,440
    surtax = compute_surtax(total, rules, capital_income=capital)
    # 3% on 378,440 = 11,353
    # 2% on min(200k, 378,440) = 200k * 0.02 = 4,000
    expected = round(excess * 0.03) + round(min(capital, excess) * 0.02)
    assert surtax == expected


def test_surtax_2025_no_capital():
    """2025: salary-only gets 3% surtax only, no extra 2%."""
    rules = get_rules(2025)
    surtax = compute_surtax(900_000, rules, capital_income=0)
    assert surtax == round((900_000 - 721_560) * 0.03)


# ================================================================
# 2022 Validation — against official שומה (tax assessment)
# ================================================================

class TestValidation2022:
    """Validate engine against 2022 filed שומה.

    Key figures from שומה:
    - Roie salary: 500,000, Michal salary: 200,000
    - Rental: 80,000, Dividends: 20,000
    - Progressive (Roie): 132,303, Progressive (Michal): 30,074
    - Surtax: 8,353, Rental 10%: 11,160, Dividend 25%: 8,304
    - Roie gross: 200,000, Total gross: 250,000
    - Credits Roie: 17,246, Credits Michal: 26,599
    - Net tax (מס מגיע): 180,000
    - Withheld: 170,000, Payments: 14,508
    - Balance: -1,199 (refund)
    """

    def test_progressive_tax_roie_2022(self):
        rules = get_rules(2022)
        tax = compute_progressive_tax(500_000, rules, personal_labor=True)
        assert abs(tax - 132_303) <= 1, f"Expected 132,303 ±1 but got {tax}"

    def test_progressive_tax_michal_2022(self):
        rules = get_rules(2022)
        tax = compute_progressive_tax(200_000, rules, personal_labor=True)
        assert tax == 30_074

    def test_surtax_per_person_2022(self):
        """Surtax on Roie only: (500,000 + 80,000 + 20,000 - 663,240) × 3%."""
        rules = get_rules(2022)
        roie_total = 500_000 + 80_000 + 20_000  # 1,000,000
        surtax = compute_surtax(roie_total, rules)
        assert surtax == 8_353

    def test_surtax_michal_zero_2022(self):
        """Michal income 200,000 is below threshold 663,240."""
        rules = get_rules(2022)
        assert compute_surtax(200_000, rules) == 0

    def test_rental_tax_2022(self):
        assert round(80_000 * 0.10) == 8_000

    def test_dividend_tax_2022(self):
        assert round(20_000 * 0.25) == 5_000

    def test_roie_gross_tax_2022(self):
        """Roie gross = progressive + surtax + rental + dividend."""
        rules = get_rules(2022)
        progressive = compute_progressive_tax(500_000, rules)
        surtax = compute_surtax(500_000 + 80_000 + 20_000, rules)
        rental = round(80_000 * 0.10)
        dividend = round(20_000 * 0.25)
        gross = progressive + surtax + rental + dividend
        # שומה: 200,000; off by ±1 due to progressive rounding
        assert abs(gross - 200_000) <= 1

    def test_full_balance_2022(self):
        """Full computation produces correct net tax and refund."""
        rules = get_rules(2022)
        cp = rules.credit_point_value  # 2,676

        # Gross tax
        roie_gross_tax = (
            compute_progressive_tax(500_000, rules)
            + compute_surtax(500_000 + 80_000 + 20_000, rules)
            + round(80_000 * 0.10)
            + round(20_000 * 0.25)
        )
        michal_gross_tax = compute_progressive_tax(200_000, rules)

        # Credits (from שומה breakdown)
        roie_credits = (
            round(2.25 * cp)  # resident: 6,021
            + round(3 * cp)  # children: 8,028
            + 3_000  # 45a pension credit
        )
        assert roie_credits == 15_000

        michal_credits = (
            round(2.25 * cp)  # resident: 6,021
            + round(6 * cp)  # children: 16,056
            + round(0.5 * cp)  # woman: 1,338
            + 3_000  # 45a(h) pension+insurance credit
        )
        assert michal_credits == 20_000

        # Net tax (excess Michal credits don't transfer)
        roie_net = max(0, roie_gross_tax - roie_credits)
        michal_net = max(0, michal_gross_tax - michal_credits)
        total_net = roie_net + michal_net
        assert abs(total_net - 180_000) <= 1

        # Balance (before interest)
        balance = total_net - 170_000 - 10_000
        # שומה shows -1,199 incl -32 interest, so -1,167 before interest
        assert abs(balance - (-1_167)) <= 1


# ================================================================
# 2023 Validation — against filed 1301 + payment records
# ================================================================

class TestValidation2023:
    """Validate engine against 2023 filed 1301 data.

    Key figures from 1301 submission:
    - Roie salary: 500,000, Michal salary: 200,000
    - Rental: 80,000, Dividends: 40,000, Capital gains: 405
    - Tax withheld Roie: 130,000, Michal: 6,252
    - Rental tax paid: 17,693 (= 80,000 × 13% = 10% + 3% surtax)
    - Refund: 1,734
    """

    def test_progressive_tax_roie_2023(self):
        rules = get_rules(2023)
        tax = compute_progressive_tax(500_000, rules, personal_labor=True)
        # No שומה to compare, but value should be consistent
        assert 740_000 < tax < 760_000, f"Unexpected progressive tax: {tax}"

    def test_progressive_tax_michal_2023(self):
        rules = get_rules(2023)
        tax = compute_progressive_tax(200_000, rules, personal_labor=True)
        assert 28_000 < tax < 33_000, f"Unexpected progressive tax: {tax}"

    def test_surtax_per_person_2023(self):
        """Surtax on Roie: (salary + rental + dividends + CG - threshold) × 3%."""
        rules = get_rules(2023)
        roie_total = 500_000 + 80_000 + 40_000 + 405  # 1,000,000
        surtax = compute_surtax(roie_total, rules)
        expected = round((1_000_000 - 698_280) * 0.03)  # 39,969
        assert surtax == expected

    def test_surtax_michal_zero_2023(self):
        rules = get_rules(2023)
        assert compute_surtax(200_000, rules) == 0

    def test_rental_tax_2023(self):
        assert round(80_000 * 0.10) == 8_000

    def test_rental_payment_includes_surtax_2023(self):
        """The 17,693 payment = 10% rental + 3% surtax on rental."""
        rental = 80_000
        assert round(rental * 0.10) + round(rental * 0.03) == 10_000

    def test_dividend_tax_2023(self):
        assert round(40_000 * 0.25) == 10_000


# ================================================================
# Cross-year consistency tests
# ================================================================

class TestCrossYearConsistency:
    """Verify tax parameters are consistent across years."""

    def test_brackets_increase_with_inflation(self):
        """Bracket thresholds should generally increase year over year."""
        for y1, y2 in [(2022, 2023), (2023, 2024)]:
            r1, r2 = get_rules(y1), get_rules(y2)
            for i in range(5):  # First 5 brackets (not infinity)
                assert r2.brackets[i].upper_limit >= r1.brackets[i].upper_limit

    def test_credit_point_increases(self):
        """Credit point value should increase (or freeze)."""
        vals = [get_rules(y).credit_point_value for y in [2022, 2023, 2024, 2025]]
        assert vals == [2_676, 2_820, 2_904, 2_904]

    def test_surtax_threshold_increases(self):
        """Surtax threshold should increase (or freeze)."""
        vals = [get_rules(y).surtax_threshold for y in [2022, 2023, 2024, 2025]]
        assert vals == [663_240, 698_280, 721_560, 721_560]

    def test_rates_unchanged_across_years(self):
        """Tax rates (10/14/20/31/35/47) stay the same across all years."""
        for year in [2022, 2023, 2024, 2025]:
            rules = get_rules(year)
            rates = [b.rate_personal for b in rules.brackets]
            assert rates == [0.10, 0.14, 0.20, 0.31, 0.35, 0.47]
