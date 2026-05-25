from __future__ import annotations

from typing import Optional, Union
from decimal import Decimal
from utils.enums import Filing, Frequency, MonthlyCompoundType, AccountType, State


def to_decimal(val: Optional[Union[Decimal, float, int, str]]) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


class Account:
    def __init__(
        self,
        owner: Person,
        initial_savings: Union[Decimal, float, int] = 0,
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

        self.owner: Person = owner
        self.initial_savings: Decimal = to_decimal(initial_savings)
        self.cost_basis: Decimal = self.initial_savings
        self.regular_investment_dollar: Decimal = to_decimal(regular_investment_dollar)
        self.regular_investment_frequency: Frequency = regular_investment_frequency
        self.annual_investment_increase: Decimal = to_decimal(
            annual_investment_increase  # percentage, how much you will contribute more next year
        )

        self.annual_investment_return: Decimal = to_decimal(annual_investment_return)
        self.annual_retirement_return: Decimal = to_decimal(annual_retirement_return)
        self.annual_retirement_post_tax_expense: Decimal = to_decimal(
            annual_retirement_post_tax_expense
        )
        self.compound_frequency: Frequency = compound_frequency
        self.compound_type: MonthlyCompoundType = compound_type
        self.account_type: AccountType = account_type


class Person:
    def __init__(
        self,
        current_age: int = 22,
        retirement_age: int = 65,
        lifespan: int = 120,
        pre_tax_income: Union[Decimal, float, int] = 115_000,  # annual value
        additional_income_tax_deductions: Union[
            Decimal, float, int
        ] = 0,  # subtracted from taxable income (income tax)
        accumulation_phase_expenses: Optional[
            dict[str, Decimal]
        ] = None,  # annual values
        state_of_residence: Optional[State] = None,
        filing: Filing = Filing.INDIVIDUAL,
    ) -> None:

        self.current_age: int = current_age
        self.retirement_age: int = retirement_age
        self.lifespan: int = lifespan
        self.pre_tax_income: Decimal = to_decimal(pre_tax_income)
        self.additional_income_tax_deductions: Decimal = to_decimal(
            additional_income_tax_deductions
        )
        self.accumulation_phase_expenses: dict[str, Decimal] = (
            dict()
            if accumulation_phase_expenses is None
            else {k: to_decimal(v) for k, v in accumulation_phase_expenses.items()}
        )
        self.state_of_residence: Optional[State] = state_of_residence
        self.filing: Filing = filing
        self.accounts: dict[str, Account] = dict()

    def add_account(self, account: Account, account_name: Optional[str] = None) -> None:
        if account.owner is not self:
            raise ValueError("Account owner must be the Person adding the account")

        if account_name is None:
            account_name = self._generate_account_name()

        if account_name in self.accounts:
            raise Exception("account names must be unique")

        self.accounts[account_name] = account

    def create_account(
        self, account_name: Optional[str] = None, **account_kwargs
    ) -> Account:
        account = Account(owner=self, **account_kwargs)
        self.add_account(account, account_name)
        return account

    def add_accounts(self, accounts: dict[str, Account]) -> None:
        for account_name, account in accounts.items():
            self.add_account(account, account_name)

    def add_accumulation_expense(
        self, name: str, expense: Union[Decimal, float, int], frequency: Frequency
    ) -> None:
        expense_decimal = to_decimal(expense)
        if frequency == Frequency.MONTHLY:
            self.accumulation_phase_expenses[name] = expense_decimal * 12
        elif frequency == Frequency.ANNUALLY:
            self.accumulation_phase_expenses[name] = expense_decimal

    @property
    def income_tax_deductions(self) -> Decimal:
        """Returns total income tax deductions (additional base deductions + retirement contributions)"""
        total = self.additional_income_tax_deductions
        for account in self.accounts.values():
            if account.account_type in (AccountType.TRADITIONAL, AccountType.HSA):
                if account.regular_investment_frequency == Frequency.MONTHLY:
                    total += account.regular_investment_dollar * 12
                elif account.regular_investment_frequency == Frequency.ANNUALLY:
                    total += account.regular_investment_dollar
        return total

    def get_reduced_income(self) -> Decimal:
        """returns income after subtracting 401(k) and HSA deductions"""
        return self.pre_tax_income - self.income_tax_deductions

    def get_fica_taxable_income(self) -> Decimal:
        """returns income that is subject to FICA (medicare/social security taxes)"""
        total_hsa_contribution = to_decimal(0)
        for _, account in self.accounts.items():
            if account.account_type == AccountType.HSA:
                if account.regular_investment_frequency == Frequency.ANNUALLY:
                    total_hsa_contribution += account.regular_investment_dollar

                if account.regular_investment_frequency == Frequency.MONTHLY:
                    total_hsa_contribution += account.regular_investment_dollar * 12

        return (
            self.pre_tax_income - total_hsa_contribution
        )  # todo calculate this by subtracting HSA contributions and change how FICA taxes are calculated pre_tax_income -> fica taxable

    def _generate_account_name(self) -> str:
        return "account_" + str(len(self.accounts))
