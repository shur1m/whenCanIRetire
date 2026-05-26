from decimal import Decimal
from typing import Dict, Tuple, List, Optional
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax
from utils.enums import Frequency, MonthlyCompoundType, AccountType, State
from utils.accounts.base import Account, _adjust_for_inflation


def calculate_aggregate_taxes(
    Y_ord_real: Decimal, Y_cap_real: Decimal, user: Person, config: GlobalParameters
) -> Tuple[Decimal, Decimal]:
    """Calculates aggregate federal and state taxes for ordinary and capital gains income.

    Applying the standard deduction exactly once per person/household and stacking capital gains.
    """
    # 1. Federal Ordinary Tax
    fed_deduction = config.get_fed_tax_deduction(user.filing)
    taxable_ord_fed = max(Decimal("0"), Y_ord_real - fed_deduction)
    fed_ord_brackets = config.get_fed_tax_brackets(user.filing)
    fed_ord_tax = calculate_progressive_tax(taxable_ord_fed, fed_ord_brackets)

    # 2. State Ordinary Tax
    state_deduction = (
        config.get_state_tax_deduction(user.state_of_residence, user.filing)
        if user.state_of_residence
        else Decimal("0")
    )
    taxable_ord_state = max(Decimal("0"), Y_ord_real - state_deduction)
    state_ord_brackets = (
        config.get_state_tax_brackets(user.state_of_residence, user.filing)
        if user.state_of_residence
        else []
    )
    state_ord_tax = (
        calculate_progressive_tax(taxable_ord_state, state_ord_brackets)
        if user.state_of_residence
        else Decimal("0")
    )
    if user.state_of_residence:
        # California surcharges
        state_ord_tax += config.calculate_state_surcharges(
            user.state_of_residence, "ordinary", taxable_ord_state
        )

    ord_tax_real = fed_ord_tax + state_ord_tax

    # 3. Federal Capital Gains Tax
    unused_deduction = max(Decimal("0"), fed_deduction - Y_ord_real)
    taxable_cap_fed = max(Decimal("0"), Y_cap_real - unused_deduction)
    fed_cap_brackets = config.get_fed_capital_gains_brackets(user.filing)

    # Capital gains tax stacked on top of ordinary income
    total_fed_cap_tax = calculate_progressive_tax(
        taxable_ord_fed + taxable_cap_fed, fed_cap_brackets
    )
    base_fed_cap_tax = calculate_progressive_tax(taxable_ord_fed, fed_cap_brackets)
    fed_cap_tax = total_fed_cap_tax - base_fed_cap_tax

    # 4. State Capital Gains Tax
    if user.state_of_residence == State.CALIFORNIA:
        # Stacked CA tax: CA_tax(ord + cap) - CA_tax(ord)
        taxable_total_state = max(
            Decimal("0"), (Y_ord_real + Y_cap_real) - state_deduction
        )
        state_total_tax = calculate_progressive_tax(
            taxable_total_state, state_ord_brackets
        )
        state_total_tax += config.calculate_state_surcharges(
            user.state_of_residence, "ordinary", taxable_total_state
        )
        state_cap_tax = state_total_tax - state_ord_tax
    else:
        state_cap_tax = Decimal("0")

    cap_tax_real = fed_cap_tax + state_cap_tax

    return ord_tax_real, cap_tax_real


