"""
Regression tests for calculate/retirement.py

Covers:
  - _adjust_for_inflation
  - _calculate_pre_tax_income (binary-search inverse of income tax)
  - _simulate_accumulation (monthly/annual compounding, monthly/annual contributions)
  - _simulate_retirement (withdrawal loop, inflation adjustment, compound in retirement)
  - simulate (full end-to-end label/value shapes)

All expected values are computed analytically from the formulas in the source
so that any refactor that changes the math will be detected.
"""

import math
import json
from decimal import Decimal

from utils.accounts.base import _adjust_for_inflation
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
    cost_basis=None,
) -> tuple[Person, Account, GlobalParameters]:
    user = Person(
        current_age=current_age,
        retirement_age=retirement_age,
        lifespan=lifespan,
        pre_tax_income=pre_tax_income,
        annual_retirement_post_tax_expense=annual_retirement_post_tax_expense,
        state_of_residence=state_of_residence,
    )
    config = _make_config(2024)
    account = Account.create(
        owner=user,
        initial_savings=initial_savings,
        cost_basis=cost_basis,
        regular_investment_dollar=regular_investment_dollar,
        regular_investment_frequency=regular_investment_frequency,
        annual_investment_increase=annual_investment_increase,
        annual_investment_return=annual_investment_return,
        annual_retirement_return=annual_retirement_return,
        compound_frequency=compound_frequency,
        compound_type=compound_type,
        account_type=account_type,
    )
    return user, account, config


