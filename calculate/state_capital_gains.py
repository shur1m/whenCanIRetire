import logging
from decimal import Decimal
from utils.enums import State
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax
from calculate.state_tax import get_state_tax_calculator

logger = logging.getLogger(__name__)


class StateCapitalGainsCalculator:
    """Base class for state-specific capital gains tax calculators.

    Source: California Franchise Tax Board (https://www.ftb.ca.gov/file/personal/income-types/capital-gains-and-losses.html)
    Source: California Employment Development Department Wages Sheet (https://edd.ca.gov/siteassets/files/pdf_pub_ctr/de231a.pdf)
    Source: Investopedia State Taxes (https://www.investopedia.com/where-can-you-avoid-state-taxes-on-capital-gains-dividends-and-investment-income-11965488)
    """

    def calculate_capital_gains_tax(
        self, capital_gains: Decimal, user: Person, config: GlobalParameters
    ) -> Decimal:
        raise NotImplementedError


class TexasCapitalGainsCalculator(StateCapitalGainsCalculator):
    """Texas has no state income or capital gains tax.

    Source: Investopedia (https://www.investopedia.com/where-can-you-avoid-state-taxes-on-capital-gains-dividends-and-investment-income-11965488)
    """

    def calculate_capital_gains_tax(
        self, capital_gains: Decimal, user: Person, config: GlobalParameters
    ) -> Decimal:
        return Decimal("0")


class CaliforniaCapitalGainsCalculator(StateCapitalGainsCalculator):
    """California taxes capital gains as ordinary income, but excludes SDI payroll tax.

    Source: California Franchise Tax Board (https://www.ftb.ca.gov/file/personal/income-types/capital-gains-and-losses.html)
    Source: California Employment Development Department Wages Sheet (https://edd.ca.gov/siteassets/files/pdf_pub_ctr/de231a.pdf)
    """

    def calculate_capital_gains_tax(
        self, capital_gains: Decimal, user: Person, config: GlobalParameters
    ) -> Decimal:
        tax_deduction = config.get_state_tax_deduction(State.CALIFORNIA, user.filing)
        taxable_income = max(Decimal("0"), capital_gains - tax_deduction)
        tax_brackets = config.get_state_tax_brackets(State.CALIFORNIA, user.filing)
        taxes_owed = calculate_progressive_tax(taxable_income, tax_brackets)

        taxes_owed += config.calculate_state_surcharges(
            State.CALIFORNIA, "ordinary", taxable_income
        )

        return taxes_owed


class FallbackStateCapitalGainsCalculator(StateCapitalGainsCalculator):
    """Fallback calculator for states we don't explicitly implement.

    Uses the state's ordinary income tax calculator on the capital gains amount.
    """

    def calculate_capital_gains_tax(
        self, capital_gains: Decimal, user: Person, config: GlobalParameters
    ) -> Decimal:
        dummy_person = Person(
            current_age=user.current_age,
            retirement_age=user.retirement_age,
            lifespan=user.lifespan,
            pre_tax_income=capital_gains,
            state_of_residence=user.state_of_residence,
            filing=user.filing,
        )
        calculator = get_state_tax_calculator(user.state_of_residence)
        return calculator.calculate_tax(dummy_person, config)


STATE_CG_CALCULATORS: dict[State, StateCapitalGainsCalculator] = {
    State.TEXAS: TexasCapitalGainsCalculator(),
    State.CALIFORNIA: CaliforniaCapitalGainsCalculator(),
}


def get_state_capital_gains_calculator(
    state: State | None,
) -> StateCapitalGainsCalculator:
    if state is None or state not in STATE_CG_CALCULATORS:
        state_name = state.value if isinstance(state, State) else str(state)
        logger.warning(
            f"State capital gains calculator not implemented for {state_name}. "
            f"Falling back to treating as ordinary state income tax."
        )
        return FallbackStateCapitalGainsCalculator()
    return STATE_CG_CALCULATORS[state]
