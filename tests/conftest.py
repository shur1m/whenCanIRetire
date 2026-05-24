import pytest
from decimal import Decimal
import json
from utils.globals import GlobalParameters
from utils.parameters import Person
from utils.enums import Filing, State
from utils.schemas import TaxSchema


@pytest.fixture(scope="session")
def tax_data() -> TaxSchema:
    with open("config/tax.json") as f:
        return TaxSchema.model_validate(json.load(f))


@pytest.fixture
def config_2024(tax_data) -> GlobalParameters:
    return GlobalParameters(
        year=2024, inflation_rate=Decimal("0.03"), yearly_tax=tax_data.root["2024"]
    )


@pytest.fixture
def person_tx_115k() -> Person:
    """Single filer, Texas (no state tax), $115k pre-tax income."""
    return Person(
        current_age=30,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=115_000,
        state_of_residence=State.TEXAS,
        filing=Filing.INDIVIDUAL,
    )


@pytest.fixture
def person_ca_115k() -> Person:
    """Single filer, California, $115k pre-tax income."""
    return Person(
        current_age=30,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=115_000,
        state_of_residence=State.CALIFORNIA,
        filing=Filing.INDIVIDUAL,
    )


@pytest.fixture
def person_tx_joint_200k() -> Person:
    """Joint filer, Texas, $200k pre-tax income."""
    return Person(
        current_age=35,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=200_000,
        state_of_residence=State.TEXAS,
        filing=Filing.JOINT,
    )
