import logging
from decimal import Decimal
from utils.enums import City
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax

logger = logging.getLogger(__name__)


class LocalTaxCalculator:
    """Base class for local / municipal tax calculators."""

    def calculate_income_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        raise NotImplementedError


class NoLocalTaxCalculator(LocalTaxCalculator):
    """For municipalities with no local income tax (or when city_of_residence is None)."""

    def calculate_income_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return Decimal("0")


class NewYorkCityTaxCalculator(LocalTaxCalculator):
    """New York City local personal income tax calculator.

    References:
        - NYS Department of Taxation and Finance, Form IT-201-I Instructions (New York City tax rate schedule):
          https://www.tax.ny.gov/forms/current-forms/it/it201i.htm
    """

    def calculate_income_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        tax_deduction = config.get_local_tax_deduction(City.NEW_YORK_CITY, user.filing)

        # Bracket-based local income tax
        taxable_income = max(Decimal("0"), user.get_reduced_income() - tax_deduction)
        tax_brackets = config.get_local_tax_brackets(City.NEW_YORK_CITY, user.filing)
        return calculate_progressive_tax(taxable_income, tax_brackets)


# Strategy registry
LOCAL_TAX_CALCULATORS: dict[City, LocalTaxCalculator] = {
    City.NEW_YORK_CITY: NewYorkCityTaxCalculator(),
}


def get_local_tax_calculator(city: City | None) -> LocalTaxCalculator:
    if city is None:
        return NoLocalTaxCalculator()
    if city not in LOCAL_TAX_CALCULATORS:
        city_name = city.value if isinstance(city, City) else str(city)
        logger.warning(
            f"Local tax calculator not implemented for {city_name}. "
            f"Falling back to treat as having no local taxes."
        )
        return NoLocalTaxCalculator()
    return LOCAL_TAX_CALCULATORS[city]


def calculate_annual_local_income_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    """Calculates annual local income tax for a given user and configuration.

    References:
        - NYS Department of Taxation and Finance, Form IT-201-I Instructions (New York City resident tax):
          https://www.tax.ny.gov/forms/current-forms/it/it201i.htm
    """
    calculator = get_local_tax_calculator(user.city_of_residence)
    return calculator.calculate_income_tax(user, config)
