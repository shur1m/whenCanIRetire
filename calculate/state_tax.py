from decimal import Decimal
from utils.enums import Filing, State
from utils.parameters import Person
from utils.globals import GlobalParameters


class StateTaxCalculator:
    """Base class for state-specific tax calculators."""

    def calculate_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        raise NotImplementedError


class NoStateTaxCalculator(StateTaxCalculator):
    """For states with no income tax (e.g., Texas, or if state_of_residence is None)."""

    def calculate_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        return Decimal("0")


class CaliforniaTaxCalculator(StateTaxCalculator):
    """California state tax calculator including SDI and Mental Health Services taxes."""

    def calculate_tax(self, user: Person, config: GlobalParameters) -> Decimal:
        tax_deduction = config.get_state_tax_deduction(State.CALIFORNIA, user.filing)
        additional_state_tax = Decimal("0")

        state_schema = config.yearly_tax.StateTax.get(State.CALIFORNIA)
        sdi_percent = (
            state_schema.SDITaxPercent
            if state_schema and state_schema.SDITaxPercent is not None
            else Decimal("0.011")
        )
        mhs_percent = (
            state_schema.MHSTaxPercent
            if state_schema and state_schema.MHSTaxPercent is not None
            else Decimal("0.01")
        )
        mhs_threshold = (
            state_schema.MHSTaxThreshold
            if state_schema and state_schema.MHSTaxThreshold is not None
            else Decimal("1000000")
        )

        # SDI tax
        SDI_tax = sdi_percent * user.pre_tax_income

        # Mental Health Services tax (MHS)
        taxable_state_income = user.get_reduced_income() - tax_deduction
        MHS_tax = (
            mhs_percent * (taxable_state_income - mhs_threshold)
            if taxable_state_income > mhs_threshold
            else Decimal("0")
        )
        additional_state_tax += SDI_tax + MHS_tax

        # Bracket-based state income tax
        taxable_income = user.get_reduced_income() - tax_deduction
        tax_brackets = config.get_state_tax_brackets(State.CALIFORNIA, user.filing)

        taxes_owed = Decimal("0")
        for i in range(len(tax_brackets)):
            tax_percent, floor_value = tax_brackets[i]
            ceiling_value = (
                tax_brackets[i + 1][1] - Decimal("1")
                if i + 1 < len(tax_brackets)
                else Decimal("Infinity")
            )
            if taxable_income > ceiling_value:
                taxes_owed += (ceiling_value - floor_value) * tax_percent
            elif taxable_income <= floor_value:
                break
            else:
                taxes_owed += (taxable_income - floor_value) * tax_percent

        return additional_state_tax + taxes_owed


# Strategy registry
STATE_TAX_CALCULATORS: dict[State, StateTaxCalculator] = {
    State.TEXAS: NoStateTaxCalculator(),
    State.CALIFORNIA: CaliforniaTaxCalculator(),
}


def get_state_tax_calculator(state: State | None) -> StateTaxCalculator:
    if state is None:
        return NoStateTaxCalculator()
    return STATE_TAX_CALCULATORS.get(state, NoStateTaxCalculator())


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

        state_schema = config.yearly_tax.StateTax.get(State.CALIFORNIA)
        mhs_percent = (
            state_schema.MHSTaxPercent
            if state_schema and state_schema.MHSTaxPercent is not None
            else Decimal("0.01")
        )
        mhs_threshold = (
            state_schema.MHSTaxThreshold
            if state_schema and state_schema.MHSTaxThreshold is not None
            else Decimal("1000000")
        )

        MHS_tax = (
            mhs_percent * (taxable_income - mhs_threshold)
            if taxable_income > mhs_threshold
            else Decimal("0")
        )

        taxes_owed = Decimal("0")
        for i in range(len(tax_brackets)):
            tax_percent, floor_value = tax_brackets[i]
            ceiling_value = (
                tax_brackets[i + 1][1] - Decimal("1")
                if i + 1 < len(tax_brackets)
                else Decimal("Infinity")
            )
            if taxable_income > ceiling_value:
                taxes_owed += (ceiling_value - floor_value) * tax_percent
            elif taxable_income <= floor_value:
                break
            else:
                taxes_owed += (taxable_income - floor_value) * tax_percent

        return taxes_owed + MHS_tax


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
    if state is None:
        return TexasCapitalGainsCalculator()
    if state not in STATE_CG_CALCULATORS:
        import logging

        logger = logging.getLogger(__name__)
        state_name = state.value if hasattr(state, "value") else str(state)
        logger.warning(
            f"State capital gains calculator not implemented for {state_name}. "
            f"Falling back to treating as ordinary state income tax."
        )
        return FallbackStateCapitalGainsCalculator()
    return STATE_CG_CALCULATORS[state]
