from typing import Any, Callable
from nicegui import ui
from ui.state import AppState


def render_header(
    state: AppState,
    on_year_change: Callable[[str], Any],
    on_save: Callable[[], Any],
) -> ui.button:
    with ui.header().classes(
        "desktop-toolbar flex items-center justify-between no-wrap"
    ):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label("When Can I Retire?").classes("font-bold text-xs tracking-tight")
            ui.label("|").classes("text-gray-400 mx-1")
            ui.label("Tax Year:").classes("text-xs text-gray-700")

            ui.select(
                options=state.get_available_years(),
                value=state.current_year,
                on_change=lambda e: on_year_change(e.value),
            ).props("dense outlined options-dense").classes("w-20 bg-white")

        with ui.row().classes("items-center gap-2 no-wrap"):
            save_button = ui.button("Save & Calculate", on_click=on_save).classes(
                "desktop-btn desktop-btn-primary"
            )
            return save_button
