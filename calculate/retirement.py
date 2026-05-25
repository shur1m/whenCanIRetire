from typing import Union
from decimal import Decimal, ROUND_HALF_UP
from calculate.federal_tax import (
    calculate_annual_income_tax,
    calculate_annual_federal_income_tax,
    calculate_annual_state_income_tax,
)
from calculate.state_capital_gains import get_state_capital_gains_calculator
from utils.parameters import Person, Account, to_decimal
from utils.enums import Frequency, MonthlyCompoundType, AccountType, State
from utils.globals import GlobalParameters


def simulate_account(
    account: Account, config: GlobalParameters
) -> tuple[list[int], list[Decimal]]:
    graph_labels = []
    graph_savings_values = []
    current_savings = account.initial_savings

    savings_at_retirement = _simulate_accumulation(
        account, current_savings, graph_labels, graph_savings_values
    )
    _simulate_retirement(
        account,
        savings_at_retirement,
        graph_labels,
        graph_savings_values,
        config,
    )

    return graph_labels, graph_savings_values


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
    for year in range(account.owner.retirement_age - account.owner.current_age):
        # compounding yearly
        if account.compound_frequency == Frequency.ANNUALLY:
            current_savings *= Decimal("1") + account.annual_investment_return

        for month in range(12):
            # compounding monthly
            if account.compound_frequency == Frequency.MONTHLY:
                if account.compound_type == MonthlyCompoundType.DIVIDE:
                    current_savings *= Decimal(
                        "1"
                    ) + account.annual_investment_return / Decimal("12")
                elif account.compound_type == MonthlyCompoundType.ROOT:
                    current_savings *= (
                        Decimal("1") + account.annual_investment_return
                    ) ** (Decimal("1") / Decimal("12"))

            # monthly addition to investment account
            if account.regular_investment_frequency == Frequency.MONTHLY:
                contribution = account.regular_investment_dollar * (
                    (
                        (Decimal("1") + account.annual_investment_increase)
                        ** (Decimal("1") / Decimal("12"))
                    )
                    ** (year * 12 + month)
                )
                current_savings += contribution
                if account.account_type == AccountType.GENERIC:
                    account.cost_basis += contribution

        # yearly addition to investment account
        if account.regular_investment_frequency == Frequency.ANNUALLY:
            contribution = account.regular_investment_dollar * (
                (Decimal("1") + account.annual_investment_increase) ** year
            )
            current_savings += contribution
            if account.account_type == AccountType.GENERIC:
                account.cost_basis += contribution

        graph_labels.append(account.owner.current_age + year)
        graph_savings_values.append(current_savings)

    return current_savings


def _calculate_progressive_tax(
    taxable_income: Decimal, brackets: list[tuple[Decimal, Decimal]]
) -> Decimal:
    """Helper to calculate tax on taxable income using progressive tax brackets.

    Each bracket in the list is a tuple of (tax_rate, floor_value).
    """
    taxes_owed = Decimal("0")
    for i in range(len(brackets)):
        tax_percent, floor_value = brackets[i]
        ceiling_value = (
            brackets[i + 1][1] - Decimal("1")
            if i + 1 < len(brackets)
            else Decimal("Infinity")
        )
        if taxable_income > ceiling_value:
            taxes_owed += (ceiling_value - floor_value) * tax_percent
        elif taxable_income <= floor_value:
            break
        else:
            taxes_owed += (taxable_income - floor_value) * tax_percent
    return taxes_owed


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
        fed_tax = _calculate_progressive_tax(taxable_gains, brackets)
    else:
        # Ordinary federal income tax (FICA is excluded as it only applies to earned wages)
        fed_tax = calculate_annual_federal_income_tax(dummy_person, config)

    # 2. State tax calculation
    if is_capital_gains:
        # State capital gains tax using the registered calculator for the state
        calculator = get_state_capital_gains_calculator(user.state_of_residence)
        state_tax = calculator.calculate_capital_gains_tax(amount, dummy_person, config)
    else:
        # Ordinary state income tax
        state_tax = calculate_annual_state_income_tax(dummy_person, config)
        # Exclude California SDI from retirement withdrawals (SDI only applies to wages)
        if user.state_of_residence == State.CALIFORNIA:
            state_schema = config.yearly_tax.StateTax.get(State.CALIFORNIA)
            sdi_percent = (
                state_schema.SDITaxPercent
                if state_schema and state_schema.SDITaxPercent is not None
                else Decimal("0.011")
            )
            state_tax = max(Decimal("0"), state_tax - sdi_percent * amount)

    return fed_tax + state_tax


