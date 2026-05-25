from decimal import Decimal
from utils.parameters import Person
from utils.globals import GlobalParameters
from calculate.state_tax_calculators import get_state_tax_calculator


def calculate_annual_state_income_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    calculator = get_state_tax_calculator(user.state_of_residence)
    return calculator.calculate_tax(user, config)


def calculate_annual_state_payroll_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    calculator = get_state_tax_calculator(user.state_of_residence)
    return calculator.calculate_payroll_tax(user, config)
