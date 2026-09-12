import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any
from utils.enums import AccountType, Filing, Frequency, MonthlyCompoundType
from utils.parameters import Person
from utils.globals import GlobalParameters
from utils.schemas import (
    AccountSchema,
    ExpenseSchema,
    ParametersSchema,
    PersonSchema,
    TaxSchema,
)


def create_default_person_schema() -> PersonSchema:
    return PersonSchema(
        current_age=24,
        retirement_age=65,
        lifespan=100,
        pre_tax_income=Decimal("115000"),
        additional_income_tax_deductions=Decimal("0"),
        state_of_residence=None,
        city_of_residence=None,
        filing=Filing.INDIVIDUAL,
        Accounts={
            "401(k)": AccountSchema(
                account_type=AccountType.TRADITIONAL,
                regular_investment_frequency=Frequency.MONTHLY,
                initial_savings=Decimal("0"),
                regular_investment_dollar=Decimal("1916.67"),
                annual_investment_increase=Decimal("0.02"),
                annual_investment_return=Decimal("0.07"),
                annual_retirement_return=Decimal("0.05"),
                compound_frequency=Frequency.MONTHLY,
                compound_type=MonthlyCompoundType.ROOT,
            ),
            "ROTH IRA": AccountSchema(
                account_type=AccountType.ROTH,
                regular_investment_frequency=Frequency.MONTHLY,
                initial_savings=Decimal("0"),
                regular_investment_dollar=Decimal("583.33"),
                annual_investment_increase=Decimal("0.02"),
                annual_investment_return=Decimal("0.07"),
                annual_retirement_return=Decimal("0.05"),
                compound_frequency=Frequency.MONTHLY,
                compound_type=MonthlyCompoundType.ROOT,
            ),
            "HSA": AccountSchema(
                account_type=AccountType.HSA,
                regular_investment_frequency=Frequency.MONTHLY,
                initial_savings=Decimal("0"),
                regular_investment_dollar=Decimal("325.00"),
                annual_investment_increase=Decimal("0.02"),
                annual_investment_return=Decimal("0.07"),
                annual_retirement_return=Decimal("0.05"),
                compound_frequency=Frequency.MONTHLY,
                compound_type=MonthlyCompoundType.ROOT,
            ),
        },
        Expenses=[
            ExpenseSchema(
                name="Fixed Costs",
                expense=Decimal("3000.00"),
                frequency=Frequency.MONTHLY,
            )
        ],
    )


def generate_default_parameters(
    parameters_path: str = "config/parameters.json",
    tax_path: str = "config/tax.json",
) -> dict:
    tax_years: list[str] = []
    if os.path.exists(tax_path):
        try:
            with open(tax_path, "r") as f:
                tax_data = json.load(f)
                tax_years = sorted(list(tax_data.keys()))
        except Exception:
            tax_years = []

    if not tax_years:
        tax_years = ["2024", "2025", "2026"]

    current_year = int(tax_years[-1])
    person_dict = create_default_person_schema().model_dump(mode="json")
    out: dict[str, Any] = {"CurrentYear": current_year}
    for yr in tax_years:
        out[yr] = {"Person": person_dict}

    target_path = Path(parameters_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w") as f:
        json.dump(out, f, indent=4)

    return out


def parse_parameters(
    year: int | None = None,
    parameters_path: str = "config/parameters.json",
) -> tuple[Person, GlobalParameters]:
    if not os.path.exists(parameters_path) or os.path.getsize(parameters_path) == 0:
        generate_default_parameters(parameters_path)

    with open(parameters_path) as parameters_json:
        parameter_data = json.load(parameters_json)

    # Validate parameters config
    parameters_config = ParametersSchema.model_validate(parameter_data)

    current_year = year if year is not None else parameters_config.CurrentYear
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
