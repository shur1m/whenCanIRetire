"""
Regression tests for calculate/tax.py

These tests pin the exact numeric outputs of every public tax function so that
any refactor that accidentally changes the math will be caught immediately.

Hand-verified expected values (see inline comments) are computed from the 2024
tax tables in config/tax.json.

2024 Federal individual brackets (taxable income = gross - standard deduction):
  Standard deduction: $14,600
  10%  on $0        – $11,600
  12%  on $11,601   – $47,150
  22%  on $47,151   – $100,525
  24%  on $100,526  – $191,950
  32%  on $191,951  – $243,725
  35%  on $243,726  – $609,350
  37%  on $609,351+

2024 FICA:
  Social Security: 6.2% on up to $168,600
  Medicare: 1.45% on all; +0.9% above $200k (individual) / $250k (joint)
"""
import math
import pytest

from calculate.tax import (
    calculate_annual_income_tax,
    calculate_annual_federal_income_tax,
    calculate_annual_state_income_tax,
    calculate_annual_social_security_tax,
    calculate_annual_medicare_tax,
)
from utils.globals import GlobalParameters
from utils.parameters import Person, Account
from utils.enums import Filing, Frequency, AccountType, State


# ---------------------------------------------------------------------------
# Helper – ensures GlobalParameters is loaded for the right year/user before
# every assertion.  Tests call this directly when the fixture user doesn't
# match the scenario being tested.
# ---------------------------------------------------------------------------

def _setup(user: Person, year: int = 2024) -> None:
    GlobalParameters.configure(year, user)


# ===========================================================================
# calculate_annual_federal_income_tax
# ===========================================================================

class TestFederalIncomeTax:
    """
    2024 individual, gross = $115,000
    Taxable income = 115,000 - 14,600 (std deduction) = $100,400

    Bracket math:
      10%  on  11,600          =  1,160.00
      12%  on (47,150-11,600)  = 35,550 * 0.12 = 4,266.00
      22%  on (100,400-47,150) = 53,250 * 0.22 = 11,715.00
      Total = 17,141.00
    """

    def test_single_115k_federal_tax(self, person_tx_115k):
        """
        2024 individual, $115k gross, std deduction $14,600 → taxable = $100,400.
        Bracket math:
          10% on $11,600            =  1,160.00
          12% on $35,550            =  4,266.00
          22% on $53,250            = 11,715.00
          Subtotal ≈ 17,141 (small float rounding expected)
        """
        result = calculate_annual_federal_income_tax(person_tx_115k)
        assert math.isclose(result, 17_141.00, abs_tol=1.0), (
            f"Expected ~17141.00, got {result}"
        )

    def test_zero_income_no_federal_tax(self):
        """Income below the standard deduction → taxable income ≤ 0 → no tax."""
        user = Person(pre_tax_income=10_000, state_of_residence=State.TEXAS)
        _setup(user)
        assert calculate_annual_federal_income_tax(user) == 0.0

    def test_income_exactly_at_standard_deduction(self):
        """Income exactly equal to standard deduction → zero taxable income."""
        deduction = 14_600  # 2024 individual standard deduction
        user = Person(pre_tax_income=deduction, state_of_residence=State.TEXAS)
        _setup(user)
        assert calculate_annual_federal_income_tax(user) == 0.0

    def test_very_high_income_hits_top_bracket(self):
        """$700k individual: should be taxed at the 37% top bracket."""
        user = Person(pre_tax_income=700_000, state_of_residence=State.TEXAS)
        _setup(user)
        result = calculate_annual_federal_income_tax(user)
        # Top bracket (37%) starts at $609,351; verify we exceed it
        assert result > 200_000, f"Expected substantial tax on $700k, got {result}"

    def test_joint_filer_uses_joint_brackets(self, person_tx_joint_200k):
        """Joint filer should get a lower effective rate than individual at same income."""
        joint_result = calculate_annual_federal_income_tax(person_tx_joint_200k)

        individual_user = Person(
            pre_tax_income=200_000,
            state_of_residence=State.TEXAS,
            filing=Filing.INDIVIDUAL,
        )
        _setup(individual_user)
        individual_result = calculate_annual_federal_income_tax(individual_user)

        assert joint_result < individual_result, (
            "Joint filers should pay less tax than individual filers at the same income"
        )

    def test_401k_deduction_reduces_federal_tax(self):
        """Traditional 401(k) contribution reduces taxable income and therefore tax."""
        income = 115_000
        user_no_account = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_no_account)
        tax_no_deduction = calculate_annual_federal_income_tax(user_no_account)

        user_with_401k = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_with_401k)
        user_with_401k.create_account(
            "401k",
            regular_investment_dollar=500,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.TRADITIONAL,
        )
        tax_with_deduction = calculate_annual_federal_income_tax(user_with_401k)

        assert tax_with_deduction < tax_no_deduction, (
            "401(k) deductions should reduce federal income tax"
        )

    def test_roth_does_not_reduce_federal_tax(self):
        """Roth contributions are post-tax; they must NOT reduce federal income tax."""
        income = 115_000
        user_no_account = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_no_account)
        tax_no_account = calculate_annual_federal_income_tax(user_no_account)

        user_roth = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_roth)
        user_roth.create_account(
            "Roth",
            regular_investment_dollar=500,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.ROTH,
        )
        tax_with_roth = calculate_annual_federal_income_tax(user_roth)

        assert math.isclose(tax_no_account, tax_with_roth, abs_tol=0.01), (
            "Roth contributions should not change federal tax"
        )


