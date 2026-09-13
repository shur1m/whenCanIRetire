import asyncio
from pathlib import Path
from typing import Any, Optional

from nicegui import ui

from ui.charts import compute_chart_options
from ui.components import (
    render_accounts,
    render_expenses,
    render_header,
    render_personal_info,
)
from ui.state import AppState

app_state = AppState()

CSS_DIR = Path(__file__).parent / "css"

ECHARTS_LOADING_OPTIONS = {
    "text": "Calculating...",
    "color": "#2b5c8f",
    "textColor": "#222222",
    "maskColor": "rgba(255, 255, 255, 0.6)",
    "fontSize": 12,
    "showSpinner": True,
    "spinnerRadius": 12,
    "lineWidth": 3,
}

INITIAL_BUDGET_OPTIONS = {
    "title": {
        "text": "Annual Spending & Taxes",
        "left": "center",
        "textStyle": {"fontSize": 13, "fontWeight": "bold", "color": "#222222"},
    }
}

INITIAL_RETIREMENT_OPTIONS = {
    "title": {
        "text": "Retirement Savings Projection",
        "left": "center",
        "textStyle": {"fontSize": 13, "fontWeight": "bold", "color": "#222222"},
    }
}


def load_styles():
    for filename in ("base.css", "controls.css", "components.css"):
        css_path = CSS_DIR / filename
        if css_path.exists():
            ui.add_css(css_path)


