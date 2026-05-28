import logging
from decimal import Decimal
from utils.enums import State
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax

logger = logging.getLogger(__name__)


class StateTaxCalculator:
    """Base class for state-specific tax calculators."""

    def calculate_income_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        raise NotImplementedError

    def calculate_payroll_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return Decimal("0")

    def calculate_capital_gains_tax(
        self,
        capital_gains: Decimal,
        user: Person,
        config: GlobalParameters,
        ordinary_income: Decimal = Decimal("0"),
    ) -> Decimal:
        """Default fallback: treat capital gains as ordinary state income, stacked on top of ordinary income."""
        dummy_total = Person(
            current_age=user.current_age,
            retirement_age=user.retirement_age,
            lifespan=user.lifespan,
            pre_tax_income=ordinary_income + capital_gains,
            state_of_residence=user.state_of_residence,
            filing=user.filing,
        )
        total_tax = self.calculate_income_tax(dummy_total, config)

        dummy_ordinary = Person(
            current_age=user.current_age,
            retirement_age=user.retirement_age,
            lifespan=user.lifespan,
            pre_tax_income=ordinary_income,
            state_of_residence=user.state_of_residence,
            filing=user.filing,
        )
        ordinary_tax = self.calculate_income_tax(dummy_ordinary, config)

        return max(Decimal("0"), total_tax - ordinary_tax)


class NoStateTaxCalculator(StateTaxCalculator):
    """For states with no income tax (e.g., Texas, or if state_of_residence is None)."""

    def calculate_income_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return Decimal("0")

    def calculate_capital_gains_tax(
        self,
        capital_gains: Decimal,
        user: Person,
        config: GlobalParameters,
        ordinary_income: Decimal = Decimal("0"),
    ) -> Decimal:
        return Decimal("0")


class CaliforniaTaxCalculator(StateTaxCalculator):
    """California state tax calculator including SDI and Mental Health Services taxes."""

    def calculate_income_tax(self, user: Person, config: GlobalParameters) -> Decimal:
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
    if state not in STATE_TAX_CALCULATORS:
        state_name = state.value if isinstance(state, State) else str(state)
        logger.warning(
            f"State tax calculator not implemented for {state_name}. "
            f"Falling back to treat as having no state taxes."
        )
        return NoStateTaxCalculator()
    return STATE_TAX_CALCULATORS[state]


def calculate_annual_state_income_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    calculator = get_state_tax_calculator(user.state_of_residence)
    return calculator.calculate_income_tax(user, config)


def calculate_annual_state_payroll_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    calculator = get_state_tax_calculator(user.state_of_residence)
    return calculator.calculate_payroll_tax(user, config)
