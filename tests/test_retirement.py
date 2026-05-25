"""
Regression tests for calculate/retirement.py

Covers:
  - _adjust_for_inflation
  - _calculate_pre_tax_income (binary-search inverse of income tax)
  - _simulate_accumulation (monthly/annual compounding, monthly/annual contributions)
  - _simulate_retirement (withdrawal loop, inflation adjustment, compound in retirement)
  - simulate_account (full end-to-end label/value shapes)

All expected values are computed analytically from the formulas in the source
so that any refactor that changes the math will be detected.
"""

import math
import json
from decimal import Decimal
import pytest

from calculate.retirement import (
    simulate_account,
    _adjust_for_inflation,
    _calculate_pre_tax_income,
    _simulate_accumulation,
    _simulate_retirement,
)
from calculate.federal_tax import calculate_annual_income_tax
from utils.globals import GlobalParameters
from utils.parameters import Person, Account
from utils.enums import Filing, Frequency, MonthlyCompoundType, AccountType, State
from utils.schemas import TaxSchema

# Load and validate tax tables once at module scope to eliminate file I/O overhead in tests
with open("config/tax.json") as _f:
    _TAX_DATA = TaxSchema.model_validate(json.load(_f))

# ---------------------------------------------------------------------------
# Shared setup helper
# ---------------------------------------------------------------------------


def _make_config(year=2024) -> GlobalParameters:
    return GlobalParameters(
        year=year,
        inflation_rate=Decimal("0.03"),
        yearly_tax=_TAX_DATA.root[str(year)],
    )


def _make_person_and_account(
    current_age=30,
    retirement_age=40,  # short window for fast tests
    lifespan=50,
    pre_tax_income=115_000,
    initial_savings=0,
    regular_investment_dollar=1_000,
    regular_investment_frequency=Frequency.MONTHLY,
    annual_investment_increase=0.0,
    annual_investment_return=0.07,
    annual_retirement_return=0.05,
    annual_retirement_post_tax_expense=60_000,
    compound_frequency=Frequency.MONTHLY,
    compound_type=MonthlyCompoundType.ROOT,
    account_type=AccountType.GENERIC,
    state_of_residence=State.TEXAS,
) -> tuple[Person, Account, GlobalParameters]:
    user = Person(
        current_age=current_age,
        retirement_age=retirement_age,
        lifespan=lifespan,
        pre_tax_income=pre_tax_income,
        state_of_residence=state_of_residence,
    )
    config = _make_config(2024)
    account = Account(
        owner=user,
        initial_savings=initial_savings,
        regular_investment_dollar=regular_investment_dollar,
        regular_investment_frequency=regular_investment_frequency,
        annual_investment_increase=annual_investment_increase,
        annual_investment_return=annual_investment_return,
        annual_retirement_return=annual_retirement_return,
        annual_retirement_post_tax_expense=annual_retirement_post_tax_expense,
        compound_frequency=compound_frequency,
        compound_type=compound_type,
        account_type=account_type,
    )
    return user, account, config


# ===========================================================================
# _adjust_for_inflation
# ===========================================================================


