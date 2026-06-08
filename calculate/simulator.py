from decimal import Decimal
from typing import Dict, Tuple, List
from utils.parameters import Person
from utils.globals import GlobalParameters, calculate_progressive_tax
from utils.enums import Frequency, MonthlyCompoundType, AccountType
from utils.accounts.base import Account, _adjust_for_inflation
from calculate.state_tax import get_state_tax_calculator


def calculate_aggregate_taxes(
    Y_ord_real: Decimal,
    Y_cap_real: Decimal,
    user: Person,
    config: GlobalParameters,
) -> Tuple[Decimal, Decimal]:
    """Calculates aggregate federal and state taxes for ordinary and capital gains income in real dollars.

    This function applies standard deductions exactly once for the individual or joint household,
    preventing double-counting when multiple accounts are drawn from. Long-term capital gains are stacked
    on top of the ordinary taxable income pool to correctly calculate progressive tax brackets.

    Args:
        Y_ord_real: Aggregated annual ordinary pre-tax income in today's (real) dollars.
        Y_cap_real: Aggregated annual capital gains income in today's (real) dollars.
        user: The Person owner containing filing status and state.
        config: The GlobalParameters configuration context for the tax brackets.

    Returns:
        A tuple of (ordinary_income_tax_real, capital_gains_tax_real).
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

    # Capital gains tax stacked on top of ordinary income: Tax(Ord + Cap) - Tax(Ord)
    total_fed_cap_tax = calculate_progressive_tax(
        taxable_ord_fed + taxable_cap_fed, fed_cap_brackets
    )
    base_fed_cap_tax = calculate_progressive_tax(taxable_ord_fed, fed_cap_brackets)
    fed_cap_tax = total_fed_cap_tax - base_fed_cap_tax

    # 4. State Capital Gains Tax
    state_calculator = get_state_tax_calculator(user.state_of_residence)
    state_cap_tax = state_calculator.calculate_capital_gains_tax(
        Y_cap_real, user, config, ordinary_income=Y_ord_real
    )

    cap_tax_real = fed_cap_tax + state_cap_tax

    return ord_tax_real, cap_tax_real


class RetirementSimulator:
    """Coordinates retirement and accumulation simulation phases across multiple accounts concurrently."""

    def __init__(
        self,
        user: Person,
        config: GlobalParameters,
    ) -> None:
        self.user = user
        self.config = config
        self.accounts = user.accounts

    def simulate(self) -> Dict[str, Tuple[List[int], List[Decimal]]]:
        """Runs the complete multi-account retirement simulation.

        Orchestrates both accumulation and retirement phases, ensuring taxes and compounding are
        coordinated across all accounts.

        Returns:
            A dictionary mapping account names to tuples of (labels/ages, savings_values).
        """
        account_labels, account_values, savings = self._reset_simulation_state()
        self._run_accumulation_phase(savings, account_labels, account_values)
        self._run_retirement_phase(savings, account_labels, account_values)

        return {
            name: (account_labels[name], account_values[name]) for name in self.accounts
        }

    def _reset_simulation_state(
        self,
    ) -> Tuple[Dict[str, List[int]], Dict[str, List[Decimal]], Dict[str, Decimal]]:
        """Initializes empty labels and values lists, and resets account current_savings and cost basis."""
        account_labels: Dict[str, List[int]] = {}
        account_values: Dict[str, List[Decimal]] = {}
        savings: Dict[str, Decimal] = {}

        for name, account in self.accounts.items():
            account_labels[name] = []
            account_values[name] = []
            account.current_savings = account.initial_savings
            savings[name] = account.initial_savings

            from utils.accounts.brokerage import BrokerageAccount

            if isinstance(account, BrokerageAccount):
                if hasattr(account, "initial_cost_basis"):
                    account.cost_basis = account.initial_cost_basis
                else:
                    account.initial_cost_basis = account.cost_basis

        return account_labels, account_values, savings

    def _run_accumulation_phase(
        self,
        savings: Dict[str, Decimal],
        account_labels: Dict[str, List[int]],
        account_values: Dict[str, List[Decimal]],
    ) -> None:
        """Simulates growth and contributions for each account independently up to retirement age."""
        for name, account in self.accounts.items():
            savings[name] = account.simulate_accumulation(
                savings[name], account_labels[name], account_values[name]
            )

    def _run_retirement_phase(
        self,
        savings: Dict[str, Decimal],
        account_labels: Dict[str, List[int]],
        account_values: Dict[str, List[Decimal]],
    ) -> None:
        """Simulates monthly withdrawals, coordinated taxation, and compounding until lifespan or depletion."""
        retirement_months = 0
        lifespan_months = (self.user.lifespan - self.user.retirement_age) * 12

        while retirement_months < lifespan_months:
            if all(savings[name] <= 0 for name in self.accounts):
                self._record_depletion_state(account_labels, account_values)
                break

            months_since_today = (
                self.user.retirement_age - self.user.current_age
            ) * 12 + retirement_months
            inflation_factor = _adjust_for_inflation(
                Decimal("1"), months_since_today, self.config
            )

            # 1. Target monthly net withdrawals and run solver to get required gross withdrawals
            W_capped, tax_allocated = self._calculate_monthly_pre_tax_withdrawals(
                savings, months_since_today, inflation_factor
            )

            # 2. Deduct finalized withdrawals and update cost basis
            for name, acc in self.accounts.items():
                savings[name] = savings[name] - W_capped[name]
                acc.post_withdraw_update(W_capped[name], savings[name])

            # 3. Compound remaining balances
            self._compound_savings_for_month(savings, retirement_months)

            retirement_months += 1

            # 4. Record yearly data points
            if retirement_months % 12 == 0:
                self._record_yearly_balances(
                    savings, account_labels, account_values, retirement_months
                )

        # Update final savings on the account models
        for name, acc in self.accounts.items():
            acc.current_savings = savings[name]

    def _get_drawdown_order(self) -> List[Tuple[str, Account]]:
        """Returns the accounts sorted by priority: Brokerage/Generic -> Traditional -> Roth/HSA."""

        def priority_key(item: Tuple[str, Account]) -> Tuple[int, str]:
            name, account = item
            if account.account_type == AccountType.GENERIC:
                return 1, name
            elif account.account_type == AccountType.TRADITIONAL:
                return 2, name
            else:  # ROTH and HSA
                return 3, name

        return sorted(self.accounts.items(), key=priority_key)

    def _solve_taxable_withdrawal(
        self,
        acc: Account,
        remaining_net: Decimal,
        account_savings: Decimal,
        inflation_factor: Decimal,
        total_trad_withdrawn: Decimal,
        total_cap_withdrawn: Decimal,
    ) -> Tuple[Decimal, Decimal]:
        """Calculates the pre-tax withdrawal and tax incurred for a taxable account using binary search."""
        # Determine the gain ratio for capital gains tax calculations (only for Brokerage)
        g_ratio = Decimal("0")
        if acc.account_type == AccountType.GENERIC:
            from utils.parameters import BrokerageAccount

            if isinstance(acc, BrokerageAccount) and account_savings > 0:
                g_ratio = max(
                    Decimal("0"),
                    (account_savings - acc.cost_basis) / account_savings,
                )

        # Helper to calculate marginal tax for a candidate withdrawal W
        def get_marginal_tax(W: Decimal) -> Decimal:
            if acc.account_type == AccountType.TRADITIONAL:
                new_trad = total_trad_withdrawn + W
                new_cap = total_cap_withdrawn
            else:  # AccountType.GENERIC
                new_trad = total_trad_withdrawn
                new_cap = total_cap_withdrawn + W * g_ratio

            # Calculate aggregate taxes at new totals
            ord_tax_real, cap_tax_real = calculate_aggregate_taxes(
                new_trad * 12 / inflation_factor,
                new_cap * 12 / inflation_factor,
                self.user,
                self.config,
            )
            total_tax_monthly = (ord_tax_real + cap_tax_real) * inflation_factor / 12

            # Calculate baseline taxes (before this account's withdrawal)
            base_ord_tax, base_cap_tax = calculate_aggregate_taxes(
                total_trad_withdrawn * 12 / inflation_factor,
                total_cap_withdrawn * 12 / inflation_factor,
                self.user,
                self.config,
            )
            base_tax_monthly = (base_ord_tax + base_cap_tax) * inflation_factor / 12

            return total_tax_monthly - base_tax_monthly

        # Boundary check: if the entire savings cannot cover remaining_net after tax, deplete the account
        max_tax = get_marginal_tax(account_savings)
        if account_savings - max_tax <= remaining_net:
            return account_savings, max_tax

        # Binary search for the exact pre-tax amount
        left = Decimal("0")
        right = account_savings
        best_W = account_savings
        best_tax = max_tax

        for _ in range(20):
            mid = (left + right) / Decimal("2")
            tax = get_marginal_tax(mid)
            net = mid - tax
            if abs(net - remaining_net) < Decimal("0.01"):
                return mid, tax
            elif net < remaining_net:
                left = mid
            else:
                right = mid

        best_W = (left + right) / Decimal("2")
        return best_W, get_marginal_tax(best_W)

    def _calculate_monthly_pre_tax_withdrawals(
        self,
        savings: Dict[str, Decimal],
        months_since_today: int,
        inflation_factor: Decimal,
    ) -> Tuple[Dict[str, Decimal], Dict[str, Decimal]]:
        """Calculates pre-tax withdrawals sequentially from each account in priority order.

        Draws from accounts one by one, solving for each account's pre-tax amount.
        """
        remaining_net = _adjust_for_inflation(
            self.user.annual_retirement_post_tax_expense / Decimal("12"),
            months_since_today,
            self.config,
        )

        W_capped = {name: Decimal("0") for name in self.accounts}
        tax_allocated = {name: Decimal("0") for name in self.accounts}

        # Running total of withdrawals in this month (for tax stacking)
        total_trad_withdrawn = Decimal("0")
        total_cap_withdrawn = Decimal("0")

        for name, acc in self._get_drawdown_order():
            if remaining_net <= 0:
                break
            if savings[name] <= 0:
                continue

            # 1. Non-taxable accounts (Roth, HSA, etc.) require no tax calculations
            if acc.account_type not in (AccountType.TRADITIONAL, AccountType.GENERIC):
                W = min(remaining_net, savings[name])
                W_capped[name] = W
                tax_allocated[name] = Decimal("0")
                remaining_net -= W
                continue

            # 2. Taxable accounts: solve for the pre-tax withdrawal and tax
            W, tax = self._solve_taxable_withdrawal(
                acc,
                remaining_net,
                savings[name],
                inflation_factor,
                total_trad_withdrawn,
                total_cap_withdrawn,
            )
            W_capped[name] = W
            tax_allocated[name] = tax
            if W < savings[name]:
                remaining_net = Decimal("0")
            else:
                remaining_net -= W - tax

            # Update monthly totals with the finalized withdrawals for tax stacking
            if acc.account_type == AccountType.TRADITIONAL:
                total_trad_withdrawn += W
            elif acc.account_type == AccountType.GENERIC:
                from utils.parameters import BrokerageAccount

                # Determine gain ratio for tax stacking
                g_ratio = Decimal("0")
                if isinstance(acc, BrokerageAccount) and savings[name] > 0:
                    g_ratio = max(
                        Decimal("0"),
                        (savings[name] - acc.cost_basis) / savings[name],
                    )
                total_cap_withdrawn += W * g_ratio

        return W_capped, tax_allocated

    def _compound_savings_for_month(
        self, savings: Dict[str, Decimal], retirement_months: int
    ) -> None:
        """Applies compounding returns to the remaining savings of each account."""
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

    def _record_depletion_state(
        self,
        account_labels: Dict[str, List[int]],
        account_values: Dict[str, List[Decimal]],
    ) -> None:
        """Appends zero balances for the depletion year to represent account bankruptcy."""
        last_year = (
            account_labels[next(iter(self.accounts))][-1]
            if account_labels[next(iter(self.accounts))]
            else self.user.retirement_age
        )
        next_year = last_year + 1
        for name in self.accounts:
            account_labels[name].append(next_year)
            account_values[name].append(Decimal("0"))

    def _record_yearly_balances(
        self,
        savings: Dict[str, Decimal],
        account_labels: Dict[str, List[int]],
        account_values: Dict[str, List[Decimal]],
        retirement_months: int,
    ) -> None:
        """Records the year-end account balances in the labels and values lists."""
        year_index = self.user.retirement_age + retirement_months // 12
        for name in self.accounts:
            account_labels[name].append(year_index)
            account_values[name].append(savings[name])
