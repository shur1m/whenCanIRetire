import json
import logging

from utils.parameters import Person, State

logger = logging.getLogger(__name__)

class GlobalParameters:
    year = None
    inflation_rate: int = 0.03

    # federal tax brackets (percentage, floor/bottom value of bracket)
    fed_individual_tax_brackets: list[tuple[int, int]] = None
    fed_joint_tax_brackets: list[tuple[int, int]] = None
    fed_standard_tax_deduction: int = None
    fed_joint_tax_deduction: int = None

    # state tax brackets
    state_individual_tax_brackets: list[tuple[int, int]] = None
    state_joint_tax_brackets: list[tuple[int, int]] = None
    state_standard_tax_deduction: int = None
    state_joint_tax_deduction: int = None
    
    social_security_max_taxable: int = None
    social_security_tax_percent: int = None

    medicare_high_earner_tax = None
    medicare_high_earner_salary_individual = None
    medicare_high_earner_salary_joint = None
    medicare_tax_percent = None # different if you are self-employed

    def configure(year: int, user: Person, inflation_rate = 0.03) -> None:
        GlobalParameters.inflation_rate = inflation_rate
        year = str(year)
        GlobalParameters.year = year
        
        with open('config/tax.json') as tax_json:
            tax_dict = json.load(tax_json)[year]

            GlobalParameters._parse_federal_tax(tax_dict["FederalTax"])
            GlobalParameters._parse_state_tax(tax_dict["StateTax"], user)
            GlobalParameters._parse_fica_tax(tax_dict["FicaTax"])
            

    def _parse_federal_tax(federal_tax):
        federal_tax_individual = federal_tax["Individual"]
        federal_tax_joint = federal_tax["Joint"]

        GlobalParameters.fed_individual_tax_brackets = GlobalParameters._parse_tax_bracket(federal_tax_individual)
        GlobalParameters.fed_joint_tax_brackets = GlobalParameters._parse_tax_bracket(federal_tax_joint)
        GlobalParameters.fed_standard_tax_deduction = federal_tax["StandardTaxDeduction"]
        GlobalParameters.fed_joint_tax_deduction = federal_tax["JointTaxDeduction"]

    def _parse_state_tax(state_tax, user: Person):
        if user.state_of_residence == State.TEXAS:
            return
        
        state_tax = state_tax[user.state_of_residence]
        state_tax_individual = state_tax["Individual"]
        state_tax_joint = state_tax["Joint"]

        GlobalParameters.state_individual_tax_brackets = GlobalParameters._parse_tax_bracket(state_tax_individual)
        GlobalParameters.state_joint_tax_brackets = GlobalParameters._parse_state_tax(state_tax_joint)
        GlobalParameters.state_standard_tax_deduction = state_tax["StandardTaxDeduction"]
        GlobalParameters.state_joint_tax_deduction = state_tax["JointTaxDeduction"]
        
    def _parse_fica_tax(fica_tax):
        GlobalParameters.social_security_max_taxable = fica_tax["SocialSecurityMaxTaxable"]
        GlobalParameters.social_security_tax_percent = fica_tax["SocialSecurityTaxPercent"]
        GlobalParameters.medicare_high_earner_tax = fica_tax["MedicareHighEarnerTax"]
        GlobalParameters.medicare_high_earner_salary_individual = fica_tax["MedicareHighEarnerSalaryIndividual"]
        GlobalParameters.medicare_high_earner_salary_joint = fica_tax["MedicareHighEarnerSalaryJoint"]
        GlobalParameters.medicare_tax_percent = fica_tax["MedicareTaxPercent"]

    def _parse_tax_bracket(individual_or_joint_bracket: dict) -> list[tuple]:
        lower_bounds = individual_or_joint_bracket["LowerBounds"]
        percents = individual_or_joint_bracket["Percents"]
        return list(zip(percents, lower_bounds))