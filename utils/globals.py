import logging
from decimal import Decimal
from utils.enums import Filing, State
from utils.schemas import YearlyTaxSchema

logger = logging.getLogger(__name__)


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

    def get_state_tax_brackets(
        self, state: State, filing: Filing
    ) -> list[tuple[Decimal, Decimal]]:
        if state not in self.yearly_tax.StateTax:
            return []
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
        if state not in self.yearly_tax.StateTax:
            return Decimal("0")
        state_schema = self.yearly_tax.StateTax[state]
        return (
            state_schema.StandardTaxDeduction
            if filing == Filing.INDIVIDUAL
            else state_schema.JointTaxDeduction
        )

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
