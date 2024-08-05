from utils.calc import adjust_for_inflation
from utils.enums import Frequency, MonthlyCompoundType
from utils.parameters import Account, Person
import math



inflation_rate: int = 0.03
user = Person(retirement_age=65)
someAccount = Account(annual_investment_increase=0.02, compound_frequency=Frequency.ANNUALLY)
graph_labels = []
graph_savings_values = []

current_savings = someAccount.initial_savings

# accumulation phase
for year in range(user.retirement_age - user.current_age):
    #compounding yearly 
    if someAccount.compound_frequency == Frequency.ANNUALLY:
        current_savings *= (1+someAccount.annual_investment_return)

    for month in range(12):
        # compounding monthly
        if someAccount.compound_frequency == Frequency.MONTHLY:
            if someAccount.compound_type == MonthlyCompoundType.DIVIDE:
                current_savings *= 1 + someAccount.annual_investment_return/12
            elif someAccount.compound_type == MonthlyCompoundType.ROOT:
                current_savings *= math.pow(1+ someAccount.annual_investment_return, 1/12)

        # monthly addition to investment account
        if someAccount.regular_investment_frequency == Frequency.MONTHLY:
            current_savings += someAccount.regular_investment_dollar * math.pow(math.pow(1 + someAccount.annual_investment_increase, 1/12), year*12+month)


    # yearly addition to investment account
    if someAccount.regular_investment_frequency == Frequency.ANNUALLY:
        current_savings += someAccount.regular_investment_dollar * math.pow(1 + someAccount.annual_investment_increase, year)

    #! for each data point, we need a label for that year
    graph_labels.append(user.current_age + year)
    graph_savings_values.append(current_savings)

print(current_savings)

# retirement phase (no social security)
retirement_months = 0
while current_savings >= someAccount.annual_retirement_expense/12:

    # each month, subtract monthly "paycheck" and compound
    months_since_today = (user.retirement_age - user.current_age) * 12 + retirement_months
    current_savings -= adjust_for_inflation(someAccount.annual_retirement_expense/12, months_since_today, inflation_rate)
    if someAccount.compound_frequency == Frequency.MONTHLY:
        current_savings *= math.pow(1 + someAccount.annual_retirement_return, 1/12)
    elif someAccount.compound_frequency == Frequency.ANNUALLY and retirement_months % 12 == 0:
        current_savings *= 1 + someAccount.annual_retirement_return

    # add to remaining months
    retirement_months += 1

    if retirement_months % 12 == 0:
        graph_labels.append(user.current_age + year)
        graph_savings_values.append(current_savings)

print (retirement_months/12+user.retirement_age)