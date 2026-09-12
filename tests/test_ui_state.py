import json
import shutil
from pathlib import Path

import pytest

from ui.state import AppState


def test_app_state_initialization():
    state = AppState()
    assert state.current_year in state.get_available_years()
    assert state.person_schema is not None
    assert state.user is not None
    assert state.config is not None
    assert len(state.get_available_years()) > 0


def test_app_state_set_year():
    state = AppState()
    years = state.get_available_years()
    if len(years) > 1:
        other_year = [y for y in years if y != state.current_year][0]
        state.set_year(other_year)
        assert state.current_year == other_year
        assert state.person_schema == state.parameters_schema.years[other_year].Person


def test_app_state_save_raw_data(tmp_path: Path):
    src_config = Path("config/parameters.json")
    temp_config = tmp_path / "parameters.json"
    shutil.copy(src_config, temp_config)

    state = AppState(config_path=str(temp_config))
    original_age = state.person_schema.current_age
    new_age = original_age + 5

    state.person_schema.current_age = new_age
    state.save_raw_data()

    # Verify JSON file structure directly on disk
    with open(temp_config, "r") as f:
        saved_data = json.load(f)

    assert "CurrentYear" in saved_data
    # Ensure years are flattened to the root level, NOT nested under a "years" key
    assert state.current_year in saved_data
    assert saved_data[state.current_year]["Person"]["current_age"] == new_age

    # Verify reload parses cleanly
    reloaded_state = AppState(config_path=str(temp_config))
    assert reloaded_state.person_schema.current_age == new_age
