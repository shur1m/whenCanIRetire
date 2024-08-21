import math
from utils.enums import AccountType, Filing, Frequency, MonthlyCompoundType, State
from utils.parameters import Account, Person
from utils.globals import GlobalParameters


def adjust_for_inflation(todays_dollars: int,  months: int) -> int:
    inflation_multiplier = 1 + GlobalParameters.inflation_rate
    inflation_per_month = math.pow(inflation_multiplier, 1/12)
    return todays_dollars * math.pow(inflation_per_month, months)

# federal income, social security, medicare
# TODO add state tax
def calculate_annual_income_tax(user: Person) -> int:
    return calculate_annual_federal_income_tax(user) + calculate_annual_social_security_tax(user) + calculate_annual_medicare_tax(user) + calculate_annual_state_income_tax(user)

def calculate_annual_federal_income_tax(user: Person) -> int:
    return _calculate_annual_income_tax(user,
                          tax_brackets = GlobalParameters.fed_individual_tax_brackets if user.filing == Filing.INDIVIDUAL else GlobalParameters.fed_joint_tax_brackets,
                          tax_deduction=GlobalParameters.standard_tax_deduction if user.filing == Filing.INDIVIDUAL else GlobalParameters.joint_tax_deduction)

def calculate_annual_state_income_tax(user:Person) -> int:
    tax_deduction = GlobalParameters.state_standard_tax_deduction if user.filing == Filing.INDIVIDUAL else GlobalParameters.state_joint_tax_deduction
    additional_state_tax = 0

    if user.state_of_residence == State.TEXAS or user.state_of_residence == None:
        return 0

    if user.state_of_residence == State.CALIFORNIA:
        SDI_tax = 0.011 * (user.pre_tax_income - tax_deduction) # SDI tax applies to 401(k) contributions #?not sure if this applies to HSA contributions, although insignificant
        MHS_tax = 0.01 * (user.get_taxable_income() - tax_deduction) if user.get_taxable_income() > 1_000_000 else 0# mental health services tax TODO need to change this to 2million for joint filers
        additional_state_tax += SDI_tax + MHS_tax

    return additional_state_tax + _calculate_annual_income_tax(user,
                          tax_brackets = GlobalParameters.state_individual_tax_brackets if user.filing == Filing.INDIVIDUAL else GlobalParameters.state_joint_tax_brackets,
                          tax_deduction=tax_deduction)

def _calculate_annual_income_tax(user: Person, tax_brackets: list[tuple[int, int]], tax_deduction: int) -> int:
    taxable_income = user.get_taxable_income() - tax_deduction

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
    taxes_owed += user.get_fica_taxable_income() * GlobalParameters.medicare_tax
    if user.get_fica_taxable_income() > medicare_high_earner_salary:
        taxes_owed += (user.get_fica_taxable_income() - medicare_high_earner_salary) * GlobalParameters.medicare_high_earner_tax
    
    return taxes_owed

def calculate_pre_tax_income(post_tax_income: int):
    # binary search
    left = post_tax_income
    right = post_tax_income * 5
    pre_tax_income = right

    # stop once error is smaller than cent
    while abs(right - left) > 0.01:
        pre_tax_income = left + (right - left) / 2
        if pre_tax_income - calculate_annual_income_tax(Person(pre_tax_income=pre_tax_income)) > post_tax_income:
            right = pre_tax_income
        else:
            left = pre_tax_income
    
    return round(pre_tax_income, 2)

def simulate_account(account: Account):
    graph_labels = []
    graph_savings_values = []
    current_savings = account.initial_savings

    # accumulation phase
    for year in range(account.owner.retirement_age - account.owner.current_age):
        #compounding yearly 
        if account.compound_frequency == Frequency.ANNUALLY:
            current_savings *= (1+account.annual_investment_return)

        for month in range(12):
            # compounding monthly
            if account.compound_frequency == Frequency.MONTHLY:
                if account.compound_type == MonthlyCompoundType.DIVIDE:
                    current_savings *= 1 + account.annual_investment_return/12
                elif account.compound_type == MonthlyCompoundType.ROOT:
                    current_savings *= math.pow(1+ account.annual_investment_return, 1/12)

            # monthly addition to investment account
            if account.regular_investment_frequency == Frequency.MONTHLY:
                current_savings += account.regular_investment_dollar * math.pow(math.pow(1 + account.annual_investment_increase, 1/12), year*12+month)


        # yearly addition to investment account
        if account.regular_investment_frequency == Frequency.ANNUALLY:
            current_savings += account.regular_investment_dollar * math.pow(1 + account.annual_investment_increase, year)

        graph_labels.append(account.owner.current_age + year)
        graph_savings_values.append(current_savings)

    savings_at_retirement = current_savings

    # retirement phase (no social security)
    retirement_months = 0
    annual_retirement_withdrawal = account.annual_retirement_post_tax_expense
    
    # binary search pre tax expense given post tax expense for Generic and Traditional account withdrawals, Roth/HSA withdrawals are not adjusted
    if account.account_type == AccountType.GENERIC or account.account_type == AccountType.TRADITIONAL:
        annual_retirement_withdrawal = calculate_pre_tax_income(annual_retirement_withdrawal)

    while current_savings >= annual_retirement_withdrawal/12 and \
          account.owner.retirement_age + retirement_months//12 < account.owner.lifespan:

        # each month, subtract monthly "paycheck" and compound
        months_since_today = (account.owner.retirement_age - account.owner.current_age) * 12 + retirement_months
        current_savings -= adjust_for_inflation(annual_retirement_withdrawal/12, months_since_today)
        
        if account.compound_frequency == Frequency.MONTHLY:
            current_savings *= math.pow(1 + account.annual_retirement_return, 1/12)
        elif account.compound_frequency == Frequency.ANNUALLY and retirement_months % 12 == 0:
            current_savings *= 1 + account.annual_retirement_return

        # add to remaining months
        retirement_months += 1

        if retirement_months % 12 == 0:
            graph_labels.append(account.owner.retirement_age + retirement_months//12)
            graph_savings_values.append(current_savings)


    if current_savings < 0:
        graph_labels.append(account.owner.retirement_age + retirement_months//12 + 1)
        graph_savings_values.append(0)
    return graph_labels, graph_savings_values