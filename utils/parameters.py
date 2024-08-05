from utils.enums import Frequency, MonthlyCompoundType

class Person:
    def __init__(self, current_age: int = 22,
                 retirement_age: int= 65) -> None:
        self.current_age: int = current_age
        self.retirement_age: int = retirement_age

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
                 compound_type: MonthlyCompoundType= MonthlyCompoundType.ROOT) -> None:
        self.initial_savings: int = initial_savings
        self.regular_investment_dollar: int = regular_investment_dollar
        self.regular_investment_frequency: Frequency = regular_investment_frequency
        self.annual_investment_increase: int = annual_investment_increase # percentage, how much you will contribute more next year
        self.annual_investment_return: int = annual_investment_return
        self.annual_retirement_return = annual_retirement_return
        self.annual_retirement_expense = annual_retirement_expense
        self.compound_frequency: Frequency = compound_frequency
        self.compound_type: MonthlyCompoundType = compound_type