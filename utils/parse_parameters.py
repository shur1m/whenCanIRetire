import json
from decimal import Decimal
from utils.parameters import Account, Person
from utils.globals import GlobalParameters


def parse_parameters() -> Person:
    user = None
    with open("config/parameters.json") as parameters_json:
        parameter_dict = json.load(parameters_json, parse_float=Decimal)

    current_year = parameter_dict["CurrentYear"]
    current_year_parameters = parameter_dict[str(current_year)]
    person_kwargs = current_year_parameters["Person"]
    user = Person(**person_kwargs)

    for account_name, account_kwargs in current_year_parameters["Accounts"].items():
        user.create_account(account_name, **account_kwargs)

    for expense in current_year_parameters["Expenses"]:
        user.add_accumulation_expense(
            expense["name"], expense["expense"], expense["frequency"]
        )

    GlobalParameters.configure(
        current_year, user, current_year_parameters["InflationRate"]
    )
    return user