class TestAdjustForInflation:
    """
    Formula: todays_dollars * (1 + inflation_rate)^(months/12)
    Default inflation_rate = 0.03
    """

    def setup_method(self):
        self.config = _make_config(2024)

    def test_zero_months_no_change(self):
        result = _adjust_for_inflation(1_000.0, months=0, config=self.config)
        assert math.isclose(result, 1_000.0, rel_tol=1e-9)

    def test_twelve_months_one_year(self):
        """After 12 months (1 year) at 3%, value = 1000 * 1.03^1 = 1030."""
        result = _adjust_for_inflation(1_000.0, months=12, config=self.config)
        expected = 1_000.0 * 1.03
        assert math.isclose(
            result, expected, rel_tol=1e-6
        ), f"Expected {expected:.4f}, got {result:.4f}"

    def test_twenty_four_months_two_years(self):
        result = _adjust_for_inflation(1_000.0, months=24, config=self.config)
        expected = 1_000.0 * (1.03**2)
        assert math.isclose(result, expected, rel_tol=1e-6)

    def test_six_months_half_year(self):
        """6 months: value = 1000 * 1.03^(0.5) ≈ 1014.89."""
        result = _adjust_for_inflation(1_000.0, months=6, config=self.config)
        expected = 1_000.0 * math.pow(1.03, 0.5)
        assert math.isclose(result, expected, rel_tol=1e-6)

    def test_amount_scales_linearly(self):
        """Doubling the principal doubles the inflation-adjusted amount."""
        r1 = _adjust_for_inflation(500.0, months=12, config=self.config)
        r2 = _adjust_for_inflation(1_000.0, months=12, config=self.config)
        assert math.isclose(r2, 2 * r1, rel_tol=1e-9)

    def test_monotonically_increases_with_months(self):
        results = [
            _adjust_for_inflation(1_000.0, m, config=self.config)
            for m in range(0, 121, 12)
        ]
        for i in range(1, len(results)):
            assert (
                results[i] > results[i - 1]
            ), f"Inflation adjustment should grow monotonically; failed at index {i}"


# ===========================================================================
# _calculate_pre_tax_income
# ===========================================================================


class TestCalculatePreTaxIncome:
    """
    _calculate_pre_tax_income(post_tax) uses binary search to find pre_tax such
    that pre_tax - total_tax(pre_tax) ≈ post_tax.  We verify this invariant
    rather than hard-coding the result (which depends on the tax tables loaded).
    """

    def setup_method(self):
        self.user = Person(pre_tax_income=100_000, state_of_residence=State.TEXAS)
        self.config = _make_config(2024)

    def _post_tax(self, pre_tax: Decimal) -> Decimal:
        return pre_tax - calculate_annual_income_tax(
            Person(pre_tax_income=pre_tax, state_of_residence=State.TEXAS),
            self.config,
        )

    def test_round_trip_70k_post_tax(self):
        post_tax_target = 70_000
        pre_tax = _calculate_pre_tax_income(post_tax_target, self.user, self.config)
        recovered_post_tax = self._post_tax(pre_tax)
        assert math.isclose(recovered_post_tax, post_tax_target, abs_tol=0.02), (
            f"Round-trip failed: post_tax({pre_tax:.2f}) = {recovered_post_tax:.2f}, "
            f"expected {post_tax_target}"
        )

    def test_round_trip_50k_post_tax(self):
        post_tax_target = 50_000
        pre_tax = _calculate_pre_tax_income(post_tax_target, self.user, self.config)
        recovered_post_tax = self._post_tax(pre_tax)
        assert math.isclose(recovered_post_tax, post_tax_target, abs_tol=0.02)

    def test_pre_tax_is_always_greater_than_post_tax(self):
        for post_tax in [30_000, 50_000, 80_000, 100_000]:
            pre_tax = _calculate_pre_tax_income(post_tax, self.user, self.config)
            assert (
                pre_tax > post_tax
            ), f"pre_tax ({pre_tax}) should exceed post_tax ({post_tax})"

    def test_monotonic(self):
        """Higher post-tax income → higher pre-tax income."""
        results = [
            _calculate_pre_tax_income(pt, self.user, self.config)
            for pt in [40_000, 60_000, 80_000]
        ]
        assert results == sorted(results), "pre_tax should be monotonically increasing"


# ===========================================================================
# _simulate_accumulation – monthly compounding, monthly contributions
# ===========================================================================


