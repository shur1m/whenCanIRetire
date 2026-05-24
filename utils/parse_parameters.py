import json
from utils.parameters import Person
from utils.globals import GlobalParameters
from utils.schemas import ParametersSchema, TaxSchema


def parse_parameters() -> tuple[Person, GlobalParameters]:
    with open("config/parameters.json") as parameters_json:
        parameter_data = json.load(parameters_json)

    # Validate parameters config
    parameters_config = ParametersSchema.model_validate(parameter_data)

    current_year = parameters_config.CurrentYear
    yearly_config = parameters_config.years[str(current_year)]
    person_config = yearly_config.Person

    # Unpack Person config directly
    user = Person(**person_config.model_dump(exclude={"Accounts", "Expenses"}))

    # Unpack Account config directly
    for account_name, account_config in person_config.Accounts.items():
        user.create_account(account_name=account_name, **account_config.model_dump())

    for expense in person_config.Expenses:
        user.add_accumulation_expense(expense.name, expense.expense, expense.frequency)

    # Load and validate tax tables
    with open("config/tax.json") as tax_json:
        tax_data = json.load(tax_json)
    tax_config = TaxSchema.model_validate(tax_data)

    # Get the YearlyTaxSchema for current_year
    yearly_tax = tax_config.root[str(current_year)]

    config = GlobalParameters(
        year=current_year,
        inflation_rate=yearly_tax.InflationRate,
        yearly_tax=yearly_tax,
    )

    return user, config
