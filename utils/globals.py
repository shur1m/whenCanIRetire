import json
import logging
from decimal import Decimal
from typing import Optional, Union

from utils.parameters import Person, State

logger = logging.getLogger(__name__)


class GlobalParameters:
    year: Optional[str] = None
    inflation_rate: Decimal = Decimal("0.03")

    # federal tax brackets (percentage, floor/bottom value of bracket)
    fed_individual_tax_brackets: list[tuple[Decimal, Decimal]] = []
    fed_joint_tax_brackets: list[tuple[Decimal, Decimal]] = []
    fed_standard_tax_deduction: Decimal = Decimal("0")
    fed_joint_tax_deduction: Decimal = Decimal("0")

    # state tax brackets
    state_individual_tax_brackets: list[tuple[Decimal, Decimal]] = []
    state_joint_tax_brackets: list[tuple[Decimal, Decimal]] = []
    state_standard_tax_deduction: Decimal = Decimal("0")
    state_joint_tax_deduction: Decimal = Decimal("0")

    social_security_max_taxable: Decimal = Decimal("0")
    social_security_tax_percent: Decimal = Decimal("0")

    medicare_high_earner_tax: Decimal = Decimal("0")
    medicare_high_earner_salary_individual: Decimal = Decimal("0")
    medicare_high_earner_salary_joint: Decimal = Decimal("0")
    medicare_tax_percent: Decimal = Decimal("0")  # different if you are self-employed

    @classmethod
    def configure(
        cls, year: int, user: Person, inflation_rate: Union[Decimal, float, int] = 0.03
    ) -> None:
        GlobalParameters.inflation_rate = Decimal(str(inflation_rate))
        year_str = str(year)
        GlobalParameters.year = year_str

        with open("config/tax.json") as tax_json:
            tax_dict = json.load(tax_json, parse_float=Decimal)[year_str]

            GlobalParameters._parse_federal_tax(tax_dict["FederalTax"])
            GlobalParameters._parse_state_tax(tax_dict["StateTax"], user)
            GlobalParameters._parse_fica_tax(tax_dict["FicaTax"])

    @classmethod
    def _parse_federal_tax(cls, federal_tax):
        federal_tax_individual = federal_tax["Individual"]
        federal_tax_joint = federal_tax["Joint"]

        GlobalParameters.fed_individual_tax_brackets = (
            GlobalParameters._parse_tax_bracket(federal_tax_individual)
        )
        GlobalParameters.fed_joint_tax_brackets = GlobalParameters._parse_tax_bracket(
            federal_tax_joint
        )
        GlobalParameters.fed_standard_tax_deduction = Decimal(
            str(federal_tax["StandardTaxDeduction"])
        )
        GlobalParameters.fed_joint_tax_deduction = Decimal(
            str(federal_tax["JointTaxDeduction"])
        )

    @classmethod
    def _parse_state_tax(cls, state_tax, user: Person):
        if user.state_of_residence == State.TEXAS or user.state_of_residence is None:
            return

        state_tax = state_tax[user.state_of_residence]
        state_tax_individual = state_tax["Individual"]
        state_tax_joint = state_tax["Joint"]

        GlobalParameters.state_individual_tax_brackets = (
            GlobalParameters._parse_tax_bracket(state_tax_individual)
        )
        GlobalParameters.state_joint_tax_brackets = GlobalParameters._parse_tax_bracket(
            state_tax_joint
        )
        GlobalParameters.state_standard_tax_deduction = Decimal(
            str(state_tax["StandardTaxDeduction"])
        )
        GlobalParameters.state_joint_tax_deduction = Decimal(
            str(state_tax["JointTaxDeduction"])
        )

    @classmethod
    def _parse_fica_tax(cls, fica_tax):
        GlobalParameters.social_security_max_taxable = Decimal(
            str(fica_tax["SocialSecurityMaxTaxable"])
        )
        GlobalParameters.social_security_tax_percent = Decimal(
            str(fica_tax["SocialSecurityTaxPercent"])
        )
        GlobalParameters.medicare_high_earner_tax = Decimal(
            str(fica_tax["MedicareHighEarnerTax"])
        )
        GlobalParameters.medicare_high_earner_salary_individual = Decimal(
            str(fica_tax["MedicareHighEarnerSalaryIndividual"])
        )
        GlobalParameters.medicare_high_earner_salary_joint = Decimal(
            str(fica_tax["MedicareHighEarnerSalaryJoint"])
        )
        GlobalParameters.medicare_tax_percent = Decimal(
            str(fica_tax["MedicareTaxPercent"])
        )

    @classmethod
    def _parse_tax_bracket(
        cls, individual_or_joint_bracket: dict
    ) -> list[tuple[Decimal, Decimal]]:
        lower_bounds = individual_or_joint_bracket["LowerBounds"]
        percents = individual_or_joint_bracket["Percents"]
        return [
            (Decimal(str(p)), Decimal(str(lb))) for p, lb in zip(percents, lower_bounds)
        ]
