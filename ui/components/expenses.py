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
                header_container = ui.row().classes(
                    "items-center justify-between w-full mb-1 min-h-[26px]"
                )

                def setup_expense_header(container: ui.row, idx: int):
                    container.clear()
                    current_exp = state.person_schema.Expenses[idx]
                    with container:
                        ui.label(current_exp.name).classes(
                            "font-semibold text-xs text-gray-800 truncate"
                        )
                        with ui.row().classes("items-center gap-1 shrink-0"):
                            ui.button(
                                "✎",
                                on_click=lambda _, c=container, index=idx: setup_expense_edit_mode(
                                    c, index
                                ),
                            ).props("dense flat").classes(
                                "text-blue-700 text-xs p-0 h-5 w-5"
                            )

                            def remove_expense(remove_idx: int):
                                state.person_schema.Expenses.pop(remove_idx)
                                on_refresh()

                            ui.button(
                                "✕",
                                on_click=lambda _, index=idx: remove_expense(index),
                            ).props("dense flat").classes(
                                "text-red-700 text-xs p-0 h-5 w-5"
                            )

                def setup_expense_edit_mode(container: ui.row, idx: int):
                    container.clear()
                    current_exp = state.person_schema.Expenses[idx]
                    with container:
                        with ui.row().classes("items-center gap-1 w-full no-wrap"):
                            name_input = (
                                ui.input(value=current_exp.name)
                                .props("dense outlined autofocus")
                                .classes("item-rename-input text-xs")
                            )

                            def save():
                                new_name = (
                                    name_input.value.strip() if name_input.value else ""
                                )
                                if not new_name:
                                    ui.notify(
                                        "Expense name cannot be empty.",
                                        type="warning",
                                        position="top",
                                    )
                                    return
                                state.person_schema.Expenses[idx].name = new_name
                                setup_expense_header(container, idx)

                            name_input.on("keydown.enter", save)
                            name_input.on(
                                "keydown.escape",
                                lambda: setup_expense_header(container, idx),
                            )

                            ui.button("✓", on_click=save).props("dense flat").classes(
                                "text-green-700 font-bold text-xs p-0 h-5 w-5 shrink-0"
                            )
                            ui.button(
                                "✕",
                                on_click=lambda _, c=container, index=idx: setup_expense_header(
                                    c, index
                                ),
                            ).props("dense flat").classes(
                                "text-red-700 font-bold text-xs p-0 h-5 w-5 shrink-0"
                            )

                setup_expense_header(header_container, i)

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