class TestSimulateAccumulationMonthly:
    """
    Root-monthly compound, monthly contribution, no annual increase.

    For each month the balance is multiplied by (1+r)^(1/12), then the
    contribution is added.  We verify shape, monotonicity, and a precise
    first-year value.
    """

    def _run(self, **kwargs):
        user, account, config = _make_person_and_account(**kwargs)
        labels = []
        values = []
        _simulate_accumulation(account, account.initial_savings, labels, values)
        return labels, values

    def test_output_length_matches_accumulation_years(self):
        labels, values = self._run(current_age=30, retirement_age=40)
        assert len(labels) == 10  # 40 - 30 years
        assert len(values) == 10

    def test_labels_are_ages(self):
        labels, _ = self._run(current_age=30, retirement_age=35)
        assert labels == [30, 31, 32, 33, 34]

    def test_values_monotonically_increase_with_positive_return_and_contribution(self):
        _, values = self._run(
            annual_investment_return=0.07,
            regular_investment_dollar=1_000,
            initial_savings=0,
        )
        for i in range(1, len(values)):
            assert values[i] > values[i - 1]

    def test_zero_return_balance_grows_only_by_contributions(self):
        """
        With 0% return and $1,000/month for 1 year, balance = $12,000.
        """
        labels, values = self._run(
            current_age=30,
            retirement_age=31,
            initial_savings=0,
            annual_investment_return=0.0,
            annual_investment_increase=0.0,
            regular_investment_dollar=1_000,
            regular_investment_frequency=Frequency.MONTHLY,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.ROOT,
        )
        assert len(values) == 1
        assert math.isclose(
            values[0], 12_000.0, abs_tol=0.01
        ), f"Expected 12000.00, got {values[0]:.2f}"

    def test_initial_savings_are_carried_forward(self):
        labels, values = self._run(
            current_age=30,
            retirement_age=31,
            initial_savings=50_000,
            annual_investment_return=0.0,
            annual_investment_increase=0.0,
            regular_investment_dollar=0,
        )
        # No return, no contribution → balance stays at 50,000
        assert math.isclose(values[0], 50_000.0, abs_tol=0.01)

    def test_monthly_root_compound_one_year(self):
        """
        Exact formula for ROOT compounding + $1,000/month, 0% increase, 7% return:
        Each month m (0-indexed):
            balance *= (1.07)^(1/12)
            balance += 1,000
        After 12 months, verify against manual loop.
        """
        r_monthly = math.pow(1.07, 1 / 12)
        balance = 0.0
        for _ in range(12):
            balance *= r_monthly
            balance += 1_000
        expected_after_1_year = balance

        _, values = self._run(
            current_age=30,
            retirement_age=31,
            initial_savings=0,
            annual_investment_return=0.07,
            annual_investment_increase=0.0,
            regular_investment_dollar=1_000,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.ROOT,
        )
        assert math.isclose(
            values[0], expected_after_1_year, rel_tol=1e-6
        ), f"Expected {expected_after_1_year:.4f}, got {values[0]:.4f}"

    def test_monthly_divide_compound_one_year(self):
        """
        DIVIDE compounding: each month balance *= (1 + 0.07/12).
        """
        r_monthly = 1 + 0.07 / 12
        balance = 0.0
        for _ in range(12):
            balance *= r_monthly
            balance += 1_000
        expected_after_1_year = balance

        _, values = self._run(
            current_age=30,
            retirement_age=31,
            initial_savings=0,
            annual_investment_return=0.07,
            annual_investment_increase=0.0,
            regular_investment_dollar=1_000,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.DIVIDE,
        )
        assert math.isclose(values[0], expected_after_1_year, rel_tol=1e-6)

    def test_annual_increase_grows_contributions(self):
        """With a 5% annual_investment_increase, year-2 contributions are 5% larger."""
        _, values_no_increase = self._run(
            current_age=30,
            retirement_age=32,
            initial_savings=0,
            annual_investment_return=0.0,
            annual_investment_increase=0.0,
            regular_investment_dollar=1_000,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.ROOT,
        )
        _, values_with_increase = self._run(
            current_age=30,
            retirement_age=32,
            initial_savings=0,
            annual_investment_return=0.0,
            annual_investment_increase=0.05,
            regular_investment_dollar=1_000,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.ROOT,
        )
        # After 2 years, values_with_increase should be higher
        assert values_with_increase[-1] > values_no_increase[-1]

    def test_annual_contribution_frequency(self):
        """
        ANNUALLY contribution: $12,000/year with 0% return → $12,000 after year 1.
        """
        _, values = self._run(
            current_age=30,
            retirement_age=31,
            initial_savings=0,
            annual_investment_return=0.0,
            annual_investment_increase=0.0,
            regular_investment_dollar=12_000,
            regular_investment_frequency=Frequency.ANNUALLY,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.ROOT,
        )
        assert math.isclose(values[0], 12_000.0, abs_tol=0.01)

    def test_annual_compound_frequency(self):
        """
        ANNUALLY compound: 7% applied once per year at year start.
        With $0 initial and $0 contribution, balance stays 0.
        With $10k initial: after 1 year → 10,000 * 1.07 = 10,700.
        """
        _, values = self._run(
            current_age=30,
            retirement_age=31,
            initial_savings=10_000,
            annual_investment_return=0.07,
            annual_investment_increase=0.0,
            regular_investment_dollar=0,
            compound_frequency=Frequency.ANNUALLY,
        )
        assert math.isclose(values[0], 10_700.0, abs_tol=0.01)