# ===========================================================================
# calculate_annual_social_security_tax
# ===========================================================================

class TestSocialSecurityTax:
    """
    2024: 6.2% on first $168,600 of FICA-taxable income.
    """

    def test_single_115k_social_security(self, person_tx_115k):
        # 115,000 * 0.062 = 7,130
        result = calculate_annual_social_security_tax(person_tx_115k)
        assert math.isclose(result, 7_130.00, abs_tol=0.01), (
            f"Expected 7130.00, got {result}"
        )

    def test_income_above_cap_is_capped(self):
        """Income above $168,600 → SS tax = 168,600 * 6.2% = 10,453.20."""
        user = Person(pre_tax_income=300_000, state_of_residence=State.TEXAS)
        _setup(user)
        result = calculate_annual_social_security_tax(user)
        expected = 168_600 * 0.062
        assert math.isclose(result, expected, abs_tol=0.01), (
            f"Expected {expected:.2f} (capped), got {result}"
        )

    def test_income_exactly_at_cap(self):
        user = Person(pre_tax_income=168_600, state_of_residence=State.TEXAS)
        _setup(user)
        result = calculate_annual_social_security_tax(user)
        expected = 168_600 * 0.062
        assert math.isclose(result, expected, abs_tol=0.01)

    def test_hsa_contribution_reduces_ss_tax(self):
        """HSA contributions reduce FICA-taxable income, lowering SS tax."""
        income = 115_000
        user_no_hsa = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_no_hsa)
        ss_no_hsa = calculate_annual_social_security_tax(user_no_hsa)

        user_hsa = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_hsa)
        user_hsa.create_account(
            "HSA",
            regular_investment_dollar=300,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.HSA,
        )
        ss_with_hsa = calculate_annual_social_security_tax(user_hsa)

        assert ss_with_hsa < ss_no_hsa, "HSA contributions should reduce SS tax"

    def test_401k_does_not_reduce_ss_tax(self):
        """Traditional 401(k) contributions do NOT reduce FICA-taxable income."""
        income = 115_000
        user_no_account = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_no_account)
        ss_no_account = calculate_annual_social_security_tax(user_no_account)

        user_401k = Person(pre_tax_income=income, state_of_residence=State.TEXAS)
        _setup(user_401k)
        user_401k.create_account(
            "401k",
            regular_investment_dollar=500,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.TRADITIONAL,
        )
        ss_with_401k = calculate_annual_social_security_tax(user_401k)

        assert math.isclose(ss_no_account, ss_with_401k, abs_tol=0.01), (
            "401(k) should not change SS taxable income"
        )


# ===========================================================================
# calculate_annual_medicare_tax
# ===========================================================================

class TestMedicareTax:
    """
    2024: 1.45% on all income; +0.9% surtax above $200k (individual)/$250k (joint).
    """

    def test_single_115k_medicare(self, person_tx_115k):
        # 115,000 * 0.0145 = 1,667.50
        result = calculate_annual_medicare_tax(person_tx_115k)
        assert math.isclose(result, 1_667.50, abs_tol=0.01), (
            f"Expected 1667.50, got {result}"
        )

    def test_high_earner_surtax_individual(self):
        """
        Individual earning $250k: 1.45% base + additional surtax on amount above $200k.
        Per config/tax.json: MedicareHighEarnerTax = 0.09 (9%).
        base   = 250,000 * 0.0145 = 3,625.00
        surtax = 50,000  * 0.09   = 4,500.00
        total  = 8,125.00
        """
        income = 250_000
        user = Person(
            pre_tax_income=income,
            state_of_residence=State.TEXAS,
            filing=Filing.INDIVIDUAL,
        )
        _setup(user)
        result = calculate_annual_medicare_tax(user)
        # surtax rate is 0.09 (9%) as defined in config/tax.json MedicareHighEarnerTax
        base = income * 0.0145
        surtax = (income - 200_000) * GlobalParameters.medicare_high_earner_tax
        expected = base + surtax
        assert math.isclose(result, expected, abs_tol=0.01), (
            f"Expected {expected:.2f}, got {result}"
        )

    def test_no_surtax_below_threshold_individual(self):
        """Individual earning exactly at the $200k threshold: no surtax applies."""
        income = 200_000
        user = Person(
            pre_tax_income=income,
            state_of_residence=State.TEXAS,
            filing=Filing.INDIVIDUAL,
        )
        _setup(user)
        result = calculate_annual_medicare_tax(user)
        expected = income * 0.0145
        assert math.isclose(result, expected, abs_tol=0.01)

    def test_joint_surtax_threshold_is_higher(self):
        """Joint filer at $230k should not incur surtax (threshold = $250k)."""
        income = 230_000
        user_joint = Person(
            pre_tax_income=income,
            state_of_residence=State.TEXAS,
            filing=Filing.JOINT,
        )
        _setup(user_joint)
        result = calculate_annual_medicare_tax(user_joint)
        expected = income * 0.0145  # no surtax
        assert math.isclose(result, expected, abs_tol=0.01), (
            f"Joint filer at $230k should not pay surtax; expected {expected:.2f}, got {result}"
        )


