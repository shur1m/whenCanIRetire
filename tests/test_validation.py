import pytest
from pydantic import ValidationError
from utils.schemas import ParametersSchema, TaxSchema


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