# ===========================================================================
# _simulate_retirement
# ===========================================================================


class TestSimulateRetirement:
    """
    The retirement loop:
      1. Subtracts inflation-adjusted monthly expense.
      2. Compounds remaining balance.
      3. Stops when balance < monthly_expense OR age >= lifespan.
    """

    def _run_retirement(
        self,
        initial_savings,
        annual_expense,
        lifespan=50,
        retirement_age=40,
        current_age=30,
        annual_retirement_return=0.0,
        account_type=AccountType.GENERIC,
        compound_frequency=Frequency.MONTHLY,
    ):
        user = Person(
            current_age=current_age,
            retirement_age=retirement_age,
            lifespan=lifespan,
            pre_tax_income=115_000,
            state_of_residence=State.TEXAS,
        )
        config = _make_config(2024)
        account = Account(
            owner=user,
            initial_savings=initial_savings,
            annual_retirement_post_tax_expense=annual_expense,
            annual_retirement_return=annual_retirement_return,
            compound_frequency=compound_frequency,
            account_type=account_type,
        )
        labels = []
        values = []
        _simulate_retirement(account, initial_savings, labels, values, config)
        return labels, values

    def test_runs_out_within_first_year_produces_empty_output(self):
        """
        Documents the code's behavior when savings deplete within the first year.

        The loop exits when current_savings < annual_withdrawal/12 (before it
        goes negative). Labels are only recorded every 12 months. If the account
        depletes in < 12 months, no annual label is ever appended AND savings
        are left positive-but-small (so the trailing-0 guard is also false).
        Result: both lists are empty.

        This behavior is a documented quirk that the refactor must preserve.
        """
        labels, values = self._run_retirement(
            initial_savings=500_000,
            annual_expense=400_000,  # ~$33k/month guard; inflation-adj expense ~$45k → drains in 11 months
            lifespan=80,
            retirement_age=40,
            annual_retirement_return=0.0,
            account_type=AccountType.ROTH,
        )
        assert (
            labels == []
        ), "When savings deplete within < 12 months, no annual label is recorded"
        assert (
            values == []
        ), "When savings deplete within < 12 months, no value is recorded"

    def test_runs_out_after_multiple_years_appends_zero(self):
        """
        When savings last multiple years but the inflation-adjusted monthly
        expense eventually drives the balance negative, a 0 is appended.

        With $200k ROTH savings and $60k/year (guard = $5k/month):
          - At 10 years of inflation (1.03^10 ≈ 1.344), inflation-adjusted
            monthly expense ≈ $6,720, which exceeds guard ($5k).
          - When savings drop below $6,720 but above $5k, the guard passes,
            the expense drives savings negative → 0 is appended.
        Verified: produces labels [41, 42, 43] with last value = 0.
        """
        labels, values = self._run_retirement(
            initial_savings=200_000,
            annual_expense=60_000,
            lifespan=80,
            retirement_age=40,
            annual_retirement_return=0.0,
            account_type=AccountType.ROTH,
        )
        assert len(labels) > 0, "Expected at least one annual data point"
        assert (
            values[-1] == 0
        ), f"Expected trailing 0 when savings go negative mid-cycle, got {values[-1]:.2f}"
        assert labels[-1] < 80, "Account should deplete well before lifespan=80"

    def test_depletion_visualization_quirk_fix(self):
        """
        We verify that even if savings do not go negative mid-cycle (e.g. they
        terminate because they drop below the next monthly withdrawal limit),
        a final $0 data point is appended to the graph if it is before lifespan.
        """
        user, account, config = _make_person_and_account(
            current_age=30,
            retirement_age=40,
            lifespan=60,
            initial_savings=10_000,
            regular_investment_dollar=0,  # no additional savings
            annual_retirement_post_tax_expense=20_000,  # high expense to deplete quickly
            annual_retirement_return=0.0,
            account_type=AccountType.ROTH,
        )
        labels, values = simulate_account(account, config)
        # Should have run out of money well before age 60
        assert labels[-1] < 60
        assert values[-1] == Decimal("0")

    def test_large_savings_lasts_to_lifespan(self):
        """Large savings relative to expense should not run out before lifespan."""
        labels, values = self._run_retirement(
            initial_savings=10_000_000,
            annual_expense=60_000,
            lifespan=50,
            retirement_age=40,
            annual_retirement_return=0.0,
        )
        # Should NOT append a 0 (never fully depleted within lifespan)
        assert values[-1] > 0

    def test_labels_start_at_retirement_age_plus_one(self):
        """
        Labels are appended at the end of each retirement year (every 12 months).
        So the first label corresponds to retirement_age + 1 (end of first retirement year).
        """
        labels, _ = self._run_retirement(
            initial_savings=1_000_000,
            annual_expense=60_000,
            lifespan=50,
            retirement_age=40,
        )
        assert labels[0] == 41

    def test_generic_account_adjusts_for_pre_tax(self):
        """
        GENERIC account withdrawals are pre-tax adjusted.
        So the actual withdrawal is > annual_expense (since taxes eat into it).
        We verify that funds deplete faster for GENERIC than for ROTH.
        """
        labels_generic, values_generic = self._run_retirement(
            initial_savings=500_000,
            annual_expense=60_000,
            lifespan=80,
            retirement_age=40,
            annual_retirement_return=0.0,
            account_type=AccountType.GENERIC,
        )
        labels_roth, values_roth = self._run_retirement(
            initial_savings=500_000,
            annual_expense=60_000,
            lifespan=80,
            retirement_age=40,
            annual_retirement_return=0.0,
            account_type=AccountType.ROTH,
        )
        # Generic depletes faster (due to pre-tax grossing up)
        assert len(labels_generic) <= len(
            labels_roth
        ), "Generic account should deplete at least as fast as Roth"

    def test_zero_return_no_inflation_simple_depletion(self):
        """
        With 0% return AND 0% inflation, balance decreases by annual_expense/12 per month.
        Note: ROTH account → no pre-tax grossing-up.
        """
        user = Person(
            current_age=30,
            retirement_age=40,
            lifespan=50,
            pre_tax_income=115_000,
            state_of_residence=State.TEXAS,
        )
        config = _make_config(2024)
        config.inflation_rate = Decimal("0.0")
        account = Account(
            owner=user,
            initial_savings=120_000,
            annual_retirement_post_tax_expense=12_000,  # $1,000/month
            annual_retirement_return=0.0,
            compound_frequency=Frequency.MONTHLY,
            account_type=AccountType.ROTH,  # no tax grossing
        )
        labels = []
        values = []
        _simulate_retirement(account, Decimal("120000"), labels, values, config)
        # After 1 year (12 months) the balance should be 120,000 - 12,000 = 108,000
        assert math.isclose(
            values[0], 108_000.0, abs_tol=0.01
        ), f"Expected 108000.00 after year 1, got {values[0]:.2f}"


