from decimal import Decimal
from typing import Callable

from nicegui import ui

from ui.state import AppState
from utils.enums import Frequency
from utils.schemas import ExpenseSchema


def render_expenses(state: AppState, on_refresh: Callable[[], None]):
    with ui.element("div").classes("desktop-group w-full"):
        with ui.row().classes("items-center justify-between w-full mb-1"):
            ui.label("Accumulation Expenses").classes("desktop-group-title mb-0")

            def add_expense():
                state.person_schema.Expenses.append(
                    ExpenseSchema(
                        name="New Expense",
                        expense=Decimal("0.00"),
                        frequency=Frequency.MONTHLY,
                    )
                )
                on_refresh()

            ui.button("+ Add", on_click=add_expense).classes(
                "desktop-btn text-xs py-0 px-2"
            )

        for i, exp in enumerate(state.person_schema.Expenses):
            with ui.element("div").classes(
                "border border-gray-300 bg-white p-2 mb-2 rounded-sm"
            ):
                with ui.row().classes("items-center justify-between w-full mb-1"):
                    ui.label("Expense Name").classes(
                        "text-[11px] text-gray-700 font-medium"
                    )

                    def remove_expense(idx: int):
                        state.person_schema.Expenses.pop(idx)
                        on_refresh()

                    ui.button(
                        "✕ Remove",
                        on_click=lambda _, idx=i: remove_expense(idx),
                    ).props("dense flat").classes("text-red-700 text-xs p-0 h-5")

                ui.input(
                    value=exp.name,
                    on_change=lambda e, idx=i: setattr(
                        state.person_schema.Expenses[idx],
                        "name",
                        e.value,
                    ),
                ).props("dense outlined").classes("w-full mb-1.5")

                with ui.grid(columns=2).classes("w-full gap-2 min-w-0"):
                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Amount ($)").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.number(
                            value=float(exp.expense),
                            format="%.2f",
                            on_change=lambda e, idx=i: setattr(
                                state.person_schema.Expenses[idx],
                                "expense",
                                Decimal(str(e.value or 0)),
                            ),
                        ).props("dense outlined").classes("w-full")

                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Frequency").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.select(
                            {e.value: e.value.capitalize() for e in Frequency},
                            value=exp.frequency,
                            on_change=lambda e, idx=i: setattr(
                                state.person_schema.Expenses[idx],
                                "frequency",
                                e.value,
                            ),
                        ).props("dense outlined options-dense").classes("w-full")
