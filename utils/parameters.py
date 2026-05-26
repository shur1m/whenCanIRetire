from __future__ import annotations

from typing import Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from utils.enums import Filing, Frequency, MonthlyCompoundType, AccountType, State
from utils.globals import GlobalParameters


def to_decimal(val: Optional[Union[Decimal, float, int, str]]) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


class Account:
    def __new__(cls, *args, **kwargs):
        if cls is Account:
            account_type = kwargs.get("account_type")
            if account_type is None and len(args) >= 12:
                account_type = args[11]
            if account_type is None:
                account_type = AccountType.GENERIC

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

        self.owner: Person = owner
        self.initial_savings: Decimal = to_decimal(initial_savings)
        self.current_savings: Decimal = self.initial_savings
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

    def add_contribution(self, amount: Decimal) -> None:
        pass

    def post_withdraw_update(
        self, withdrawal_pre_tax: Decimal, remaining_savings: Decimal
    ) -> None:
        pass

    def get_pre_tax_withdrawal(
        self,
        post_tax_income: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> Decimal:
        return post_tax_income

    def withdraw(
        self,
        net_amount: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> tuple[Decimal, Decimal]:
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
        if self.regular_investment_frequency != Frequency.MONTHLY:
            return Decimal("0")

        increase_factor = (Decimal("1") + self.annual_investment_increase) ** (
            Decimal("1") / Decimal("12")
        )
        return self.regular_investment_dollar * (increase_factor ** (year * 12 + month))

    def _get_annual_contribution(self, year: int) -> Decimal:
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
        from calculate.retirement import _adjust_for_inflation

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
        annual_retirement_post_tax_expense: Union[Decimal, float, int] = 72_000,
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
            annual_retirement_post_tax_expense=annual_retirement_post_tax_expense,
            compound_frequency=compound_frequency,
            compound_type=compound_type,
            account_type=account_type,
        )

    def get_pre_tax_withdrawal(
        self,
        post_tax_income: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> Decimal:
        from calculate.retirement import calculate_retirement_withdrawal_tax

        left = post_tax_income
        right = post_tax_income * Decimal("5")
        pre_tax_income = right

        while abs(right - left) > Decimal("0.01"):
            pre_tax_income = left + (right - left) / Decimal("2")
            pre_tax_annual = pre_tax_income * Decimal("12")
            pre_tax_annual_real = pre_tax_annual / inflation_factor

            tax_annual_real = calculate_retirement_withdrawal_tax(
                pre_tax_annual_real, self, config, is_capital_gains=False
            )

            tax_annual = tax_annual_real * inflation_factor
            tax_monthly = tax_annual / Decimal("12")
            net_monthly = pre_tax_income - tax_monthly

            if net_monthly > post_tax_income:
                right = pre_tax_income
            else:
                left = pre_tax_income

        return pre_tax_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class RothAccount(Account):
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
        account_type: AccountType = AccountType.ROTH,
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


class HsaAccount(Account):
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
        account_type: AccountType = AccountType.HSA,
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

    def get_pre_tax_withdrawal(
        self,
        post_tax_income: Decimal,
        current_savings: Decimal,
        config: GlobalParameters,
        inflation_factor: Decimal,
    ) -> Decimal:
        from calculate.retirement import calculate_retirement_withdrawal_tax

        left = post_tax_income
        right = post_tax_income * Decimal("5")
        pre_tax_income = right

        while abs(right - left) > Decimal("0.01"):
            pre_tax_income = left + (right - left) / Decimal("2")
            pre_tax_annual = pre_tax_income * Decimal("12")
            pre_tax_annual_real = pre_tax_annual / inflation_factor

            gain_ratio = Decimal("0")
            if current_savings > 0:
                gain_ratio = max(
                    Decimal("0"),
                    (current_savings - self.cost_basis) / current_savings,
                )
            gains_annual_real = pre_tax_annual_real * gain_ratio
            tax_annual_real = calculate_retirement_withdrawal_tax(
                gains_annual_real, self, config, is_capital_gains=True
            )

            tax_annual = tax_annual_real * inflation_factor
            tax_monthly = tax_annual / Decimal("12")
            net_monthly = pre_tax_income - tax_monthly

            if net_monthly > post_tax_income:
                right = pre_tax_income
            else:
                left = pre_tax_income

        return pre_tax_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
