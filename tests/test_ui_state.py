import json
import shutil
from pathlib import Path


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


def test_app_state_rename_account_success(tmp_path: Path):
    src_config = Path("config/parameters.json")
    temp_config = tmp_path / "parameters.json"
    shutil.copy(src_config, temp_config)

    state = AppState(config_path=str(temp_config))
    original_names = list(state.person_schema.Accounts.keys())
    target_name = original_names[0]
    new_name = "Custom Renamed Account"

    original_acc_data = state.person_schema.Accounts[target_name].model_dump()

    assert state.rename_account(target_name, new_name) is True
    assert target_name not in state.person_schema.Accounts
    assert new_name in state.person_schema.Accounts

    # Verify order is preserved
    expected_names = [
        new_name if name == target_name else name for name in original_names
    ]
    assert list(state.person_schema.Accounts.keys()) == expected_names

    # Verify account properties are retained
    assert state.person_schema.Accounts[new_name].model_dump() == original_acc_data


def test_app_state_rename_account_validation(tmp_path: Path):
    src_config = Path("config/parameters.json")
    temp_config = tmp_path / "parameters.json"
    shutil.copy(src_config, temp_config)

    state = AppState(config_path=str(temp_config))
    original_names = list(state.person_schema.Accounts.keys())
    first_name = original_names[0]
    second_name = original_names[1]

    # Non-existent account
    assert state.rename_account("NonExistentAccount", "NewName") is False

    # Empty or whitespace new name
    assert state.rename_account(first_name, "") is False
    assert state.rename_account(first_name, "   ") is False

    # Duplicate name
    assert state.rename_account(first_name, second_name) is False

    # Renaming to same name returns True (no-op)
    assert state.rename_account(first_name, first_name) is True

    # State accounts unchanged
    assert list(state.person_schema.Accounts.keys()) == original_names


def test_app_state_rename_account_save(tmp_path: Path):
    src_config = Path("config/parameters.json")
    temp_config = tmp_path / "parameters.json"
    shutil.copy(src_config, temp_config)

    state = AppState(config_path=str(temp_config))
    original_names = list(state.person_schema.Accounts.keys())
    target_name = original_names[0]
    new_name = "Roth 401(k) Primary"

    assert state.rename_account(target_name, new_name) is True
    state.save_raw_data()

    # Verify persisted to JSON on disk
    with open(temp_config, "r") as f:
        saved_data = json.load(f)

    saved_accounts = saved_data[state.current_year]["Person"]["Accounts"]
    assert new_name in saved_accounts
    assert target_name not in saved_accounts

    # Reload into new AppState and verify simulation objects
    reloaded_state = AppState(config_path=str(temp_config))
    assert new_name in reloaded_state.person_schema.Accounts
    assert target_name not in reloaded_state.person_schema.Accounts
    assert new_name in reloaded_state.user.accounts


def test_render_accounts_renders_without_error():
    from ui.components.accounts import render_accounts

    state = AppState()
    render_accounts(state, on_refresh=lambda: None)


def test_render_expenses_renders_without_error():
    from ui.components.expenses import render_expenses

    state = AppState()
    render_expenses(state, on_refresh=lambda: None)
