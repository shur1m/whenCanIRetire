from decimal import Decimal
from utils.enums import Filing, State
from utils.parameters import Person
from utils.globals import GlobalParameters


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
    if user.state_of_residence == State.TEXAS or user.state_of_residence is None:
        return Decimal("0")

    tax_deduction = config.get_state_tax_deduction(user.state_of_residence, user.filing)
    additional_state_tax = Decimal("0")

    if user.state_of_residence == State.CALIFORNIA:
        # SDI tax applies to 401(k) contributions
        # #?not sure if this applies to HSA contributions, although insignificant
        SDI_tax = Decimal("0.011") * (user.pre_tax_income - tax_deduction)
        MHS_tax = (
            Decimal("0.01") * (user.get_reduced_income() - tax_deduction)
            if user.get_reduced_income() > Decimal("1000000")
            else Decimal("0")
        )  # mental health services tax TODO need to change this to 2million for joint filers
        additional_state_tax += SDI_tax + MHS_tax

    # TODO add a New York statement

    return additional_state_tax + _calculate_annual_income_tax(
        user,
        tax_brackets=config.get_state_tax_brackets(
            user.state_of_residence, user.filing
        ),
        tax_deduction=tax_deduction,
    )


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
