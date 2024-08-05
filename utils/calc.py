import math

def adjust_for_inflation(todays_dollars: int,  months: int, inflation_rate: int):
    inflation_multiplier = 1 + inflation_rate
    inflation_per_month = math.pow(inflation_multiplier, 1/12)
    return todays_dollars * math.pow(inflation_per_month, months)