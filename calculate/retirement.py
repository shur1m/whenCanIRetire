import math
from calculate.tax import calculate_annual_income_tax
from utils.parameters import Person, Account
from utils.enums import Frequency, MonthlyCompoundType, AccountType
from utils.globals import GlobalParameters

def simulate_account(account: Account):
    graph_labels = []
    graph_savings_values = []
    current_savings = account.initial_savings

    savings_at_retirement = _simulate_accumulation(account, current_savings, graph_labels, graph_savings_values)
    _simulate_retirement(account, savings_at_retirement, graph_labels, graph_savings_values)

    return graph_labels, graph_savings_values

def _adjust_for_inflation(todays_dollars: int,  months: int) -> int:
    inflation_multiplier = 1 + GlobalParameters.inflation_rate
    inflation_per_month = math.pow(inflation_multiplier, 1/12)
    return todays_dollars * math.pow(inflation_per_month, months)

def _calculate_pre_tax_income(post_tax_income: int):
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

def _simulate_accumulation(
        account: Account,
        current_savings: float,
        graph_labels: list[int],
        graph_savings_values: list[float]
) -> float:
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
        
    return current_savings

def _simulate_retirement(
        account: Account,
        current_savings: float,
        graph_labels: list[int],
        graph_savings_values: list[float]
):
    # retirement phase (no social security)
    retirement_months = 0
    annual_retirement_withdrawal = account.annual_retirement_post_tax_expense
    
    # binary search pre tax expense given post tax expense for Generic and Traditional account withdrawals, Roth/HSA withdrawals are not adjusted
    if account.account_type == AccountType.GENERIC or account.account_type == AccountType.TRADITIONAL:
        annual_retirement_withdrawal = _calculate_pre_tax_income(annual_retirement_withdrawal)

    while current_savings >= annual_retirement_withdrawal/12 and \
          account.owner.retirement_age + retirement_months//12 < account.owner.lifespan:

        # each month, subtract monthly "paycheck" and compound
        months_since_today = (account.owner.retirement_age - account.owner.current_age) * 12 + retirement_months
        current_savings -= _adjust_for_inflation(annual_retirement_withdrawal/12, months_since_today)
        
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