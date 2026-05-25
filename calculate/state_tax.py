from decimal import Decimal
from utils.enums import State
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax


class StateTaxCalculator:
    """Base class for state-specific tax calculators."""

    def calculate_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        raise NotImplementedError

    def calculate_payroll_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return Decimal("0")


class NoStateTaxCalculator(StateTaxCalculator):
    """For states with no income tax (e.g., Texas, or if state_of_residence is None)."""

    def calculate_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return Decimal("0")


class CaliforniaTaxCalculator(StateTaxCalculator):
    """California state tax calculator including SDI and Mental Health Services taxes."""

    def calculate_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        tax_deduction = config.get_state_tax_deduction(State.CALIFORNIA, user.filing)

        # Bracket-based state income tax
        taxable_income = max(Decimal("0"), user.get_reduced_income() - tax_deduction)
        tax_brackets = config.get_state_tax_brackets(State.CALIFORNIA, user.filing)
        taxes_owed = calculate_progressive_tax(taxable_income, tax_brackets)

        # Apply any ordinary surcharges dynamically
        taxable_state_income = user.get_reduced_income() - tax_deduction
        taxes_owed += config.calculate_state_surcharges(
            State.CALIFORNIA, "ordinary", taxable_state_income
        )

        return taxes_owed

    def calculate_payroll_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return config.calculate_state_surcharges(
            State.CALIFORNIA, "payroll", user.pre_tax_income
        )


# Strategy registry
STATE_TAX_CALCULATORS: dict[State, StateTaxCalculator] = {
    State.TEXAS: NoStateTaxCalculator(),
    State.CALIFORNIA: CaliforniaTaxCalculator(),
}


def get_state_tax_calculator(state: State | None) -> StateTaxCalculator:
    if state is None:
        return NoStateTaxCalculator()
    return STATE_TAX_CALCULATORS.get(state, NoStateTaxCalculator())


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
