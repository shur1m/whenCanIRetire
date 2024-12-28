import math
from utils.enums import Filing, State
from utils.parameters import Person
from utils.globals import GlobalParameters



# federal income, state income, social security, medicare
def calculate_annual_income_tax(user: Person) -> int:
    return calculate_annual_federal_income_tax(user) + calculate_annual_social_security_tax(user) + calculate_annual_medicare_tax(user) + calculate_annual_state_income_tax(user)

def calculate_annual_federal_income_tax(user: Person) -> int:
    return _calculate_annual_income_tax(user,
                          tax_brackets = GlobalParameters.fed_individual_tax_brackets if user.filing == Filing.INDIVIDUAL else GlobalParameters.fed_joint_tax_brackets,
                          tax_deduction=GlobalParameters.fed_standard_tax_deduction if user.filing == Filing.INDIVIDUAL else GlobalParameters.fed_joint_tax_deduction)

def calculate_annual_state_income_tax(user:Person) -> int:
    tax_deduction = GlobalParameters.state_standard_tax_deduction if user.filing == Filing.INDIVIDUAL else GlobalParameters.state_joint_tax_deduction
    additional_state_tax = 0

    if user.state_of_residence == State.TEXAS or user.state_of_residence == None:
        return 0

    if user.state_of_residence == State.CALIFORNIA:
        SDI_tax = 0.011 * (user.pre_tax_income - tax_deduction) # SDI tax applies to 401(k) contributions #?not sure if this applies to HSA contributions, although insignificant
        MHS_tax = 0.01 * (user.get_reduced_income() - tax_deduction) if user.get_reduced_income() > 1_000_000 else 0# mental health services tax TODO need to change this to 2million for joint filers
        additional_state_tax += SDI_tax + MHS_tax

    return additional_state_tax + _calculate_annual_income_tax(user,
                          tax_brackets = GlobalParameters.state_individual_tax_brackets if user.filing == Filing.INDIVIDUAL else GlobalParameters.state_joint_tax_brackets,
                          tax_deduction=tax_deduction)

def _calculate_annual_income_tax(user: Person, tax_brackets: list[tuple[int, int]], tax_deduction: int) -> int:
    taxable_income = user.get_reduced_income() - tax_deduction

    taxes_owed = 0
    for i in range(len(tax_brackets)):
        tax_percent, floor_value = tax_brackets[i]
        ceiling_value = tax_brackets[i+1][1] - 1 if i+1 < len(tax_brackets) else math.inf
        if taxable_income > ceiling_value:
            taxes_owed += (ceiling_value - floor_value) * tax_percent
        elif taxable_income <= floor_value:
            break
        else:
            taxes_owed += (taxable_income - floor_value) * tax_percent

    return taxes_owed

def calculate_annual_social_security_tax(user: Person) -> int:
    social_security_taxable_income = min(user.get_fica_taxable_income(), GlobalParameters.social_security_max_taxable)
    return social_security_taxable_income * GlobalParameters.social_security_tax_percent

def calculate_annual_medicare_tax(user: Person) -> int:
    taxes_owed = 0
    medicare_high_earner_salary = GlobalParameters.medicare_high_earner_salary_individual \
        if user.filing == Filing.INDIVIDUAL else GlobalParameters.medicare_high_earner_salary_joint
    taxes_owed += user.get_fica_taxable_income() * GlobalParameters.medicare_tax_percent
    if user.get_fica_taxable_income() > medicare_high_earner_salary:
        taxes_owed += (user.get_fica_taxable_income() - medicare_high_earner_salary) * GlobalParameters.medicare_high_earner_tax
    
    return taxes_owed