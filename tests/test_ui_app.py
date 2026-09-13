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
