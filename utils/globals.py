import logging
from decimal import Decimal
from utils.enums import Filing, State
from utils.schemas import YearlyTaxSchema

logger = logging.getLogger(__name__)


def calculate_progressive_tax(
    taxable_income: Decimal, brackets: list[tuple[Decimal, Decimal]]
) -> Decimal:
    """Helper to calculate tax on taxable income using progressive tax brackets.

    Each bracket in the list is a tuple of (tax_rate, floor_value).
    """
    taxes_owed = Decimal("0")
    for i in range(len(brackets)):
        tax_percent, floor_value = brackets[i]
        ceiling_value = (
            brackets[i + 1][1] if i + 1 < len(brackets) else Decimal("Infinity")
        )
        if taxable_income > floor_value:
            taxed_amount = min(taxable_income, ceiling_value) - floor_value
            taxes_owed += taxed_amount * tax_percent
        else:
            break
    return taxes_owed


class GlobalParameters:
    """An instantiable configuration context that holds tax tables and inflation rates

    for a specific year, resolving parameters dynamically.
    """

    def __init__(
        self, year: int, inflation_rate: Decimal, yearly_tax: YearlyTaxSchema
    ) -> None:
        self.year: str = str(year)
        self.inflation_rate: Decimal = inflation_rate
        self.yearly_tax: YearlyTaxSchema = yearly_tax

    def get_fed_tax_brackets(self, filing: Filing) -> list[tuple[Decimal, Decimal]]:
        bracket_schema = (
            self.yearly_tax.FederalTax.Individual
            if filing == Filing.INDIVIDUAL
            else self.yearly_tax.FederalTax.Joint
        )
        return [
            (p, lb)
            for p, lb in zip(bracket_schema.Percents, bracket_schema.LowerBounds)
        ]

    def get_fed_tax_deduction(self, filing: Filing) -> Decimal:
        return (
            self.yearly_tax.FederalTax.StandardTaxDeduction
            if filing == Filing.INDIVIDUAL
            else self.yearly_tax.FederalTax.JointTaxDeduction
        )

    def get_fed_capital_gains_brackets(
        self, filing: Filing
    ) -> list[tuple[Decimal, Decimal]]:
        if self.yearly_tax.FederalTax.CapitalGainsTax is None:
            raise ValueError(
                f"Federal Capital Gains Tax brackets configuration is missing in year {self.year}"
            )

        bracket_schema = (
            self.yearly_tax.FederalTax.CapitalGainsTax.Individual
            if filing == Filing.INDIVIDUAL
            else self.yearly_tax.FederalTax.CapitalGainsTax.Joint
        )
        return [
            (p, lb)
            for p, lb in zip(bracket_schema.Percents, bracket_schema.LowerBounds)
        ]

    def get_state_tax_brackets(
        self, state: State, filing: Filing
    ) -> list[tuple[Decimal, Decimal]]:
        if state == State.TEXAS:
            return []
        if state not in self.yearly_tax.StateTax:
            raise ValueError(
                f"State tax brackets configuration is missing for state '{state.value}' in year {self.year}"
            )
        state_schema = self.yearly_tax.StateTax[state]
        bracket_schema = (
            state_schema.Individual
            if filing == Filing.INDIVIDUAL
            else state_schema.Joint
        )
        return [
            (p, lb)
            for p, lb in zip(bracket_schema.Percents, bracket_schema.LowerBounds)
        ]

    def get_state_tax_deduction(self, state: State, filing: Filing) -> Decimal:
        if state == State.TEXAS:
            return Decimal("0")
        if state not in self.yearly_tax.StateTax:
            raise ValueError(
                f"State tax deduction configuration is missing for state '{state.value}' in year {self.year}"
            )
        state_schema = self.yearly_tax.StateTax[state]
        return (
            state_schema.StandardTaxDeduction
            if filing == Filing.INDIVIDUAL
            else state_schema.JointTaxDeduction
        )

    def calculate_state_surcharges(
        self, state: State, surcharge_type: str, amount: Decimal
    ) -> Decimal:
        if state == State.TEXAS:
            return Decimal("0")
        if state not in self.yearly_tax.StateTax:
            raise ValueError(
                f"State tax configuration is missing for state '{state.value}' in year {self.year}"
            )
        state_schema = self.yearly_tax.StateTax[state]
        surcharge_tax = Decimal("0")
        for surcharge in state_schema.Surcharges:
            if surcharge.Type == surcharge_type:
                threshold = surcharge.Threshold or Decimal("0")
                if amount > threshold:
                    surcharge_tax += surcharge.Rate * (amount - threshold)
        return surcharge_tax

    @property
    def social_security_max_taxable(self) -> Decimal:
        return self.yearly_tax.FicaTax.SocialSecurityMaxTaxable

    @property
    def social_security_tax_percent(self) -> Decimal:
        return self.yearly_tax.FicaTax.SocialSecurityTaxPercent

    @property
    def medicare_high_earner_tax(self) -> Decimal:
        return self.yearly_tax.FicaTax.MedicareHighEarnerTax

    @property
    def medicare_high_earner_salary_individual(self) -> Decimal:
        return self.yearly_tax.FicaTax.MedicareHighEarnerSalaryIndividual

    @property
    def medicare_high_earner_salary_joint(self) -> Decimal:
        return self.yearly_tax.FicaTax.MedicareHighEarnerSalaryJoint

    @property
    def medicare_tax_percent(self) -> Decimal:
        return self.yearly_tax.FicaTax.MedicareTaxPercent
