from typing import Optional
from utils.enums import Filing, Frequency, MonthlyCompoundType, AccountType, State

class Account:
    def __init__(self,
                 initial_savings: int = 0,
                 regular_investment_dollar: int = 1666,
                 regular_investment_frequency: Frequency = Frequency.MONTHLY,
                 annual_investment_increase: int = 0,
                 annual_investment_return: int = 0.07,
                 annual_retirement_return: int = 0.05,
                 annual_retirement_post_tax_expense: int = 72_000,
                 compound_frequency: Frequency = Frequency.MONTHLY,
                 compound_type: MonthlyCompoundType= MonthlyCompoundType.ROOT,
                 account_type: AccountType = AccountType.GENERIC) -> None:
        
        self.owner: Optional[Person] = None
        self.initial_savings: int = initial_savings
        self.regular_investment_dollar: int = regular_investment_dollar
        self.regular_investment_frequency: Frequency = regular_investment_frequency
        self.annual_investment_increase: int = annual_investment_increase # percentage, how much you will contribute more next year
        self.annual_investment_return: int = annual_investment_return
        self.annual_retirement_return = annual_retirement_return
        self.annual_retirement_post_tax_expense = annual_retirement_post_tax_expense
        self.compound_frequency: Frequency = compound_frequency
        self.compound_type: MonthlyCompoundType = compound_type
        self.account_type = account_type

class Person:
    def __init__(self,
                 current_age: int = 22,
                 retirement_age: int= 65,
                 lifespan: int = 120,
                 pre_tax_income: int = 115_000, # annual value
                 additional_income_tax_deductions: int = 0, # subtracted from taxable income (income tax)
                 accumulation_phase_expenses: Optional[dict[str, int]] = None, # annual values
                 state_of_residence: Optional[State] = None,
                 filing: Filing = Filing.INDIVIDUAL) -> None:
        
        self.current_age: int = current_age
        self.retirement_age: int = retirement_age
        self.lifespan = lifespan
        self.pre_tax_income = pre_tax_income
        self.income_tax_deductions = additional_income_tax_deductions
        self.accumulation_phase_expenses = dict() if accumulation_phase_expenses is None else accumulation_phase_expenses
        self.state_of_residence = state_of_residence
        self.filing = filing
        self.accounts: dict[str, Account] = dict()
    
    def add_account(self, account: Account, account_name: Optional[str] = None) -> None:
        if account_name is None:
            account_name = self._generate_account_name()

        if account_name in self.accounts:
            raise Exception("account names must be unique")
        
        self.accounts[account_name] = account
        account.owner = self

        if account.account_type == AccountType.TRADITIONAL or account.account_type == AccountType.HSA:
            if account.regular_investment_frequency == Frequency.MONTHLY:
                self.income_tax_deductions += account.regular_investment_dollar * 12
            elif account.regular_investment_frequency == Frequency.ANNUALLY:
                self.income_tax_deductions += account.regular_investment_dollar

    def add_accounts(self, accounts: dict[str, Account]) -> None:
        for account_name, account in accounts.items:
            self.accounts[account_name] = account

    def add_accumulation_expense(self, name: str, expense: int, frequency: Frequency = Frequency.MONTHLY):
        if frequency == Frequency.MONTHLY:
            self.accumulation_phase_expenses[name] = expense * 12
        elif frequency == Frequency.ANNUALLY:
            self.accumulation_phase_expenses[name] = expense

    def get_reduced_income(self) -> int:
        '''returns income after subtracting 401(k) and HSA deductions'''
        return self.pre_tax_income - self.income_tax_deductions
    
    def get_fica_taxable_income(self) -> int:
        '''returns income that is subject to FICA (medicare/social security taxes)'''
        total_hsa_contribution = 0
        for _, account in self.accounts.items():
            if account.account_type == AccountType.HSA:
                if account.regular_investment_frequency == Frequency.ANNUALLY:
                    total_hsa_contribution += account.regular_investment_dollar

                if account.regular_investment_frequency == Frequency.MONTHLY:
                    total_hsa_contribution += account.regular_investment_dollar * 12

        return self.pre_tax_income - total_hsa_contribution  # todo calculate this by subtracting HSA contributions and change how FICA taxes are calculated pre_tax_income -> fica taxable
    
    def _generate_account_name(self) -> str:
        return 'account_' + str(len(self.accounts))