def _simulate(
    account: Account, config: GlobalParameters
) -> tuple[list[int], list[Decimal]]:
    from calculate.simulator import RetirementSimulator

    account.owner.accounts = {"temp_account": account}
    simulator = RetirementSimulator(account.owner, config)
    res = simulator.simulate()
    return res["temp_account"]


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
        account.simulate_accumulation(account.initial_savings, labels, values)
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
            annual_retirement_post_tax_expense=annual_expense,
            state_of_residence=State.TEXAS,
        )
        config = _make_config(2024)
        account = Account.create(
            owner=user,
            initial_savings=initial_savings,
            annual_retirement_return=annual_retirement_return,
            compound_frequency=compound_frequency,
            account_type=account_type,
        )
        labels = []
        values = []
        account.simulate_retirement(initial_savings, labels, values, config)
        return labels, values

    def test_runs_out_within_first_year_appends_zero(self):
        """
        When savings deplete within the first year, we verify that the depletion
        is correctly visualized by appending 0 value data points.
        """
        labels, values = self._run_retirement(
            initial_savings=500_000,
            annual_expense=400_000,  # ~$33k/month guard; inflation-adj expense ~$45k → drains in 11 months
            lifespan=80,
            retirement_age=40,
            annual_retirement_return=0.0,
            account_type=AccountType.ROTH,
        )
        assert labels == [
            41,
            42,
        ], "Expected labels for the depletion year and subsequent year"
        assert values == [Decimal("0"), Decimal("0")], "Expected values to be zero"

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
            annual_retirement_post_tax_expense=12_000,
            state_of_residence=State.TEXAS,
        )
        config = _make_config(2024)
        config.inflation_rate = Decimal("0.0")
        account = Account.create(
            owner=user,
            initial_savings=120_000,
            annual_retirement_return=0.0,
            compound_frequency=Frequency.MONTHLY,
            account_type=AccountType.ROTH,  # no tax grossing
        )
        labels = []
        values = []
        account.simulate_retirement(Decimal("120000"), labels, values, config)
        # After 1 year (12 months) the balance should be 120,000 - 12,000 = 108,000
        assert math.isclose(
            values[0], 108_000.0, abs_tol=0.01
        ), f"Expected 108000.00 after year 1, got {values[0]:.2f}"

    def test_cost_basis_reduction_in_net_loss(self):
        """
        Verify that cost basis is reduced proportionally under a net-loss scenario.
        For a GENERIC account:
        S = 100,000 (initial savings)
        cost_basis = 150,000 (net loss)
        Since it is a net loss, capital gains = 0, tax = 0, so withdrawal_pre_tax = withdrawal_post_tax.
        With monthly expense = 12,000 (1,000/month):
        In month 1:
        withdrawal_pre_tax = 1000
        total_savings_before_withdrawal = 100000
        cost_basis_withdrawn = 150000 * (1000 / 100000) = 1500
        Remaining cost basis should be 150000 - 1500 = 148500.
        After 12 months, CB should be 150000 - 12 * 1500 = 132000.
        """
        user = Person(
            current_age=30,
            retirement_age=40,
            lifespan=41,
            pre_tax_income=115_000,
            annual_retirement_post_tax_expense=12_000,
            state_of_residence=State.TEXAS,
        )
        config = _make_config(2024)
        config.inflation_rate = Decimal("0.0")
        from utils.parameters import BrokerageAccount

        account = Account.create(
            owner=user,
            initial_savings=100_000,
            annual_retirement_return=0.0,
            compound_frequency=Frequency.MONTHLY,
            account_type=AccountType.GENERIC,
        )
        assert isinstance(account, BrokerageAccount)
        account.cost_basis = Decimal("150000")
        labels = []
        values = []
        account.simulate_retirement(Decimal("100000"), labels, values, config)
        assert math.isclose(
            float(account.cost_basis), 132_000.0, abs_tol=1.0
        ), f"Expected cost basis of 132000.00 after 12 months, got {account.cost_basis:.2f}"

    def test_retirement_tax_inflation_adjustment(self):
        """
        Verify that tax calculations adjust for inflation so that bracket creep is avoided.
        The pre-tax monthly income required for a target post-tax monthly income must scale
        proportionally with the inflation factor.
        """
        user = Person(
            current_age=30,
            retirement_age=40,
            lifespan=50,
            pre_tax_income=115_000,
            state_of_residence=State.TEXAS,
        )
        config = _make_config(2024)

        # Test TRADITIONAL account (progressive ordinary income tax)
        account_trad = Account.create(
            owner=user,
            initial_savings=1_000_000,
            account_type=AccountType.TRADITIONAL,
        )

        # Calculate pre-tax income at inflation_factor = 1.0 (real dollars)
        pre_tax_real = account_trad.get_pre_tax_withdrawal(
            post_tax_income=Decimal("5000"),
            current_savings=Decimal("1000000"),
            config=config,
            inflation_factor=Decimal("1.0"),
        )

        # Calculate pre-tax income at inflation_factor = 1.5 (inflated dollars)
        pre_tax_inflated = account_trad.get_pre_tax_withdrawal(
            post_tax_income=Decimal("5000") * Decimal("1.5"),
            current_savings=Decimal("1000000"),
            config=config,
            inflation_factor=Decimal("1.5"),
        )

        expected_inflated = pre_tax_real * Decimal("1.5")
        assert math.isclose(
            float(pre_tax_inflated), float(expected_inflated), rel_tol=1e-5
        ), f"Expected progressive pre-tax inflated to be {expected_inflated}, got {pre_tax_inflated}"

        # Test GENERIC account (capital gains tax)
        from utils.parameters import BrokerageAccount

        account_generic = Account.create(
            owner=user,
            initial_savings=1_000_000,
            account_type=AccountType.GENERIC,
        )
        assert isinstance(account_generic, BrokerageAccount)
        account_generic.cost_basis = Decimal("400000")  # gain ratio is 0.6

        # Calculate pre-tax income at inflation_factor = 1.0 (real dollars)
        pre_tax_real_gen = account_generic.get_pre_tax_withdrawal(
            post_tax_income=Decimal("5000"),
            current_savings=Decimal("1000000"),
            config=config,
            inflation_factor=Decimal("1.0"),
        )

        # Calculate pre-tax income at inflation_factor = 1.8 (inflated dollars)
        pre_tax_inflated_gen = account_generic.get_pre_tax_withdrawal(
            post_tax_income=Decimal("5000") * Decimal("1.8"),
            current_savings=Decimal("1000000"),
            config=config,
            inflation_factor=Decimal("1.8"),
        )

        expected_inflated_gen = pre_tax_real_gen * Decimal("1.8")
        assert math.isclose(
            float(pre_tax_inflated_gen), float(expected_inflated_gen), rel_tol=1e-5
        ), f"Expected capital gains pre-tax inflated to be {expected_inflated_gen}, got {pre_tax_inflated_gen}"


# ===========================================================================
# simulate – end-to-end
# ===========================================================================


