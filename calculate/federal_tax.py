from decimal import Decimal
from utils.enums import Filing
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax


def calculate_annual_federal_income_tax(
    user: Person, config: GlobalParameters
) -> Decimal:
    return _calculate_annual_income_tax(
        user,
        tax_brackets=config.get_fed_tax_brackets(user.filing),
        tax_deduction=config.get_fed_tax_deduction(user.filing),
    )


def _calculate_annual_income_tax(
    user: Person, tax_brackets: list[tuple[Decimal, Decimal]], tax_deduction: Decimal
) -> Decimal:
    taxable_income = max(Decimal("0"), user.get_reduced_income() - tax_deduction)
    return calculate_progressive_tax(taxable_income, tax_brackets)


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
