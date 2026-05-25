from decimal import Decimal
from utils.enums import Filing, State
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax


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
        taxable_income = max(Decimal("0"), user.get_reduced_income() - tax_deduction)
        tax_brackets = config.get_state_tax_brackets(State.CALIFORNIA, user.filing)
        taxes_owed = calculate_progressive_tax(taxable_income, tax_brackets)

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
