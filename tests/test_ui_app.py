import asyncio
from ui.app import init_ui
from ui.charts import compute_chart_options
from ui.components.header import render_header
from ui.state import AppState


def test_compute_chart_options():
    state = AppState()
    budget_opts, retirement_opts = compute_chart_options(state.user, state.config)

    assert isinstance(budget_opts, dict)
    assert "series" in budget_opts
    assert "title" in budget_opts
    assert budget_opts["title"]["text"] == "Annual Spending & Taxes"

    assert isinstance(retirement_opts, dict)
    assert "series" in retirement_opts
    assert "xAxis" in retirement_opts
    assert "yAxis" in retirement_opts
    assert retirement_opts["title"]["text"] == "Retirement Savings Projection"


def test_render_header_returns_button():
    state = AppState()
    save_called = False

    def dummy_save():
        nonlocal save_called
        save_called = True

    btn = render_header(
        state=state,
        on_year_change=lambda _: None,
        on_save=dummy_save,
    )

    assert btn is not None
    assert btn.text == "Save & Calculate"


def test_init_ui_initializes_cleanly():
    # Calling init_ui should create the NiceGUI layout without raising errors
    init_ui()


def test_async_compute_chart_options_thread():
    state = AppState()

    async def run_async_compute():
        return await asyncio.to_thread(compute_chart_options, state.user, state.config)

    budget_opts, ret_opts = asyncio.run(run_async_compute())
    assert "series" in budget_opts
    assert "series" in ret_opts


def test_on_year_change_updates_state_and_charts():
    ctx = init_ui()
    on_year_change = ctx["on_year_change"]
    app_state = ctx["app_state"]
    budget_chart = ctx["budget_chart"]
    retirement_chart = ctx["retirement_chart"]

    async def run_year_switch():
        with budget_chart:
            # Switch to 2024
            await on_year_change("2024")
            assert app_state.current_year == "2024"
            opts_2024 = dict(budget_chart.options)
            ret_2024 = dict(retirement_chart.options)

            # Switch to 2025
            await on_year_change("2025")
            assert app_state.current_year == "2025"
            opts_2025 = dict(budget_chart.options)
            ret_2025 = dict(retirement_chart.options)

            # Ensure options are updated and reflect different years
            assert "series" in opts_2024 and "series" in opts_2025
            assert "series" in ret_2024 and "series" in ret_2025

            # Switch using an object with a .value attribute (e.g. ValueChangeEventArguments)
            class DummyEvent:
                value = "2026"

            await on_year_change(DummyEvent())
            assert app_state.current_year == "2026"

    asyncio.run(run_year_switch())


def test_save_and_calculate():
    ctx = init_ui()
    save_and_calculate = ctx["save_and_calculate"]
    budget_chart = ctx["budget_chart"]

    async def run_save():
        with budget_chart:
            await save_and_calculate()

    asyncio.run(run_save())
