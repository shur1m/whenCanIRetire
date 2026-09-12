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
                name = f"Account {len(state.person_schema.Accounts) + 1}"
                state.person_schema.Accounts[name] = AccountSchema()
                on_refresh()

            ui.button("+ Add", on_click=add_account).classes(
                "desktop-btn text-xs py-0 px-2"
            )

        for acc_name, acc in list(state.person_schema.Accounts.items()):
            with ui.element("div").classes(
                "border border-gray-300 bg-white p-2 mb-2 rounded-sm"
            ):
                with ui.row().classes("items-center justify-between w-full mb-1"):
                    ui.label(acc_name).classes("font-semibold text-xs text-gray-800")

                    def remove_account(name: str):
                        del state.person_schema.Accounts[name]
                        on_refresh()

                    ui.button(
                        "✕ Remove",
                        on_click=lambda _, name=acc_name: remove_account(name),
                    ).props("dense flat").classes("text-red-700 text-xs p-0 h-5")

                with ui.grid(columns=2).classes("w-full gap-2 min-w-0"):
                    with ui.column().classes("gap-0.5 w-full min-w-0"):
                        ui.label("Type").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.select(
                            {
                                e.value: e.value.capitalize()
                                for e in AccountType
                            },
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
                            {
                                e.value: e.value.capitalize()
                                for e in Frequency
                            },
                            value=acc.regular_investment_frequency,
                            on_change=lambda e, name=acc_name: setattr(
                                state.person_schema.Accounts[name],
                                "regular_investment_frequency",
                                e.value,
                            ),
                        ).props("dense outlined options-dense").classes("w-full")