def _calculate_retirement_pre_tax_income(
    post_tax_income: Decimal,
    account: Account,
    current_savings: Decimal,
    config: GlobalParameters,
) -> Decimal:
    """Calculates the pre-tax monthly withdrawal required to meet a post-tax target.

    Since tax brackets are structured on an annual basis, we project the monthly
    withdrawal to an annual rate, compute the annual tax, and divide by 12.
    We use binary search to solve for:
        pre_tax_income - tax_monthly(pre_tax_income) == post_tax_income
    """
    # Roth and HSA accounts are 100% tax-free, so pre-tax equals post-tax
    if account.account_type not in (AccountType.GENERIC, AccountType.TRADITIONAL):
        return post_tax_income

    # Initialize binary search range
    left = post_tax_income
    right = post_tax_income * Decimal("5")  # Safe upper bound
    pre_tax_income = right

    # Narrow down the pre-tax income until the precision is within a cent
    while abs(right - left) > Decimal("0.01"):
        pre_tax_income = left + (right - left) / Decimal("2")
        pre_tax_annual = pre_tax_income * Decimal("12")

        if account.account_type == AccountType.TRADITIONAL:
            # Traditional accounts are taxed on 100% of the withdrawal amount as ordinary income
            tax_annual = calculate_retirement_withdrawal_tax(
                pre_tax_annual, account, config, is_capital_gains=False
            )
        else:
            # For GENERIC (Brokerage) accounts, tax is only applied to the capital gains portion.
            # The gain ratio is determined based on the current cost basis.
            gain_ratio = Decimal("0")
            if current_savings > 0:
                gain_ratio = max(
                    Decimal("0"),
                    (current_savings - account.cost_basis) / current_savings,
                )
            gains_annual = pre_tax_annual * gain_ratio
            tax_annual = calculate_retirement_withdrawal_tax(
                gains_annual, account, config, is_capital_gains=True
            )

        tax_monthly = tax_annual / Decimal("12")
        net_monthly = pre_tax_income - tax_monthly

        if net_monthly > post_tax_income:
            right = pre_tax_income
        else:
            left = pre_tax_income

    return pre_tax_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _simulate_retirement(
    account: Account,
    current_savings: Decimal,
    graph_labels: list[int],
    graph_savings_values: list[Decimal],
    config: GlobalParameters,
) -> None:
    # retirement phase (no social security)
    retirement_months = 0
    post_tax_annual_expense = account.annual_retirement_post_tax_expense
    post_tax_monthly_withdrawal = post_tax_annual_expense / Decimal("12")

    while (
        current_savings > Decimal("0")
        and account.owner.retirement_age + retirement_months // 12
        < account.owner.lifespan
    ):
        months_since_today = (
            account.owner.retirement_age - account.owner.current_age
        ) * 12 + retirement_months

        # Inflate the target monthly post-tax withdrawal
        inflated_post_tax_monthly = _adjust_for_inflation(
            post_tax_monthly_withdrawal,
            months_since_today,
            config,
        )

        # Calculate the pre-tax monthly withdrawal needed dynamically based on current cost basis
        pre_tax_monthly = _calculate_retirement_pre_tax_income(
            inflated_post_tax_monthly,
            account,
            current_savings,
            config,
        )

        if current_savings < pre_tax_monthly:
            withdrawal_pre_tax = current_savings
            current_savings = Decimal("0")
        else:
            withdrawal_pre_tax = pre_tax_monthly
            current_savings -= pre_tax_monthly

        # If it's a GENERIC account, decrease cost_basis proportionally
        if account.account_type == AccountType.GENERIC and current_savings > Decimal(
            "0"
        ):
            gain_ratio = max(
                Decimal("0"),
                (current_savings + withdrawal_pre_tax - account.cost_basis)
                / (current_savings + withdrawal_pre_tax),
            )
            # When withdrawing, the cost basis is reduced by the cost basis of the assets sold.
            # Under the Average Basis Method (IRS Publication 550), the cost basis per dollar withdrawn is
            # cost_basis / current_savings. Therefore, the cost basis is reduced by:
            # cost_basis_withdrawn = withdrawal_pre_tax * (cost_basis / current_savings)
            # which is mathematically equivalent to: withdrawal_pre_tax * (1 - gain_ratio).
            # Source: IRS Publication 550 (Investment Income and Expenses): https://www.irs.gov/publications/p550
            cost_basis_withdrawn = withdrawal_pre_tax * (Decimal("1") - gain_ratio)
            account.cost_basis = max(
                Decimal("0"), account.cost_basis - cost_basis_withdrawn
            )
        elif account.account_type == AccountType.GENERIC and current_savings == Decimal(
            "0"
        ):
            account.cost_basis = Decimal("0")

        if account.compound_frequency == Frequency.MONTHLY:
            current_savings *= (Decimal("1") + account.annual_retirement_return) ** (
                Decimal("1") / Decimal("12")
            )
        elif (
            account.compound_frequency == Frequency.ANNUALLY
            and retirement_months % 12 == 0
        ):
            current_savings *= Decimal("1") + account.annual_retirement_return

        # add to remaining months
        retirement_months += 1

        if retirement_months % 12 == 0:
            graph_labels.append(account.owner.retirement_age + retirement_months // 12)
            graph_savings_values.append(current_savings)

    if current_savings == Decimal("0"):
        last_year = graph_labels[-1] if graph_labels else account.owner.retirement_age
        next_year = last_year + 1
        graph_labels.append(next_year)
        graph_savings_values.append(Decimal("0"))
