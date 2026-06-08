from __future__ import annotations

from typing import Optional, Union, TYPE_CHECKING
from decimal import Decimal
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

    @classmethod
    def create(cls, *args, **kwargs) -> Account:
        """Dynamic factory method to instantiate the correct subclass based on account_type."""
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
            return TraditionalAccount(*args, **kwargs)
        elif account_type == AccountType.ROTH:
            return RothAccount(*args, **kwargs)
        elif account_type == AccountType.HSA:
            return HsaAccount(*args, **kwargs)
        else:
            return BrokerageAccount(*args, **kwargs)

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

            # compounding yearly
            if self.compound_frequency == Frequency.ANNUALLY:
                current_savings *= Decimal("1") + self.annual_investment_return

            graph_labels.append(self.owner.current_age + year)
            graph_savings_values.append(current_savings)

        self.current_savings = current_savings
        return current_savings
