from __future__ import annotations

from typing import Optional, Union, TYPE_CHECKING
from decimal import Decimal, ROUND_HALF_UP
from utils.enums import Frequency, MonthlyCompoundType, AccountType

if TYPE_CHECKING:
    from utils.parameters import Person
    from utils.globals import GlobalParameters


def to_decimal(val: Optional[Union[Decimal, float, int, str]]) -> Decimal:
    """Converts a value to a Decimal. Returns Decimal("0") if None."""
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _adjust_for_inflation(
    todays_dollars: Union[Decimal, float, int],
    months: int,
    config: GlobalParameters,
) -> Decimal:
    """Adjusts a dollar value for inflation compounded monthly over a number of months.

    Formula: todays_dollars * (1 + inflation_rate)**(months/12)
    """
    todays_dollars_dec = to_decimal(todays_dollars)
    inflation_rate_dec = config.inflation_rate
    inflation_multiplier = Decimal("1") + inflation_rate_dec
    inflation_per_month = inflation_multiplier ** (Decimal("1") / Decimal("12"))
    return todays_dollars_dec * (inflation_per_month**months)


class Account:
    """Base class representing a financial investment or retirement account.

    Serves as a polymorphic base class and uses the Factory pattern in `__new__`
    to dynamically return instances of subclasses (TraditionalAccount, RothAccount,
    HsaAccount, BrokerageAccount) based on the account_type parameter.
    """

    def __new__(cls, *args, **kwargs):
        """Dynamic factory method to instantiate the correct subclass based on account_type."""
        if cls is Account:
            account_type = kwargs.get("account_type")
            if account_type is None and len(args) >= 12:
                account_type = args[11]
            if account_type is None:
                account_type = AccountType.GENERIC

            from utils.accounts.traditional import TraditionalAccount
            from utils.accounts.roth import RothAccount
            from utils.accounts.hsa import HsaAccount
            from utils.accounts.brokerage import BrokerageAccount

            if account_type == AccountType.TRADITIONAL:
                return object.__new__(TraditionalAccount)
            elif account_type == AccountType.ROTH:
                return object.__new__(RothAccount)
            elif account_type == AccountType.HSA:
                return object.__new__(HsaAccount)
            else:
                return object.__new__(BrokerageAccount)
        return object.__new__(cls)

    def __init__(
        self,
        owner: Person,
        initial_savings: Union[Decimal, float, int] = 0,
        cost_basis: Optional[Union[Decimal, float, int]] = None,
        regular_investment_dollar: Union[Decimal, float, int] = 1666,
        regular_investment_frequency: Frequency = Frequency.MONTHLY,
        annual_investment_increase: Union[Decimal, float, int] = 0.0,
        annual_investment_return: Union[Decimal, float, int] = 0.07,
        annual_retirement_return: Union[Decimal, float, int] = 0.05,
        annual_retirement_post_tax_expense: Union[Decimal, float, int] = 72_000,
        compound_frequency: Frequency = Frequency.MONTHLY,
        compound_type: MonthlyCompoundType = MonthlyCompoundType.ROOT,
        account_type: AccountType = AccountType.GENERIC,
    ) -> None:
        """Initializes general parameters shared by all account types."""
        self.owner: Person = owner
        self.initial_savings: Decimal = to_decimal(initial_savings)
        self.current_savings: Decimal = self.initial_savings
        self.regular_investment_dollar: Decimal = to_decimal(regular_investment_dollar)
        self.regular_investment_frequency: Frequency = regular_investment_frequency
        self.annual_investment_increase: Decimal = to_decimal(
            annual_investment_increase
        )

        self.annual_investment_return: Decimal = to_decimal(annual_investment_return)
        self.annual_retirement_return: Decimal = to_decimal(annual_retirement_return)
        self.annual_retirement_post_tax_expense: Decimal = to_decimal(
            annual_retirement_post_tax_expense
        )
        self.compound_frequency: Frequency = compound_frequency
        self.compound_type: MonthlyCompoundType = compound_type
        self.account_type: AccountType = account_type

    def add_contribution(self, amount: Decimal) -> None:
        """Invoked during the accumulation phase to record a contribution.

        Overridden in BrokerageAccount to increase the cost basis.
        """

    def post_withdraw_update(
        self, withdrawal_pre_tax: Decimal, remaining_savings: Decimal
    ) -> None:
        """Invoked after a withdrawal is made to adjust account state.

        Overridden in BrokerageAccount to reduce the cost basis proportionally.
        """

    def get_pre_tax_withdrawal(
        self,
        post_tax_income: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> Decimal:
        """Calculates the pre-tax monthly withdrawal required to meet a post-tax target.

        Uses the Template Method pattern by invoking `calculate_withdrawal_tax`.
        Default behavior (Roth, HSA) has 0% tax, so pre-tax withdrawal equals post-tax target.
        """
        return post_tax_income

    def calculate_withdrawal_tax(
        self,
        pre_tax_annual_real: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
    ) -> Decimal:
        """Calculates and returns the annual real tax on a pre-tax withdrawal.

        Part of the Template Method pattern for binary search.
        Defaults to Decimal("0") (Roth and HSA). Overridden in Traditional and Brokerage.
        """
        return Decimal("0")

    def _binary_search_pre_tax_withdrawal(
        self,
        post_tax_income: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> Decimal:
        """Helper method to run a binary search to find the pre-tax monthly withdrawal.

        Solves for: pre_tax_income - tax_monthly(pre_tax_income) == post_tax_income.
        Calls `calculate_withdrawal_tax` polymorphically to compute the tax.
        """
        left = post_tax_income
        right = post_tax_income * Decimal("5")
        pre_tax_income = right

        while abs(right - left) > Decimal("0.01"):
            pre_tax_income = left + (right - left) / Decimal("2")
            pre_tax_annual = pre_tax_income * Decimal("12")
            pre_tax_annual_real = pre_tax_annual / inflation_factor

            tax_annual_real = self.calculate_withdrawal_tax(
                pre_tax_annual_real, current_savings, config
            )

            tax_annual = tax_annual_real * inflation_factor
            tax_monthly = tax_annual / Decimal("12")
            net_monthly = pre_tax_income - tax_monthly

            if net_monthly > post_tax_income:
                right = pre_tax_income
            else:
                left = pre_tax_income

        return pre_tax_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def withdraw(
        self,
        net_amount: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """Performs a withdrawal from the account for a target net amount.

        Updates account state and returns (withdrawal_pre_tax, remaining_savings).
        """
        pre_tax_amount = self.get_pre_tax_withdrawal(
            net_amount, current_savings, config, inflation_factor
        )
        if current_savings < pre_tax_amount:
            withdrawal_pre_tax = current_savings
            remaining_savings = Decimal("0")
        else:
            withdrawal_pre_tax = pre_tax_amount
            remaining_savings = current_savings - pre_tax_amount

        self.post_withdraw_update(withdrawal_pre_tax, remaining_savings)
        return withdrawal_pre_tax, remaining_savings

    def _compound_monthly(self, current_savings: Decimal) -> Decimal:
        """Helper to compound investment return monthly based on compound frequency/type."""
        if self.compound_frequency != Frequency.MONTHLY:
            return current_savings

        if self.compound_type == MonthlyCompoundType.DIVIDE:
            rate = self.annual_investment_return / Decimal("12")
            return current_savings * (Decimal("1") + rate)
        elif self.compound_type == MonthlyCompoundType.ROOT:
            rate_root = (Decimal("1") + self.annual_investment_return) ** (
                Decimal("1") / Decimal("12")
            )
            return current_savings * rate_root
        return current_savings

    def _get_monthly_contribution(self, year: int, month: int) -> Decimal:
        """Helper to compute the contribution for a given month, accounting for annual increase."""
        if self.regular_investment_frequency != Frequency.MONTHLY:
            return Decimal("0")

        increase_factor = (Decimal("1") + self.annual_investment_increase) ** (
            Decimal("1") / Decimal("12")
        )
        return self.regular_investment_dollar * (increase_factor ** (year * 12 + month))

    def _get_annual_contribution(self, year: int) -> Decimal:
        """Helper to compute the contribution for a given year, accounting for annual increase."""
        if self.regular_investment_frequency != Frequency.ANNUALLY:
            return Decimal("0")

        increase_factor = (Decimal("1") + self.annual_investment_increase) ** year
        return self.regular_investment_dollar * increase_factor

    def simulate_accumulation(
        self,
        current_savings: Decimal,
        graph_labels: list[int],
        graph_savings_values: list[Decimal],
    ) -> Decimal:
        """Simulates growth of the account during the accumulation (pre-retirement) phase.

        Appends yearly data points to graph_labels and graph_savings_values.
        """
        for year in range(self.owner.retirement_age - self.owner.current_age):
            # compounding yearly
            if self.compound_frequency == Frequency.ANNUALLY:
                current_savings *= Decimal("1") + self.annual_investment_return

            for month in range(12):
                current_savings = self._compound_monthly(current_savings)
                contribution = self._get_monthly_contribution(year, month)
                if contribution > 0:
                    current_savings += contribution
                    self.add_contribution(contribution)

            # yearly addition to investment account
            contribution = self._get_annual_contribution(year)
            if contribution > 0:
                current_savings += contribution
                self.add_contribution(contribution)

            graph_labels.append(self.owner.current_age + year)
            graph_savings_values.append(current_savings)

        self.current_savings = current_savings
        return current_savings

    def simulate_retirement(
        self,
        current_savings: Decimal,
        graph_labels: list[int],
        graph_savings_values: list[Decimal],
        config: GlobalParameters,
    ) -> None:
        """Simulates drawdown of the account during the retirement phase.

        Appends yearly data points to graph_labels and graph_savings_values.
        """
        retirement_months = 0
        post_tax_annual_expense = self.annual_retirement_post_tax_expense
        post_tax_monthly_withdrawal = post_tax_annual_expense / Decimal("12")

        while (
            current_savings > Decimal("0")
            and self.owner.retirement_age + retirement_months // 12
            < self.owner.lifespan
        ):
            months_since_today = (
                self.owner.retirement_age - self.owner.current_age
            ) * 12 + retirement_months

            inflated_post_tax_monthly = _adjust_for_inflation(
                post_tax_monthly_withdrawal,
                months_since_today,
                config,
            )

            inflation_factor = _adjust_for_inflation(
                Decimal("1"), months_since_today, config
            )

            withdrawal_pre_tax, remaining_savings = self.withdraw(
                inflated_post_tax_monthly,
                current_savings,
                config,
                inflation_factor,
            )

            current_savings = remaining_savings

            if self.compound_frequency == Frequency.MONTHLY:
                current_savings *= (Decimal("1") + self.annual_retirement_return) ** (
                    Decimal("1") / Decimal("12")
                )
            elif (
                self.compound_frequency == Frequency.ANNUALLY
                and retirement_months % 12 == 0
            ):
                current_savings *= Decimal("1") + self.annual_retirement_return

            retirement_months += 1

            if retirement_months % 12 == 0:
                graph_labels.append(self.owner.retirement_age + retirement_months // 12)
                graph_savings_values.append(current_savings)

        if current_savings == Decimal("0"):
            last_year = graph_labels[-1] if graph_labels else self.owner.retirement_age
            next_year = last_year + 1
            graph_labels.append(next_year)
            graph_savings_values.append(Decimal("0"))

        self.current_savings = current_savings

    def simulate(self, config: GlobalParameters) -> tuple[list[int], list[Decimal]]:
        """Orchestrates both accumulation and retirement simulation phases.

        Returns (graph_labels, graph_savings_values).
        """
        graph_labels: list[int] = []
        graph_savings_values: list[Decimal] = []
        self.current_savings = self.initial_savings

        savings_at_retirement = self.simulate_accumulation(
            self.current_savings, graph_labels, graph_savings_values
        )
        self.simulate_retirement(
            savings_at_retirement,
            graph_labels,
            graph_savings_values,
            config,
        )
        return graph_labels, graph_savings_values
