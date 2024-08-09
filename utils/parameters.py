from typing import Optional
from utils.enums import Filing, Frequency, MonthlyCompoundType, AccountType

class Account:
    def __init__(self,
                 initial_savings: int = 0,
                 regular_investment_dollar: int = 1666,
                 regular_investment_frequency: Frequency = Frequency.MONTHLY,
                 annual_investment_increase: int = 0,
                 annual_investment_return: int = 0.07,
                 annual_retirement_return: int = 0.05,
                 annual_retirement_expense: int = 72_000,
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
        self.annual_retirement_expense = annual_retirement_expense
        self.compound_frequency: Frequency = compound_frequency
        self.compound_type: MonthlyCompoundType = compound_type
        self.account_type = account_type

class Person:
    def __init__(self,
                 current_age: int = 22,
                 retirement_age: int= 65,
                 lifespan: int = 120,
                 pre_tax_income: int = 115_000,
                 additional_tax_deductions: int = 0,
                 filing: Filing = Filing.INDIVIDUAL) -> None:
        
        self.current_age: int = current_age
        self.retirement_age: int = retirement_age
        self.lifespan = lifespan
        self.pre_tax_income = pre_tax_income
        self.tax_deductions = additional_tax_deductions
        self.filing = filing
        self.accounts: dict[str, Account] = dict()
    
    def add_account(self, account: Account, account_name: Optional[str] = None) -> None:
        if account_name is None:
            account_name = self._generate_account_name()
        self.accounts[account_name] = account
        account.owner = self

        if account.account_type == AccountType.TRADITIONAL:
            if account.regular_investment_frequency == Frequency.MONTHLY:
                self.tax_deductions += account.regular_investment_dollar * 12
            elif account.regular_investment_frequency == Frequency.ANNUALLY:
                self.tax_deductions += account.regular_investment_dollar

    def add_accounts(self, accounts: dict[str, Account]) -> None:
        for account_name, account in accounts.items:
            self.accounts[account_name] = account

    def get_taxable_income(self) -> int:
        return self.pre_tax_income - self.tax_deductions
    
    def _generate_account_name(self) -> str:
        return 'account_' + str(len(self.accounts))