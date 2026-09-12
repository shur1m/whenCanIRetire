from decimal import Decimal
from typing import Callable

from nicegui import ui

from ui.state import AppState
from utils.enums import AccountType, Frequency
from utils.schemas import AccountSchema


def render_accounts(state: AppState, on_refresh: Callable[[], None]):
    with ui.element("div").classes("desktop-group w-full"):
        with ui.row().classes("items-center justify-between w-full mb-1"):
            ui.label("Investment Accounts").classes("desktop-group-title mb-0")

            def add_account():
                i = len(state.person_schema.Accounts) + 1
                while f"Account {i}" in state.person_schema.Accounts:
                    i += 1
                name = f"Account {i}"
                state.person_schema.Accounts[name] = AccountSchema()
                on_refresh()

            ui.button("+ Add", on_click=add_account).classes(
                "desktop-btn text-xs py-0 px-2"
            )

        for acc_name, acc in list(state.person_schema.Accounts.items()):
            with ui.element("div").classes(
                "border border-gray-300 bg-white p-2 mb-2 rounded-sm"
            ):
                header_container = ui.row().classes(
                    "items-center justify-between w-full mb-1 min-h-[26px]"
                )

                def setup_header(container: ui.row, current_name: str):
                    container.clear()
                    with container:
                        ui.label(current_name).classes(
                            "font-semibold text-xs text-gray-800 truncate"
                        )
                        with ui.row().classes("items-center gap-1 shrink-0"):
                            ui.button(
                                "✎",
                                on_click=lambda _, c=container, n=current_name: setup_edit_mode(
                                    c, n
                                ),
                            ).props("dense flat").classes(
                                "text-blue-700 text-xs p-0 h-5 w-5"
                            ).tooltip(
                                "Edit"
                            )

                            def remove_account(name: str):
                                del state.person_schema.Accounts[name]
                                on_refresh()

                            ui.button(
                                "✕",
                                on_click=lambda _, name=current_name: remove_account(
                                    name
                                ),
                            ).props("dense flat").classes(
                                "text-red-700 text-xs p-0 h-5 w-5"
                            ).tooltip(
                                "Remove"
                            )

                def setup_edit_mode(container: ui.row, current_name: str):
                    container.clear()
                    with container:
                        with ui.row().classes("items-center gap-1 w-full no-wrap"):
                            name_input = (
                                ui.input(value=current_name)
                                .props("dense outlined autofocus")
                                .classes("item-rename-input text-xs")
                            )

                            def save():
                                new_name = (
                                    name_input.value.strip() if name_input.value else ""
                                )
                                if not new_name:
                                    ui.notify(
                                        "Account name cannot be empty.",
                                        type="warning",
                                        position="top",
                                    )
                                    return
                                if (
                                    new_name != current_name
                                    and new_name in state.person_schema.Accounts
                                ):
                                    ui.notify(
                                        f"Account '{new_name}' already exists.",
                                        type="warning",
                                        position="top",
                                    )
                                    return
                                if new_name != current_name:
                                    state.rename_account(current_name, new_name)
                                    on_refresh()
                                else:
                                    setup_header(container, current_name)

                            name_input.on("keydown.enter", save)
                            name_input.on(
                                "keydown.escape",
                                lambda: setup_header(container, current_name),
                            )

                            ui.button("✓", on_click=save).props("dense flat").classes(
                                "text-green-700 font-bold text-xs p-0 h-5 w-5 shrink-0"
                            ).tooltip("Save")
                            ui.button(
                                "✕",
                                on_click=lambda _, c=container, n=current_name: setup_header(
                                    c, n
                                ),
                            ).props("dense flat").classes(
                                "text-gray-600 font-bold text-xs p-0 h-5 w-5 shrink-0"
                            ).tooltip(
                                "Cancel"
                            )

                setup_header(header_container, acc_name)

                with ui.grid(columns=2).classes("w-full gap-2 min-w-0"):
                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Type").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.select(
                            {e.value: e.value.capitalize() for e in AccountType},
                            value=acc.account_type,
                            on_change=lambda e, name=acc_name: setattr(
                                state.person_schema.Accounts[name],
                                "account_type",
                                e.value,
                            ),
                        ).props("dense outlined options-dense").classes("w-full")

                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Initial ($)").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.number(
                            value=float(acc.initial_savings),
                            format="%.2f",
                            on_change=lambda e, name=acc_name: setattr(
                                state.person_schema.Accounts[name],
                                "initial_savings",
                                Decimal(str(e.value or 0)),
                            ),
                        ).props("dense outlined").classes("w-full")

                with ui.grid(columns=2).classes("w-full gap-2 mt-1.5 min-w-0"):
                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Regular Inv. ($)").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.number(
                            value=float(acc.regular_investment_dollar),
                            format="%.2f",
                            on_change=lambda e, name=acc_name: setattr(
                                state.person_schema.Accounts[name],
                                "regular_investment_dollar",
                                Decimal(str(e.value or 0)),
                            ),
                        ).props("dense outlined").classes("w-full")

                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Frequency").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.select(
                            {e.value: e.value.capitalize() for e in Frequency},
                            value=acc.regular_investment_frequency,
                            on_change=lambda e, name=acc_name: setattr(
                                state.person_schema.Accounts[name],
                                "regular_investment_frequency",
                                e.value,
                            ),
                        ).props("dense outlined options-dense").classes("w-full")
