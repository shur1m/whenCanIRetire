"""Regression tests for calculate/tax.py

These tests verify the total income tax aggregation and retirement contribution
savings calculations.
"""

import math
import json
from decimal import Decimal

from calculate.aggregate import (
    calculate_annual_income_tax,
    calculate_retirement_deductions_excess,
)
from calculate.federal_tax import (
    calculate_annual_federal_income_tax,
    calculate_annual_social_security_tax,
    calculate_annual_medicare_tax,
)
from calculate.state_tax import (
    calculate_annual_state_income_tax,
)
from utils.globals import GlobalParameters
from utils.parameters import Person
from utils.enums import Filing, Frequency, AccountType, State
from utils.schemas import TaxSchema

# Load and validate tax tables once at module scope to eliminate file I/O overhead in tests
with open("config/tax.json") as _f:
    _TAX_DATA = TaxSchema.model_validate(json.load(_f))


def _setup(user: Person, year: int = 2024) -> GlobalParameters:
    return GlobalParameters(
        year=year,
        inflation_rate=Decimal("0.03"),
        yearly_tax=_TAX_DATA.root[str(year)],
    )


# ===========================================================================
# calculate_annual_income_tax (total)
# ===========================================================================


class TestTotalIncomeTax:
    def test_total_is_sum_of_components(self, person_tx_115k, config_2024):
        """Total tax must equal the sum of its four components."""
        federal = calculate_annual_federal_income_tax(person_tx_115k, config_2024)
        state = calculate_annual_state_income_tax(person_tx_115k, config_2024)
        ss = calculate_annual_social_security_tax(person_tx_115k, config_2024)
        medicare = calculate_annual_medicare_tax(person_tx_115k, config_2024)
        total = calculate_annual_income_tax(person_tx_115k, config_2024)

        assert math.isclose(
            total, federal + state + ss + medicare, abs_tol=0.01
        ), f"Total tax {total} != components sum {federal + state + ss + medicare}"

    def test_total_texas_115k_pinned(self, person_tx_115k, config_2024):
        """
        Pin the full tax bill for TX single filer at $115k (2024).
        Federal ≈ 17,141.00 + SS = 7,130.00 + Medicare = 1,667.50 + State = 0
        Total ≈ 25,938.50
        """
        result = calculate_annual_income_tax(person_tx_115k, config_2024)
        assert math.isclose(
            result, 25_938.50, abs_tol=1.0
        ), f"Expected ~25938.50 total tax, got {result:.2f}"

    def test_total_california_115k_higher_than_texas(
        self, person_tx_115k, person_ca_115k, config_2024
    ):
        tx_tax = calculate_annual_income_tax(person_tx_115k, config_2024)
        ca_tax = calculate_annual_income_tax(person_ca_115k, config_2024)
        assert ca_tax > tx_tax, "CA tax should be higher than TX for the same income"

    def test_higher_income_means_higher_tax(self):
        """Monotonicity: more income → more total tax."""
        user_low = Person(pre_tax_income=80_000, state_of_residence=State.TEXAS)
        config_low = _setup(user_low)
        user_high = Person(pre_tax_income=200_000, state_of_residence=State.TEXAS)
        config_high = _setup(user_high)
        assert calculate_annual_income_tax(
            user_high, config_high
        ) > calculate_annual_income_tax(user_low, config_low)


def test_calculate_retirement_deductions_excess_preserves_additional_deductions():
    user = Person(
        pre_tax_income=100_000,
        additional_income_tax_deductions=5_000,
        state_of_residence=State.TEXAS,
        filing=Filing.INDIVIDUAL,
    )
    user.create_account(
        "401k",
        regular_investment_dollar=10_000,
        regular_investment_frequency=Frequency.ANNUALLY,
        account_type=AccountType.TRADITIONAL,
    )
    config = _setup(user)

    tax_with_all = calculate_annual_income_tax(user, config)
    excess_savings = calculate_retirement_deductions_excess(user, config, tax_with_all)

    only_base_user = Person(
        pre_tax_income=100_000,
        additional_income_tax_deductions=5_000,
        state_of_residence=State.TEXAS,
        filing=Filing.INDIVIDUAL,
    )
    tax_with_only_base = calculate_annual_income_tax(only_base_user, config)
    expected_savings = tax_with_only_base - tax_with_all

    assert math.isclose(
        excess_savings, expected_savings, abs_tol=0.01
    ), f"Expected excess savings to be {expected_savings}, but got {excess_savings}."
