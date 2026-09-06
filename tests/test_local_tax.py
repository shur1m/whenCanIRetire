import json
import logging
import math
from decimal import Decimal

import pytest

from calculate.local_tax import (
    calculate_annual_local_income_tax,
    get_local_tax_calculator,
    NewYorkCityTaxCalculator,
    NoLocalTaxCalculator,
)
from utils.enums import City, Filing, Frequency, AccountType
from utils.globals import GlobalParameters
from utils.parameters import Person
from utils.schemas import TaxSchema

with open("config/tax.json") as _f:
    _TAX_DATA = TaxSchema.model_validate(json.load(_f))


def _make_config(year: int = 2024) -> GlobalParameters:
    return GlobalParameters(
        year=year,
        inflation_rate=Decimal("0.03"),
        yearly_tax=_TAX_DATA.root[str(year)],
    )


class TestLocalTaxCalculatorRegistry:
    def test_get_local_tax_calculator_none(self):
        calculator = get_local_tax_calculator(None)
        assert isinstance(calculator, NoLocalTaxCalculator)

    def test_get_local_tax_calculator_nyc(self):
        calculator = get_local_tax_calculator(City.NEW_YORK_CITY)
        assert isinstance(calculator, NewYorkCityTaxCalculator)

    def test_get_local_tax_calculator_unimplemented(self, caplog):
        with caplog.at_level(logging.WARNING):
            calculator = get_local_tax_calculator("San Francisco")  # type: ignore
            assert isinstance(calculator, NoLocalTaxCalculator)
            assert "not implemented" in caplog.text


class TestNewYorkCityTaxCalculator:
    def test_nyc_income_below_standard_deduction(self):
        user = Person(
            pre_tax_income=8000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.INDIVIDUAL,
        )
        config = _make_config(2024)
        tax = calculate_annual_local_income_tax(user, config)
        assert tax == Decimal("0")

    def test_nyc_individual_first_bracket(self):
        # Taxable income: $20,000 - $8,000 = $12,000
        # 12,000 * 3.078% = $369.36
        user = Person(
            pre_tax_income=20000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.INDIVIDUAL,
        )
        config = _make_config(2024)
        tax = calculate_annual_local_income_tax(user, config)
        assert math.isclose(tax, Decimal("369.36"), abs_tol=0.01)

    def test_nyc_individual_multiple_brackets(self):
        # Taxable income: $58,000 - $8,000 = $50,000
        # 12,000 * 0.03078 + 13,000 * 0.03762 + 25,000 * 0.03819 = 1,813.17
        user = Person(
            pre_tax_income=58000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.INDIVIDUAL,
        )
        config = _make_config(2024)
        tax = calculate_annual_local_income_tax(user, config)
        assert math.isclose(tax, Decimal("1813.17"), abs_tol=0.01)

    def test_nyc_individual_120k(self):
        # Taxable income: $120,000 - $8,000 = $112,000
        # 1,813.17 + (112,000 - 50,000) * 0.03876 = 1,813.17 + 2,403.12 = 4,216.29
        user = Person(
            pre_tax_income=120000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.INDIVIDUAL,
        )
        config = _make_config(2024)
        tax = calculate_annual_local_income_tax(user, config)
        assert math.isclose(tax, Decimal("4216.29"), abs_tol=0.01)

    def test_nyc_joint_120k(self):
        # Taxable income: $120,000 - $16,050 = $103,950
        # 21,600 * 0.03078 + 23,400 * 0.03762 + 45,000 * 0.03819 + 13,950 * 0.03876 = 3,804.40
        user = Person(
            pre_tax_income=120000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.JOINT,
        )
        config = _make_config(2024)
        tax = calculate_annual_local_income_tax(user, config)
        assert math.isclose(tax, Decimal("3804.40"), abs_tol=0.01)

    def test_nyc_pre_tax_deductions_reduce_tax(self):
        user_no_deduction = Person(
            pre_tax_income=100000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.INDIVIDUAL,
        )
        user_with_deduction = Person(
            pre_tax_income=100000,
            city_of_residence=City.NEW_YORK_CITY,
            filing=Filing.INDIVIDUAL,
        )
        user_with_deduction.create_account(
            "401k",
            regular_investment_dollar=10000,
            regular_investment_frequency=Frequency.ANNUALLY,
            account_type=AccountType.TRADITIONAL,
        )
        config = _make_config(2024)
        tax_no_deduction = calculate_annual_local_income_tax(user_no_deduction, config)
        tax_with_deduction = calculate_annual_local_income_tax(
            user_with_deduction, config
        )
        assert tax_no_deduction > tax_with_deduction
        # Expected savings on $10,000 at top marginal rate 3.876% is $387.60
        assert math.isclose(
            tax_no_deduction - tax_with_deduction, Decimal("387.60"), abs_tol=0.01
        )
