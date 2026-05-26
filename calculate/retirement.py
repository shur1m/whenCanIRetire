from typing import Union
from decimal import Decimal
from calculate.federal_tax import calculate_annual_federal_income_tax
from calculate.state_tax import (
    calculate_annual_state_income_tax,
    get_state_tax_calculator,
)
from utils.parameters import Person, Account, to_decimal
from utils.globals import GlobalParameters, calculate_progressive_tax


def simulate_account(
    account: Account, config: GlobalParameters
) -> tuple[list[int], list[Decimal]]:
    return account.simulate(config)


def _adjust_for_inflation(
    todays_dollars: Union[Decimal, float, int],
    months: int,
    config: GlobalParameters,
) -> Decimal:
    todays_dollars_dec = to_decimal(todays_dollars)
    inflation_rate_dec = config.inflation_rate
    inflation_multiplier = Decimal("1") + inflation_rate_dec
    inflation_per_month = inflation_multiplier ** (Decimal("1") / Decimal("12"))
    return todays_dollars_dec * (inflation_per_month**months)


def _simulate_accumulation(
    account: Account,
    current_savings: Decimal,
    graph_labels: list[int],
    graph_savings_values: list[Decimal],
) -> Decimal:
    return account.simulate_accumulation(
        current_savings, graph_labels, graph_savings_values
    )


def calculate_retirement_withdrawal_tax(
    amount: Decimal,
    account: Account,
    config: GlobalParameters,
    is_capital_gains: bool = False,
) -> Decimal:
    """Calculates Federal and State taxes for a retirement withdrawal amount.

    Excludes payroll taxes (FICA and California SDI) as they only apply to wage/earned income.

    Sources:
    - IRS Topic No. 409 Capital Gains and Losses: https://www.irs.gov/taxtopics/tc409 (Federal LTCG rates)
    - NerdWallet Capital Gains Tax Rates: https://www.nerdwallet.com/taxes/learn/capital-gains-tax-rates (Federal LTCG brackets)
    - California Franchise Tax Board FTB: https://www.ftb.ca.gov/file/personal/income-types/capital-gains-and-losses.html (State LTCG taxed as ordinary income)
    - California Employment Development Department Wages Sheet (EDD): https://edd.ca.gov/siteassets/files/pdf_pub_ctr/de231a.pdf (SDI payroll tax only applies to wages)
    - Investopedia State Taxes: https://www.investopedia.com/where-can-you-avoid-state-taxes-on-capital-gains-dividends-and-investment-income-11965488 (Texas has 0% state capital gains / income tax)
    """
    user = account.owner
    dummy_person = Person(
        current_age=user.current_age,
        retirement_age=user.retirement_age,
        lifespan=user.lifespan,
        pre_tax_income=amount,
        state_of_residence=user.state_of_residence,
        filing=user.filing,
    )

    # 1. Federal tax calculation
    if is_capital_gains:
        # Standard deduction is applied to the withdrawal amount to find taxable capital gains
        deduction = config.get_fed_tax_deduction(user.filing)
        taxable_gains = max(Decimal("0"), amount - deduction)
        brackets = config.get_fed_capital_gains_brackets(user.filing)
        fed_tax = calculate_progressive_tax(taxable_gains, brackets)
    else:
        # Ordinary federal income tax (FICA is excluded as it only applies to earned wages)
        fed_tax = calculate_annual_federal_income_tax(dummy_person, config)

    # 2. State tax calculation
    if is_capital_gains:
        # State capital gains tax using the registered calculator for the state
        calculator = get_state_tax_calculator(user.state_of_residence)
        state_tax = calculator.calculate_capital_gains_tax(amount, dummy_person, config)
    else:
        # Ordinary state income tax
        state_tax = calculate_annual_state_income_tax(dummy_person, config)

    return fed_tax + state_tax


def _calculate_retirement_pre_tax_income(
    post_tax_income: Decimal,
    account: Account,
    current_savings: Decimal,
    config: GlobalParameters,
    inflation_factor: Decimal = Decimal("1.0"),
) -> Decimal:
    return account.get_pre_tax_withdrawal(
        post_tax_income, current_savings, config, inflation_factor
    )


def _simulate_retirement(
    account: Account,
    current_savings: Decimal,
    graph_labels: list[int],
    graph_savings_values: list[Decimal],
    config: GlobalParameters,
) -> None:
    account.simulate_retirement(
        current_savings, graph_labels, graph_savings_values, config
    )
