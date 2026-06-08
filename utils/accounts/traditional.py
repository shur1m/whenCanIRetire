from __future__ import annotations

from typing import Optional, Union, TYPE_CHECKING
from decimal import Decimal
from utils.enums import Frequency, MonthlyCompoundType, AccountType
from utils.accounts.base import Account

if TYPE_CHECKING:
    from utils.parameters import Person


class TraditionalAccount(Account):
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
        account_type: AccountType = AccountType.TRADITIONAL,
        **kwargs,
    ) -> None:
        super().__init__(
            owner=owner,
            initial_savings=initial_savings,
            cost_basis=cost_basis,
            regular_investment_dollar=regular_investment_dollar,
            regular_investment_frequency=regular_investment_frequency,
            annual_investment_increase=annual_investment_increase,
            annual_investment_return=annual_investment_return,
            annual_retirement_return=annual_retirement_return,
            compound_frequency=compound_frequency,
            compound_type=compound_type,
            account_type=account_type,
        )