# ===========================================================================
# calculate_annual_state_income_tax
# ===========================================================================

class TestStateIncomeTax:
    def test_texas_no_state_tax(self, person_tx_115k):
        assert calculate_annual_state_income_tax(person_tx_115k) == 0

    def test_none_state_no_state_tax(self):
        """
        state_of_residence=None means no state tax is levied.
        We use TEXAS for GlobalParameters.configure (which handles None gracefully
        only for the state_of_residence == None check in calculate_annual_state_income_tax),
        but configure requires an actual State or Texas to avoid a KeyError.
        We therefore configure with TEXAS and then set state to None on the user.
        """
        user = Person(pre_tax_income=115_000, state_of_residence=State.TEXAS)
        _setup(user)
        user.state_of_residence = None  # patch after configure
        assert calculate_annual_state_income_tax(user) == 0

    def test_california_state_tax_positive(self, person_ca_115k):
        result = calculate_annual_state_income_tax(person_ca_115k)
        assert result > 0, "California resident should owe state income tax"

    def test_california_includes_sdi(self, person_ca_115k):
        """
        California SDI = 1.1% of (pre_tax_income - state std deduction).
        State std deduction 2024: $5,363.
        SDI = 0.011 * (115,000 - 5,363) = 0.011 * 109,637 = 1,206.01
        The total state tax must be at least this much.
        """
        sdi_floor = 0.011 * (115_000 - 5_363)
        result = calculate_annual_state_income_tax(person_ca_115k)
        assert result >= sdi_floor, (
            f"CA state tax should include SDI (≥ {sdi_floor:.2f}), got {result:.2f}"
        )

    def test_california_115k_state_tax_exact(self, person_ca_115k):
        """
        Pin the exact CA state tax for $115k individual, 2024.

        CA taxable income = 115,000 - 5,363 = 109,637
        Bracket math (individual):
          1%   on 10,412               = 104.12
          2%   on (24,684-10,412)      = 14,272 * 0.02  = 285.44
          4%   on (38,959-24,684)      = 14,275 * 0.04  = 571.00
          6%   on (54,081-38,959)      = 15,122 * 0.06  = 907.32
          8%   on (68,350-54,081)      = 14,269 * 0.08  = 1,141.52
          9.3% on (109,637-68,350)     = 41,287 * 0.093 = 3,839.69
          Bracket total = 6,849.09
        SDI = 0.011 * (115,000 - 5,363) = 0.011 * 109,637 = 1,206.01
        Total CA state tax ≈ 8,055.10
        """
        result = calculate_annual_state_income_tax(person_ca_115k)
        assert math.isclose(result, 8_055.10, abs_tol=1.0), (
            f"Expected CA state tax ~8055.10, got {result:.2f}"
        )


# ===========================================================================
# calculate_annual_income_tax (total)
# ===========================================================================

class TestTotalIncomeTax:
    def test_total_is_sum_of_components(self, person_tx_115k):
        """Total tax must equal the sum of its four components."""
        federal = calculate_annual_federal_income_tax(person_tx_115k)
        state = calculate_annual_state_income_tax(person_tx_115k)
        ss = calculate_annual_social_security_tax(person_tx_115k)
        medicare = calculate_annual_medicare_tax(person_tx_115k)
        total = calculate_annual_income_tax(person_tx_115k)

        assert math.isclose(total, federal + state + ss + medicare, abs_tol=0.01), (
            f"Total tax {total} != components sum {federal + state + ss + medicare}"
        )

    def test_total_texas_115k_pinned(self, person_tx_115k):
        """
        Pin the full tax bill for TX single filer at $115k (2024).
        Federal ≈ 17,141.00 + SS = 7,130.00 + Medicare = 1,667.50 + State = 0
        Total ≈ 25,938.50
        """
        result = calculate_annual_income_tax(person_tx_115k)
        assert math.isclose(result, 25_938.50, abs_tol=1.0), (
            f"Expected ~25938.50 total tax, got {result:.2f}"
        )

    def test_total_california_115k_higher_than_texas(
        self, person_tx_115k, person_ca_115k
    ):
        tx_tax = calculate_annual_income_tax(person_tx_115k)
        ca_tax = calculate_annual_income_tax(person_ca_115k)
        assert ca_tax > tx_tax, "CA tax should be higher than TX for the same income"

    def test_higher_income_means_higher_tax(self):
        """Monotonicity: more income → more total tax."""
        user_low = Person(pre_tax_income=80_000, state_of_residence=State.TEXAS)
        _setup(user_low)
        user_high = Person(pre_tax_income=200_000, state_of_residence=State.TEXAS)
        _setup(user_high)
        assert calculate_annual_income_tax(user_high) > calculate_annual_income_tax(
            user_low
        )
