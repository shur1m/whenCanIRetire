"""
Shared pytest fixtures for regression tests.

GlobalParameters is a class-level (global) singleton that must be configured
before any tax or retirement calculations run. Fixtures here handle that setup
so individual test modules don't have to.
"""
import pytest
from utils.globals import GlobalParameters
from utils.parameters import Person, Account
from utils.enums import Filing, Frequency, MonthlyCompoundType, AccountType, State


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def configure_2024(user: Person) -> None:
    """Load 2024 tax tables into GlobalParameters for the given user."""
    GlobalParameters.configure(2024, user)


# ---------------------------------------------------------------------------
# Basic person fixtures (no state tax)
# ---------------------------------------------------------------------------

@pytest.fixture
def person_tx_115k() -> Person:
    """Single filer, Texas (no state tax), $115k pre-tax income, 2024 tables."""
    user = Person(
        current_age=30,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=115_000,
        state_of_residence=State.TEXAS,
        filing=Filing.INDIVIDUAL,
    )
    configure_2024(user)
    return user


@pytest.fixture
def person_ca_115k() -> Person:
    """Single filer, California, $115k pre-tax income, 2024 tables."""
    user = Person(
        current_age=30,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=115_000,
        state_of_residence=State.CALIFORNIA,
        filing=Filing.INDIVIDUAL,
    )
    configure_2024(user)
    return user


@pytest.fixture
def person_tx_joint_200k() -> Person:
    """Joint filer, Texas, $200k pre-tax income, 2024 tables."""
    user = Person(
        current_age=35,
        retirement_age=65,
        lifespan=90,
        pre_tax_income=200_000,
        state_of_residence=State.TEXAS,
        filing=Filing.JOINT,
    )
    configure_2024(user)
    return user
