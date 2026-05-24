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

    user = Person(
        current_age=person_config.current_age,
        retirement_age=person_config.retirement_age,
        lifespan=person_config.lifespan,
        pre_tax_income=person_config.pre_tax_income,
        additional_income_tax_deductions=person_config.additional_income_tax_deductions,
        state_of_residence=person_config.state_of_residence,
        filing=person_config.filing,
    )

    for account_name, account_config in yearly_config.Accounts.items():
        user.create_account(
            account_name=account_name,
            initial_savings=account_config.initial_savings,
            regular_investment_dollar=account_config.regular_investment_dollar,
            regular_investment_frequency=account_config.regular_investment_frequency,
            annual_investment_increase=account_config.annual_investment_increase,
            annual_investment_return=account_config.annual_investment_return,
            annual_retirement_return=account_config.annual_retirement_return,
            annual_retirement_post_tax_expense=account_config.annual_retirement_post_tax_expense,
            compound_frequency=account_config.compound_frequency,
            compound_type=account_config.compound_type,
            account_type=account_config.account_type,
        )

    for expense in yearly_config.Expenses:
        user.add_accumulation_expense(expense.name, expense.expense, expense.frequency)

    # Load and validate tax tables
    with open("config/tax.json") as tax_json:
        tax_data = json.load(tax_json)
    tax_config = TaxSchema.model_validate(tax_data)

    # Get the YearlyTaxSchema for current_year
    yearly_tax = tax_config.root[str(current_year)]

    config = GlobalParameters(
        year=current_year,
        inflation_rate=yearly_config.InflationRate,
        yearly_tax=yearly_tax,
    )

    return user, config
