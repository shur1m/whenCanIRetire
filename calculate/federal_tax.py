from decimal import Decimal
import copy
from utils.enums import Filing, State, Frequency
from utils.parameters import Person
from utils.globals import GlobalParameters
from calculate.state_tax import get_state_tax_calculator


def calculate_annual_income_tax(user: Person, config: GlobalParameters) -> Decimal:
    return (
        calculate_annual_federal_income_tax(user, config)
        + calculate_annual_social_security_tax(user, config)
        + calculate_annual_medicare_tax(user, config)
        + calculate_annual_state_income_tax(user, config)
    )


def calculate_annual_federal_income_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    return _calculate_annual_income_tax(
        user,
        tax_brackets=config.get_fed_tax_brackets(user.filing),
        tax_deduction=config.get_fed_tax_deduction(user.filing),
    )


def calculate_annual_state_income_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    calculator = get_state_tax_calculator(user.state_of_residence)
    return calculator.calculate_tax(user, config)


def _calculate_annual_income_tax(
    user: Person, tax_brackets: list[tuple[Decimal, Decimal]], tax_deduction: Decimal
) -> Decimal:
    taxable_income = user.get_reduced_income() - tax_deduction

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

    return taxes_owed


def calculate_annual_social_security_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    social_security_taxable_income = min(
        user.get_fica_taxable_income(), config.social_security_max_taxable
    )
    return social_security_taxable_income * config.social_security_tax_percent


def calculate_annual_medicare_tax(user: Person, config: GlobalParameters) -> Decimal:
    taxes_owed = Decimal("0")
    medicare_high_earner_salary = (
        config.medicare_high_earner_salary_individual
        if user.filing == Filing.INDIVIDUAL
        else config.medicare_high_earner_salary_joint
    )
    taxes_owed += user.get_fica_taxable_income() * config.medicare_tax_percent
    if user.get_fica_taxable_income() > medicare_high_earner_salary:
        taxes_owed += (
            user.get_fica_taxable_income() - medicare_high_earner_salary
        ) * config.medicare_high_earner_tax

    return taxes_owed


def calculate_retirement_deductions_excess(
    user: Person, config: GlobalParameters, user_tax: Decimal
) -> Decimal:
    """Calculates tax savings achieved by contributing to pre-tax retirement accounts (401(k), HSA)."""
    no_deduction_user = copy.copy(user)
    no_deduction_user.accounts = dict()
    no_deduction_user.income_tax_deductions = Decimal("0")

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