class RetirementSimulator:
    def __init__(
        self,
        user: Person,
        config: GlobalParameters,
        accounts: Optional[Dict[str, Account]] = None,
    ) -> None:
        self.user = user
        self.config = config
        self.accounts = accounts if accounts is not None else user.accounts

    def simulate(self) -> Dict[str, Tuple[List[int], List[Decimal]]]:
        account_labels: Dict[str, List[int]] = {}
        account_values: Dict[str, List[Decimal]] = {}
        savings: Dict[str, Decimal] = {}

        # Reset savings & cost basis
        for name, account in self.accounts.items():
            account_labels[name] = []
            account_values[name] = []
            account.current_savings = account.initial_savings
            from utils.accounts.brokerage import BrokerageAccount

            if isinstance(account, BrokerageAccount):
                if hasattr(account, "initial_cost_basis"):
                    account.cost_basis = account.initial_cost_basis
                else:
                    account.initial_cost_basis = account.cost_basis

        # 1. Accumulation Phase
        for name, account in self.accounts.items():
            savings[name] = account.simulate_accumulation(
                account.current_savings, account_labels[name], account_values[name]
            )

        # 2. Coordinated Retirement Phase
        retirement_months = 0
        lifespan_months = (self.user.lifespan - self.user.retirement_age) * 12

        while retirement_months < lifespan_months:
            # Check if all accounts are empty
            if all(savings[name] <= 0 for name in self.accounts):
                # Depletion year labels
                last_year = (
                    account_labels[next(iter(self.accounts))][-1]
                    if account_labels[next(iter(self.accounts))]
                    else self.user.retirement_age
                )
                next_year = last_year + 1
                for name in self.accounts:
                    account_labels[name].append(next_year)
                    account_values[name].append(Decimal("0"))
                break

            months_since_today = (
                self.user.retirement_age - self.user.current_age
            ) * 12 + retirement_months
            inflation_factor = _adjust_for_inflation(
                Decimal("1"), months_since_today, self.config
            )

            # Target post-tax monthly withdrawal for each account
            inflated_post_tax = {}
            for name, account in self.accounts.items():
                post_tax_target = account.annual_retirement_post_tax_expense / Decimal(
                    "12"
                )
                inflated_post_tax[name] = _adjust_for_inflation(
                    post_tax_target, months_since_today, self.config
                )

            # Fixed-point iteration to find pre-tax withdrawals
            W_pre = {name: val for name, val in inflated_post_tax.items()}
            W_capped = {name: Decimal("0") for name in self.accounts}
            tax_allocated = {name: Decimal("0") for name in self.accounts}

            for _ in range(20):
                # Cap withdrawals by current savings
                for name in self.accounts:
                    W_capped[name] = min(W_pre[name], savings[name])

                # Compute aggregate pre-tax ordinary real income
                total_trad_withdrawal = sum(
                    W_capped[name]
                    for name, acc in self.accounts.items()
                    if acc.account_type == AccountType.TRADITIONAL
                )
                Y_ord_real = total_trad_withdrawal * 12 / inflation_factor

                # Compute aggregate pre-tax capital gains real income
                total_brokerage_cap_gains = Decimal("0")
                gain_ratio = {}
                for name, acc in self.accounts.items():
                    if acc.account_type == AccountType.GENERIC:
                        from utils.parameters import BrokerageAccount

                        if isinstance(acc, BrokerageAccount) and savings[name] > 0:
                            g_ratio = max(
                                Decimal("0"),
                                (savings[name] - acc.cost_basis) / savings[name],
                            )
                        else:
                            g_ratio = Decimal("0")
                        gain_ratio[name] = g_ratio
                        total_brokerage_cap_gains += W_capped[name] * g_ratio

                Y_cap_real = total_brokerage_cap_gains * 12 / inflation_factor

                # Calculate aggregate taxes
                ord_tax_real, cap_tax_real = calculate_aggregate_taxes(
                    Y_ord_real, Y_cap_real, self.user, self.config
                )

                ord_tax_monthly = ord_tax_real * inflation_factor / 12
                cap_tax_monthly = cap_tax_real * inflation_factor / 12

                # Allocate taxes
                for name, acc in self.accounts.items():
                    if acc.account_type == AccountType.TRADITIONAL:
                        if total_trad_withdrawal > 0:
                            tax_allocated[name] = ord_tax_monthly * (
                                W_capped[name] / total_trad_withdrawal
                            )
                        else:
                            tax_allocated[name] = Decimal("0")
                    elif acc.account_type == AccountType.GENERIC:
                        if total_brokerage_cap_gains > 0:
                            tax_allocated[name] = cap_tax_monthly * (
                                (W_capped[name] * gain_ratio[name])
                                / total_brokerage_cap_gains
                            )
                        else:
                            tax_allocated[name] = Decimal("0")
                    else:
                        tax_allocated[name] = Decimal("0")

                # Update W_pre
                diff = Decimal("0")
                for name in self.accounts:
                    if W_pre[name] <= savings[name]:
                        new_val = inflated_post_tax[name] + tax_allocated[name]
                    else:
                        new_val = savings[name]
                    diff += abs(W_pre[name] - new_val)
                    W_pre[name] = new_val

                if diff < Decimal("0.01"):
                    break

            # Deduct capped withdrawals and update states
            for name, acc in self.accounts.items():
                savings[name] = savings[name] - W_capped[name]
                acc.post_withdraw_update(W_capped[name], savings[name])

            # Compound remaining savings
            for name, acc in self.accounts.items():
                if acc.compound_frequency == Frequency.MONTHLY:
                    if acc.compound_type == MonthlyCompoundType.DIVIDE:
                        rate = acc.annual_retirement_return / Decimal("12")
                        savings[name] *= Decimal("1") + rate
                    elif acc.compound_type == MonthlyCompoundType.ROOT:
                        rate_root = (Decimal("1") + acc.annual_retirement_return) ** (
                            Decimal("1") / Decimal("12")
                        )
                        savings[name] *= rate_root
                elif (
                    acc.compound_frequency == Frequency.ANNUALLY
                    and (retirement_months + 1) % 12 == 0
                ):
                    savings[name] *= Decimal("1") + acc.annual_retirement_return

            retirement_months += 1

            # Append year-end data points
            if retirement_months % 12 == 0:
                year_index = self.user.retirement_age + retirement_months // 12
                for name in self.accounts:
                    account_labels[name].append(year_index)
                    account_values[name].append(savings[name])

        # Save final savings
        for name, acc in self.accounts.items():
            acc.current_savings = savings[name]

        return {
            name: (account_labels[name], account_values[name]) for name in self.accounts
        }
