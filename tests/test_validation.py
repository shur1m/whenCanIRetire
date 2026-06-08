import pytest
from pydantic import ValidationError
from utils.schemas import ParametersSchema, TaxSchema
from utils.parameters import Person
from utils.enums import Filing, State
from utils.globals import GlobalParameters
from decimal import Decimal
import copy


def test_invalid_parameters_json_missing_current_year():
    invalid_data = {
        # missing CurrentYear
        "2026": {
            "Person": {
                "current_age": 24,
                "retirement_age": 50,
                "lifespan": 120,
                "pre_tax_income": 120000,
            },
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        ParametersSchema.model_validate(invalid_data)
    assert "CurrentYear" in str(exc_info.value)


def test_invalid_parameters_json_bad_enum_value():
    invalid_data = {
        "CurrentYear": 2026,
        "2026": {
            "Person": {
                "current_age": 24,
                "retirement_age": 50,
                "lifespan": 120,
                "pre_tax_income": 120000,
                "filing": "not-a-valid-filing-status",
            },
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        ParametersSchema.model_validate(invalid_data)
    assert "filing" in str(exc_info.value)


def test_invalid_tax_json_missing_federal_tax():
    invalid_data = {
        "2026": {
            "InflationRate": 0.03,
            # missing FederalTax
            "StateTax": {},
            "FicaTax": {
                "SocialSecurityMaxTaxable": 184500,
                "SocialSecurityTaxPercent": 0.062,
                "MedicareHighEarnerTax": 0.09,
                "MedicareHighEarnerSalaryIndividual": 200000,
                "MedicareHighEarnerSalaryJoint": 250000,
                "MedicareTaxPercent": 0.0145,
            },
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        TaxSchema.model_validate(invalid_data)
    assert "FederalTax" in str(exc_info.value)


def test_missing_state_tax_raises_value_error(tax_data):
    user = Person(
        current_age=30,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=115_000,
        state_of_residence=State.CALIFORNIA,
        filing=Filing.INDIVIDUAL,
    )

    # Create a copy and remove California from StateTax to simulate missing state tax configuration
    yearly_tax_copy = copy.deepcopy(tax_data.root["2026"])
    if State.CALIFORNIA in yearly_tax_copy.StateTax:
        del yearly_tax_copy.StateTax[State.CALIFORNIA]

    config_2026 = GlobalParameters(
        year=2026,
        inflation_rate=Decimal("0.03"),
        yearly_tax=yearly_tax_copy,
    )

    with pytest.raises(ValueError, match="State tax brackets configuration is missing"):
        config_2026.get_state_tax_brackets(State.CALIFORNIA, user.filing)

    with pytest.raises(
        ValueError, match="State tax deduction configuration is missing"
    ):
        config_2026.get_state_tax_deduction(State.CALIFORNIA, user.filing)

    with pytest.raises(ValueError, match="State tax configuration is missing"):
        config_2026.calculate_state_surcharges(
            State.CALIFORNIA, "ordinary", Decimal("100000")
        )
