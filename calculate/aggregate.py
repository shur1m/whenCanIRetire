from copy import copy
from decimal import Decimal

from calculate.federal_tax import (
    calculate_annual_federal_income_tax,
    calculate_annual_medicare_tax,
    calculate_annual_social_security_tax,
)
from calculate.state_tax import (
    calculate_annual_state_income_tax,
    calculate_annual_state_payroll_tax,
)
from utils.enums import Frequency
from utils.parameters import Person
from utils.globals import GlobalParameters


def calculate_annual_income_tax(
        user: Person,      config: GlobalParameters) -> Decimal:
    return (
        calculate_annual_federal_income_tax(user, config)
        + calculate_annual_social_security_tax(user, config)
        + calculate_annual_medicare_tax(user, config)
        + calculate_annual_state_income_tax(user, config)
        + calculate_annual_state_payroll_tax(user, config)
    )


def calculate_retirement_deductions_excess(
    user: Person, config: GlobalParameters, user_tax: Decimal
) -> Decimal:
    """Calculates tax savings achieved by contributing to pre-tax retirement accounts (401(k), HSA)."""
    no_deduction_user = copy(user)
    no_deduction_user.accounts = dict()

    return calculate_annual_income_tax(no_deduction_user, config) - user_tax


def calculate_income_distribution_data(
    user: Person, config: GlobalParameters
) -> dict[str, Decimal]:
    """Calculates distribution of gross annual income across categories (taxes, contributions, expenses)."""
    pie_data: dict[str, Decimal] = {
        "Federal Income tax": calculate_annual_federal_income_tax(user, config),
        "Medicare Tax": calculate_annual_medicare_tax(user, config),
        "Social Security Tax": calculate_annual_social_security_tax(user, config),
    }

    state_tax = calculate_annual_state_income_tax(user, config)
    if state_tax > Decimal("0"):
        pie_data["State Tax"] = state_tax

    # Add account contributions
    for account_name, account in user.accounts.items():
        retirement_contributions = Decimal("0")
        if account.regular_investment_frequency == Frequency.MONTHLY:
            retirement_contributions = account.regular_investment_dollar * 12
        elif account.regular_investment_frequency == Frequency.ANNUALLY:
            retirement_contributions = account.regular_investment_dollar
        pie_data[account_name + " contribution"] = retirement_contributions

    # Add other expenses
    for expense_name, expense in user.accumulation_phase_expenses.items():
        pie_data[expense_name] = expense

    # Add remaining income
    remaining_income = user.pre_tax_income - sum(pie_data.values())
    pie_data["Remaining Income"] = remaining_income

    return pie_data
