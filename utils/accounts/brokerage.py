from __future__ import annotations

from typing import Optional, Union, TYPE_CHECKING
from decimal import Decimal
from utils.enums import Frequency, MonthlyCompoundType, AccountType
from utils.accounts.base import Account, to_decimal

if TYPE_CHECKING:
    from utils.parameters import Person
    from utils.globals import GlobalParameters


class BrokerageAccount(Account):
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
            annual_retirement_post_tax_expense=annual_retirement_post_tax_expense,
            compound_frequency=compound_frequency,
            compound_type=compound_type,
            account_type=account_type,
        )
        self.cost_basis: Decimal = (
            to_decimal(cost_basis) if cost_basis is not None else Decimal("0")
        )
        self.initial_cost_basis: Decimal = self.cost_basis

    def add_contribution(self, amount: Decimal) -> None:
        self.cost_basis += amount

    def post_withdraw_update(
        self, withdrawal_pre_tax: Decimal, remaining_savings: Decimal
    ) -> None:
        total_savings_before_withdrawal = remaining_savings + withdrawal_pre_tax
        if total_savings_before_withdrawal > 0:
            cost_basis_withdrawn = self.cost_basis * (
                withdrawal_pre_tax / total_savings_before_withdrawal
            )
            self.cost_basis = max(Decimal("0"), self.cost_basis - cost_basis_withdrawn)
        else:
            self.cost_basis = Decimal("0")

    def calculate_withdrawal_tax(
        self,
        pre_tax_annual_real: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
    ) -> Decimal:
        from calculate.retirement import calculate_retirement_withdrawal_tax

        gain_ratio = Decimal("0")
        if current_savings > 0:
            gain_ratio = max(
                Decimal("0"),
                (current_savings - self.cost_basis) / current_savings,
            )
        gains_annual_real = pre_tax_annual_real * gain_ratio
        return calculate_retirement_withdrawal_tax(
            gains_annual_real, self, config, is_capital_gains=True
        )

    def get_pre_tax_withdrawal(
        self,
        post_tax_income: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> Decimal:
        return self._binary_search_pre_tax_withdrawal(
            post_tax_income, current_savings, config, inflation_factor
        )
