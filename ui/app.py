from pathlib import Path

from nicegui import ui

from ui.charts import (
    get_budget_pie_chart_options,
    get_retirement_line_chart_options,
)
from ui.components import (
    render_accounts,
    render_expenses,
    render_header,
    render_personal_info,
)
from ui.state import AppState

app_state = AppState()

CSS_DIR = Path(__file__).parent / "css"


def load_styles():
    for filename in ("base.css", "controls.css", "components.css"):
        css_path = CSS_DIR / filename
        if css_path.exists():
            ui.add_css(css_path)


def init_ui():
    load_styles()

    def update_charts():
        budget_chart.options.clear()
        budget_chart.options.update(
            get_budget_pie_chart_options(app_state.user, app_state.config)
        )
        budget_chart.update()
        retirement_chart.options.clear()
        retirement_chart.options.update(
            get_retirement_line_chart_options(app_state.user, app_state.config)
        )
        retirement_chart.update()

    def save_and_calculate():
        try:
            app_state.save_raw_data()
            ui.notify(
                "Configuration saved successfully!",
                type="positive",
                position="top",
            )
            update_charts()
        except Exception as ex:
            ui.notify(f"Error saving: {ex}", type="negative", position="top")

    def on_year_change(new_year: str):
        app_state.set_year(new_year)
        render_config_form()
        update_charts()
        ui.notify(
            f"Switched to Tax Year {new_year}",
            type="info",
            position="top",
        )

    # Top Toolbar
    render_header(
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
            form_container.clear()
            with form_container:
                render_personal_info(app_state)
                render_expenses(app_state, on_refresh=render_config_form)
                render_accounts(app_state, on_refresh=render_config_form)
                ui.button("Save & Calculate", on_click=save_and_calculate).classes(
                    "desktop-btn desktop-btn-primary w-full mt-2 mb-4"
                )

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
                ui.echart(
                    get_budget_pie_chart_options(app_state.user, app_state.config)
                )
                .classes("w-full")
                .style("width: 100%; height: 440px; min-height: 440px;")
            )

        with ui.element("div").classes(
            "desktop-panel p-3 w-full flex flex-col min-w-0"
        ) as retirement_panel:
            retirement_chart = (
                ui.echart(
                    get_retirement_line_chart_options(app_state.user, app_state.config)
                )
                .classes("w-full")
                .style("width: 100%; height: 480px; min-height: 480px;")
            )