class TestSimulate:
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
        labels, values = _simulate(account, config)
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
        labels, values = _simulate(account, config)
        # The max should be somewhere around retirement, not at the very end
        max_value = max(values)
        last_value = values[-1]
        assert (
            max_value > last_value
        ), "Portfolio value should peak during/near retirement, not at the end"

    def test_lengths_match(self):
        user, account, config = _make_person_and_account()
        labels, values = _simulate(account, config)
        assert len(labels) == len(values)

    def test_all_values_non_negative(self):
        user, account, config = _make_person_and_account(
            account_type=AccountType.ROTH,
            annual_retirement_post_tax_expense=40_000,
        )
        _, values = _simulate(account, config)
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
        labels, values = _simulate(account, config)
        # The last value from the accumulation phase (index 9 = age 39)
        assert math.isclose(
            values[9], expected_at_retirement, rel_tol=1e-5
        ), f"Expected {expected_at_retirement:.2f} at retirement, got {values[9]:.2f}"

    def test_generic_cost_basis_accumulation(self):
        """Verify cost basis accumulates contributions correctly during the accumulation phase."""
        user, account, config = _make_person_and_account(
            current_age=30,
            retirement_age=33,
            lifespan=33,
            initial_savings=5_000,
            cost_basis=5_000,
            regular_investment_dollar=1_000,
            regular_investment_frequency=Frequency.MONTHLY,
            annual_investment_increase=0.0,
            account_type=AccountType.GENERIC,
        )
        _simulate(account, config)
        # Initial basis = 5000.
        # Contributions: 3 years * 12 months * 1000/month = 36000.
        # Expected basis = 41000.
        from utils.parameters import BrokerageAccount

        assert isinstance(account, BrokerageAccount)
        assert account.cost_basis == Decimal("41000")

    def test_federal_capital_gains_brackets_2025_and_2026(self):
        """Verify capital gains calculations using the new 2025 and 2026 LTCG brackets."""
        config_2025 = _make_config(year=2025)
        user_2025 = Person(filing=Filing.INDIVIDUAL, state_of_residence=State.TEXAS)
        account_2025 = Account.create(owner=user_2025, account_type=AccountType.GENERIC)

        # Under 2025 Single: 0% up to 48,350. Standard deduction is 15,750.
        # Taxable gain = 60,000 - 15,750 = 44,250.
        # Since 44,250 <= 48,350, it is all taxed at 0%. Total tax = 0.
        from calculate.retirement import calculate_retirement_withdrawal_tax

        tax = calculate_retirement_withdrawal_tax(
            Decimal("60000"), account_2025, config_2025, is_capital_gains=True
        )
        assert tax == Decimal("0")

        # If gain is 100,000:
        # Taxable gain = 100,000 - 15,750 = 84,250.
        # First 48,350 taxed at 0% (0 tax).
        # Next 35,900 taxed at 15% (tax = 35900 * 0.15 = 5385.00).
        # Total tax = 5,385.00.
        tax = calculate_retirement_withdrawal_tax(
            Decimal("100000"), account_2025, config_2025, is_capital_gains=True
        )
        assert tax == Decimal("5385.00")

    def test_state_capital_gains_tax_calculators(self):
        """Verify California (progressive ordinary, no SDI, includes MHS) and Texas (0%) state capital gains tax calculators."""
        config_2025 = _make_config(year=2025)

        # Texas
        user_tx = Person(state_of_residence=State.TEXAS)
        from calculate.state_tax import get_state_tax_calculator

        calculator_tx = get_state_tax_calculator(State.TEXAS)
        tx_tax = calculator_tx.calculate_capital_gains_tax(
            Decimal("100000"), user_tx, config_2025
        )
        assert tx_tax == Decimal("0")

        # California
        # Using 2024 config since CA tax brackets are configured for 2024.
        # Standard deduction = 5,363. Taxable gain = 20,000 - 5,363 = 14,637.
        # First 10,412 taxed at 1% = 104.12.
        # Next 4,225 taxed at 2% = 84.50.
        # Total CA tax = 188.62.
        config_2024 = _make_config(year=2024)
        user_ca = Person(state_of_residence=State.CALIFORNIA, filing=Filing.INDIVIDUAL)
        calculator_ca = get_state_tax_calculator(State.CALIFORNIA)
        ca_tax = calculator_ca.calculate_capital_gains_tax(
            Decimal("20000"), user_ca, config_2024
        )
        assert ca_tax == Decimal("188.62")

    def test_get_state_tax_calculator_warning(self, caplog):
        """Verify that requesting a state tax calculator for an unimplemented state logs a warning and falls back to NoStateTaxCalculator."""
        import logging

        # Using a dummy state name to trigger fallback
        unimplemented_state = "New York"
        from calculate.state_tax import get_state_tax_calculator

        with caplog.at_level(logging.WARNING):
            get_state_tax_calculator(unimplemented_state)  # type: ignore
            assert len(caplog.records) > 0
            assert "not implemented" in caplog.text

    def test_retirement_withdrawals_exclude_fica_and_sdi(self):
        """Verify that FICA and SDI are excluded in retirement withdrawals."""
        config_2024 = _make_config(year=2024)
        user_ca = Person(state_of_residence=State.CALIFORNIA, filing=Filing.INDIVIDUAL)
        account_trad = Account.create(
            owner=user_ca, account_type=AccountType.TRADITIONAL
        )

        # Calculate retirement withdrawal tax for 100,000 pre-tax
        from calculate.retirement import calculate_retirement_withdrawal_tax

        ret_tax = calculate_retirement_withdrawal_tax(
            Decimal("100000"), account_trad, config_2024, is_capital_gains=False
        )

        # Calculate standard tax on the same amount (includes FICA/SDI)
        from calculate.aggregate import calculate_annual_income_tax

        user_ca.pre_tax_income = Decimal("100000")
        std_tax = calculate_annual_income_tax(user_ca, config_2024)

        # The difference must be at least the FICA + SDI payroll taxes on $100k
        assert std_tax - ret_tax >= Decimal("8750")

    def test_coordinated_simulation_applies_single_deduction(self):
        """Verify that when multiple traditional accounts are simulated,
        the standard deduction is applied only once in aggregate, rather than once per account.
        """
        user = Person(
            current_age=30,
            retirement_age=30,
            lifespan=31,
            pre_tax_income=100_000,
            annual_retirement_post_tax_expense=20_000,
            state_of_residence=State.TEXAS,
            filing=Filing.INDIVIDUAL,
        )
        config = _make_config(year=2024)

        acc1 = Account.create(
            owner=user,
            initial_savings=500_000,
            annual_retirement_return=0.0,
            account_type=AccountType.TRADITIONAL,
        )
        acc2 = Account.create(
            owner=user,
            initial_savings=500_000,
            annual_retirement_return=0.0,
            account_type=AccountType.TRADITIONAL,
        )
        user.add_account(acc1, "Traditional_1")
        user.add_account(acc2, "Traditional_2")

        from calculate.simulator import RetirementSimulator

        simulator = RetirementSimulator(user, config)
        results = simulator.simulate()

        _, vals1 = results["Traditional_1"]
        _, vals2 = results["Traditional_2"]

        assert vals1[0] < 490_000
        assert (
            vals2[0] == 500_000
        )  # Sequentially untouched because Traditional_1 is drawn first and has enough savings

    def test_coordinated_simulation_stacks_capital_gains(self):
        """Verify that capital gains are stacked on top of ordinary income in coordinated simulation."""
        user = Person(
            current_age=30,
            retirement_age=30,
            lifespan=31,
            pre_tax_income=100_000,
            annual_retirement_post_tax_expense=60_000,
            state_of_residence=State.TEXAS,
            filing=Filing.INDIVIDUAL,
        )
        config = _make_config(year=2024)

        acc_trad = Account.create(
            owner=user,
            initial_savings=500_000,
            annual_retirement_return=0.0,
            account_type=AccountType.TRADITIONAL,
        )
        acc_brok = Account.create(
            owner=user,
            initial_savings=500_000,
            cost_basis=0,
            annual_retirement_return=0.0,
            account_type=AccountType.GENERIC,
        )
        user.add_account(acc_trad, "Traditional")
        user.add_account(acc_brok, "Brokerage")

        from calculate.simulator import RetirementSimulator

        simulator = RetirementSimulator(user, config)
        results = simulator.simulate()

        _, brok_vals = results["Brokerage"]
        assert brok_vals[0] < 490_000
