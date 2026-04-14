"""Tests for tax rules engine — brackets, surtax, credit points, cross-year consistency."""

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


def test_progressive_tax_mid_range_2024():
    """Progressive tax on a mid-range salary spanning multiple brackets."""
    rules = get_rules(2024)
    tax = compute_progressive_tax(500_000, rules, personal_labor=True)
    # Brackets: 8,412 + 5,124 + 14,616 + 23,399 + 80,752 = 132,303
    assert abs(tax - 132_303) <= 5, f"Expected ~132,303 but got {tax}"


def test_progressive_tax_lower_range_2024():
    """Progressive tax on a lower salary spanning 4 brackets."""
    rules = get_rules(2024)
    tax = compute_progressive_tax(200_000, rules, personal_labor=True)
    # Brackets: 8,412 + 5,124 + 14,616 + 1,922 = 30,074
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


def test_surtax_above_threshold_2024():
    """Surtax applies at 3% on income above threshold."""
    rules = get_rules(2024)
    # Fictional income: 900k salary + 80k rental + 20k dividends = 1,000k
    total = 1_000_000
    surtax = compute_surtax(total, rules)
    expected = round((1_000_000 - 721_560) * 0.03)  # 8,353
    assert surtax == expected

    # Income below threshold
    assert compute_surtax(600_000, rules) == 0


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
# Real-data validation tests moved to test_validation_private.py
# (gitignored — contains personal financial data)
# ================================================================


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