def init_ui():
    load_styles()

    current_calc_id = 0
    header_save_btn: Optional[ui.button] = None
    drawer_save_btn: Optional[ui.button] = None
    is_calculating = False

    def set_save_buttons_enabled(enabled: bool):
        nonlocal is_calculating
        is_calculating = not enabled
        if header_save_btn is not None:
            header_save_btn.set_enabled(enabled)
        if drawer_save_btn is not None:
            drawer_save_btn.set_enabled(enabled)

    async def update_charts():
        nonlocal current_calc_id
        current_calc_id += 1
        calc_id = current_calc_id

        budget_chart.run_chart_method("showLoading", "default", ECHARTS_LOADING_OPTIONS)
        retirement_chart.run_chart_method(
            "showLoading", "default", ECHARTS_LOADING_OPTIONS
        )
        set_save_buttons_enabled(False)

        user = app_state.user
        config = app_state.config

        try:
            budget_opts, retirement_opts = await asyncio.to_thread(
                compute_chart_options, user, config
            )
        except Exception as ex:
            if calc_id == current_calc_id:
                budget_chart.run_chart_method("hideLoading")
                retirement_chart.run_chart_method("hideLoading")
                set_save_buttons_enabled(True)
                try:
                    ui.notify(
                        f"Error calculating charts: {ex}",
                        type="negative",
                        position="top",
                    )
                except Exception:
                    pass
            return

        # If a newer calculation was started while this one was computing, discard stale result
        if calc_id != current_calc_id:
            return

        budget_chart.options.clear()
        budget_chart.options.update(budget_opts)
        budget_chart.update()
        budget_chart.run_chart_method("setOption", budget_opts, True)

        retirement_chart.options.clear()
        retirement_chart.options.update(retirement_opts)
        retirement_chart.update()
        retirement_chart.run_chart_method("setOption", retirement_opts, True)

        budget_chart.run_chart_method("hideLoading")
        retirement_chart.run_chart_method("hideLoading")
        set_save_buttons_enabled(True)

    async def save_and_calculate():
        if is_calculating:
            return
        try:
            app_state.save_raw_data()
            try:
                ui.notify(
                    "Configuration saved successfully!",
                    type="positive",
                    position="top",
                )
            except Exception:
                pass
            await update_charts()
        except Exception as ex:
            try:
                ui.notify(f"Error saving: {ex}", type="negative", position="top")
            except Exception:
                pass

    async def on_year_change(new_year: Any):
        if hasattr(new_year, "value"):
            new_year = new_year.value
        new_year = str(new_year)
        app_state.set_year(new_year)
        render_config_form()
        try:
            ui.notify(
                f"Switched to Tax Year {new_year}",
                type="info",
                position="top",
            )
        except Exception:
            pass
        await update_charts()

    # Top Toolbar
    header_save_btn = render_header(
        state=app_state,
        on_year_change=on_year_change,
        on_save=save_and_calculate,
    )

    # Left Drawer (Form inputs)
    with ui.left_drawer(value=True).classes("desktop-drawer p-3 overflow-y-auto").style(
        "width: 400px;"
    ):
        form_container = ui.column().classes("w-full gap-2")

        def render_config_form():
            nonlocal drawer_save_btn
            form_container.clear()
            with form_container:
                render_personal_info(app_state)
                render_expenses(app_state, on_refresh=render_config_form)
                render_accounts(app_state, on_refresh=render_config_form)
                drawer_save_btn = ui.button(
                    "Save & Calculate",
                    on_click=save_and_calculate,
                ).classes("desktop-btn desktop-btn-primary w-full mt-2 mb-4")
                if is_calculating and drawer_save_btn is not None:
                    drawer_save_btn.set_enabled(False)

        render_config_form()

    # Main Content Area Header with View Toggle
    with ui.row().classes(
        "w-full bg-[#e8e8e8] border-b border-[#c8c8c8] px-3 py-1.5 items-center justify-between shrink-0"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.label("Charts View:").classes("text-xs font-semibold text-gray-700")

            def update_view_mode(mode: str):
                if mode == "both":
                    budget_panel.set_visibility(True)
                    retirement_panel.set_visibility(True)
                    budget_chart.style("width: 100%; height: 440px; min-height: 440px;")
                    retirement_chart.style(
                        "width: 100%; height: 480px; min-height: 480px;"
                    )
                elif mode == "retirement":
                    budget_panel.set_visibility(False)
                    retirement_panel.set_visibility(True)
                    retirement_chart.style(
                        "width: 100%; height: calc(100vh - 120px); min-height: 520px;"
                    )
                elif mode == "budget":
                    budget_panel.set_visibility(True)
                    retirement_panel.set_visibility(False)
                    budget_chart.style(
                        "width: 100%; height: calc(100vh - 120px); min-height: 520px;"
                    )

                ui.timer(
                    0.05, lambda: budget_chart.run_chart_method("resize"), once=True
                )
                ui.timer(
                    0.05,
                    lambda: retirement_chart.run_chart_method("resize"),
                    once=True,
                )

            ui.toggle(
                {
                    "both": "Both Charts",
                    "retirement": "Retirement Projection",
                    "budget": "Spending & Taxes",
                },
                value="both",
                on_change=lambda e: update_view_mode(e.value),
            ).props("dense unelevated outlined no-caps").classes("text-xs bg-white")

    # Main Content Area Scroll Container
    with ui.element("div").classes("charts-scroll-container"):
        with ui.element("div").classes(
            "desktop-panel p-3 w-full flex flex-col min-w-0"
        ) as budget_panel:
            budget_chart = (
                ui.echart(INITIAL_BUDGET_OPTIONS)
                .classes("w-full")
                .style("width: 100%; height: 440px; min-height: 440px;")
            )

        with ui.element("div").classes(
            "desktop-panel p-3 w-full flex flex-col min-w-0"
        ) as retirement_panel:
            retirement_chart = (
                ui.echart(INITIAL_RETIREMENT_OPTIONS)
                .classes("w-full")
                .style("width: 100%; height: 480px; min-height: 480px;")
            )

    # Initial async load: starts immediately without blocking the UI
    ui.timer(0.01, update_charts, once=True)

    return {
        "app_state": app_state,
        "on_year_change": on_year_change,
        "save_and_calculate": save_and_calculate,
        "update_charts": update_charts,
        "budget_chart": budget_chart,
        "retirement_chart": retirement_chart,
    }
