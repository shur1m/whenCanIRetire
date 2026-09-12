from decimal import Decimal
from nicegui import ui
from ui.state import AppState
from utils.enums import City, Filing, State


def render_personal_info(state: AppState):
    with ui.element("div").classes("desktop-group w-full"):
        ui.label("Personal Information").classes("desktop-group-title")

        with ui.grid(columns=2).classes("w-full gap-2 min-w-0"):
            with ui.column().classes("gap-0.5 w-full min-w-0"):
                ui.label("Current Age").classes("text-[11px] text-gray-700 font-medium")
                ui.number(
                    value=state.person_schema.current_age,
                    on_change=lambda e: setattr(
                        state.person_schema,
                        "current_age",
                        int(e.value or 0),
                    ),
                ).props("dense outlined").classes("w-full")

            with ui.column().classes("gap-0.5 w-full min-w-0"):
                ui.label("Retirement Age").classes(
                    "text-[11px] text-gray-700 font-medium"
                )
                ui.number(
                    value=state.person_schema.retirement_age,
                    on_change=lambda e: setattr(
                        state.person_schema,
                        "retirement_age",
                        int(e.value or 0),
                    ),
                ).props("dense outlined").classes("w-full")

            with ui.column().classes("gap-0.5 w-full min-w-0"):
                ui.label("Lifespan").classes("text-[11px] text-gray-700 font-medium")
                ui.number(
                    value=state.person_schema.lifespan,
                    on_change=lambda e: setattr(
                        state.person_schema,
                        "lifespan",
                        int(e.value or 0),
                    ),
                ).props("dense outlined").classes("w-full")

            with ui.column().classes("gap-0.5 w-full min-w-0"):
                ui.label("Filing Status").classes(
                    "text-[11px] text-gray-700 font-medium"
                )
                ui.select(
                    {e.value: e.value.capitalize() for e in Filing},
                    value=state.person_schema.filing,
                    on_change=lambda e: setattr(state.person_schema, "filing", e.value),
                ).props("dense outlined options-dense").classes("w-full")

        with ui.column().classes("w-full gap-0.5 mt-2"):
            ui.label("Pre-tax Income ($)").classes(
                "text-[11px] text-gray-700 font-medium"
            )
            ui.number(
                value=float(state.person_schema.pre_tax_income),
                format="%.2f",
                on_change=lambda e: setattr(
                    state.person_schema,
                    "pre_tax_income",
                    Decimal(str(e.value or 0)),
                ),
            ).props("dense outlined").classes("w-full")

        with ui.column().classes("w-full gap-0.5 mt-1.5"):
            ui.label("Additional Tax Deductions ($)").classes(
                "text-[11px] text-gray-700 font-medium"
            )
            ui.number(
                value=float(state.person_schema.additional_income_tax_deductions),
                format="%.2f",
                on_change=lambda e: setattr(
                    state.person_schema,
                    "additional_income_tax_deductions",
                    Decimal(str(e.value or 0)),
                ),
            ).props("dense outlined").classes("w-full")

        with ui.grid(columns=2).classes("w-full gap-2 mt-2 min-w-0"):
            with ui.column().classes("gap-0.5 w-full min-w-0"):
                ui.label("State").classes("text-[11px] text-gray-700 font-medium")

                def on_state_change(e):
                    val = None if (e.value is None or e.value == "(None)") else e.value
                    setattr(state.person_schema, "state_of_residence", val)

                ui.select(
                    ["(None)"] + [e.value for e in State],
                    value=(
                        state.person_schema.state_of_residence
                        if state.person_schema.state_of_residence
                        else "(None)"
                    ),
                    on_change=on_state_change,
                ).props("dense outlined options-dense clearable").classes("w-full")

            with ui.column().classes("gap-0.5 w-full min-w-0"):
                ui.label("City").classes("text-[11px] text-gray-700 font-medium")

                def on_city_change(e):
                    val = None if (e.value is None or e.value == "(None)") else e.value
                    setattr(state.person_schema, "city_of_residence", val)

                ui.select(
                    ["(None)"] + [e.value for e in City],
                    value=(
                        state.person_schema.city_of_residence
                        if state.person_schema.city_of_residence
                        else "(None)"
                    ),
                    on_change=on_city_change,
                ).props("dense outlined options-dense clearable").classes("w-full")