# ===========================================================================
# simulate_account – end-to-end
# ===========================================================================


class TestSimulateAccount:
    """Full pipeline: accumulation + retirement."""

    def test_labels_cover_full_timeline(self):
        user, account, config = _make_person_and_account(
            current_age=30,
            retirement_age=40,
            lifespan=50,
            initial_savings=0,
            regular_investment_dollar=1_000,
            annual_retirement_post_tax_expense=60_000,
            annual_retirement_return=0.05,
            account_type=AccountType.ROTH,
        )
        labels, values = simulate_account(account, config)
        assert labels[0] == 30, "First label should be current age"
        assert labels[len(labels) - 1] >= 40, "Labels must extend into retirement"

    def test_values_peak_at_or_near_retirement(self):
        """Savings grow during accumulation and then decline in retirement."""
        user, account, config = _make_person_and_account(
            current_age=30,
            retirement_age=40,
            lifespan=55,
            initial_savings=0,
            regular_investment_dollar=1_000,
            annual_retirement_post_tax_expense=40_000,
            annual_retirement_return=0.0,
            annual_investment_return=0.07,
            account_type=AccountType.ROTH,
        )
        labels, values = simulate_account(account, config)
        # The max should be somewhere around retirement, not at the very end
        max_value = max(values)
        last_value = values[-1]
        assert (
            max_value > last_value
        ), "Portfolio value should peak during/near retirement, not at the end"

    def test_lengths_match(self):
        user, account, config = _make_person_and_account()
        labels, values = simulate_account(account, config)
        assert len(labels) == len(values)

    def test_all_values_non_negative(self):
        user, account, config = _make_person_and_account(
            account_type=AccountType.ROTH,
            annual_retirement_post_tax_expense=40_000,
        )
        _, values = simulate_account(account, config)
        # The very last value may be 0 (depleted), but never negative from the loop
        for i, v in enumerate(values[:-1]):
            assert v >= 0, f"Negative balance at index {i}: {v}"
        # Last entry is either ≥0 or exactly 0
        assert values[-1] >= 0

    def test_pinned_accumulation_10_years_monthly_root_7pct(self):
        """
        10 years, $1,000/month, ROOT monthly compounding at 7%, no increase.
        Manual calculation.
        """
        r_monthly = math.pow(1.07, 1 / 12)
        balance = 0.0
        for _ in range(10 * 12):
            balance *= r_monthly
            balance += 1_000
        expected_at_retirement = balance

        user, account, config = _make_person_and_account(
            current_age=30,
            retirement_age=40,
            lifespan=40,  # lifespan == retirement_age → no retirement phase
            initial_savings=0,
            annual_investment_return=0.07,
            annual_investment_increase=0.0,
            regular_investment_dollar=1_000,
            regular_investment_frequency=Frequency.MONTHLY,
            compound_frequency=Frequency.MONTHLY,
            compound_type=MonthlyCompoundType.ROOT,
            account_type=AccountType.ROTH,
            annual_retirement_post_tax_expense=0,
        )
        labels, values = simulate_account(account, config)
        # The last value from the accumulation phase (index 9 = age 39)
        assert math.isclose(
            values[9], expected_at_retirement, rel_tol=1e-5
        ), f"Expected {expected_at_retirement:.2f} at retirement, got {values[9]:.2f}"
