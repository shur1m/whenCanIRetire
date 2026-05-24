from typing import Union
from decimal import Decimal, ROUND_HALF_UP
from calculate.tax import calculate_annual_income_tax
from utils.parameters import Person, Account, to_decimal
from utils.enums import Frequency, MonthlyCompoundType, AccountType
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


def _calculate_pre_tax_income(
    post_tax_income: Union[Decimal, float, int],
    user: Person,
    config: GlobalParameters,
) -> Decimal:
    # binary search
    post_tax_income_dec = to_decimal(post_tax_income)
    left = post_tax_income_dec
    right = post_tax_income_dec * Decimal("5")
    pre_tax_income = right

    # stop once error is smaller than cent
    while abs(right - left) > Decimal("0.01"):
        pre_tax_income = left + (right - left) / Decimal("2")
        # create dummy person using the actual user's state and filing status
        dummy_person = Person(
            pre_tax_income=pre_tax_income,
            state_of_residence=user.state_of_residence,
            filing=user.filing,
        )
        if (
            pre_tax_income - calculate_annual_income_tax(dummy_person, config)
            > post_tax_income_dec
        ):
            right = pre_tax_income
        else:
            left = pre_tax_income

    return pre_tax_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
                current_savings += account.regular_investment_dollar * (
                    (
                        (Decimal("1") + account.annual_investment_increase)
                        ** (Decimal("1") / Decimal("12"))
                    )
                    ** (year * 12 + month)
                )

        # yearly addition to investment account
        if account.regular_investment_frequency == Frequency.ANNUALLY:
            current_savings += account.regular_investment_dollar * (
                (Decimal("1") + account.annual_investment_increase) ** year
            )

        graph_labels.append(account.owner.current_age + year)
        graph_savings_values.append(current_savings)

    return current_savings


def _simulate_retirement(
    account: Account,
    current_savings: Decimal,
    graph_labels: list[int],
    graph_savings_values: list[Decimal],
    config: GlobalParameters,
) -> None:
    # retirement phase (no social security)
    retirement_months = 0
    annual_retirement_withdrawal = account.annual_retirement_post_tax_expense

    # binary search pre tax expense given post tax expense for Generic and Traditional account withdrawals, Roth/HSA withdrawals are not adjusted
    if (
        account.account_type == AccountType.GENERIC
        or account.account_type == AccountType.TRADITIONAL
    ):
        annual_retirement_withdrawal = _calculate_pre_tax_income(
            annual_retirement_withdrawal, account.owner, config
        )

    while (
        current_savings >= annual_retirement_withdrawal / Decimal("12")
        and account.owner.retirement_age + retirement_months // 12
        < account.owner.lifespan
    ):

        # each month, subtract monthly "paycheck" and compound
        months_since_today = (
            account.owner.retirement_age - account.owner.current_age
        ) * 12 + retirement_months
        current_savings -= _adjust_for_inflation(
            annual_retirement_withdrawal / Decimal("12"),
            months_since_today,
            config,
        )

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

    if current_savings < Decimal("0"):
        graph_labels.append(account.owner.retirement_age + retirement_months // 12 + 1)
        graph_savings_values.append(Decimal("0"))
