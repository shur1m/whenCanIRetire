import json
from decimal import Decimal
from typing import Dict, List

from nicegui import ui

from calculate.aggregate import (
    calculate_income_distribution_data,
    calculate_retirement_deductions_excess,
)
from calculate.simulator import RetirementSimulator
from utils.enums import AccountType, City, Filing, Frequency, MonthlyCompoundType, State
from utils.globals import GlobalParameters
from utils.parameters import Person
from utils.parse_parameters import parse_parameters
from utils.schemas import (
    AccountSchema,
    ExpenseSchema,
    ParametersSchema,
    PersonSchema,
)


class AppState:
    def __init__(self):
        self.raw_data = self.load_raw_data()
        self.parameters_schema = ParametersSchema.model_validate(self.raw_data)
        self.current_year = str(self.parameters_schema.CurrentYear)
        if self.current_year not in self.parameters_schema.years:
            self.current_year = sorted(list(self.parameters_schema.years.keys()))[-1]
        self.person_schema = self.parameters_schema.years[self.current_year].Person
        self.user, self.config = parse_parameters(year=int(self.current_year))

    def get_available_years(self) -> List[str]:
        return sorted(list(self.parameters_schema.years.keys()))

    def load_raw_data(self) -> dict:
        with open("config/parameters.json", "r") as f:
            return json.load(f)

    def set_year(self, year_str: str):
        self.current_year = year_str
        self.parameters_schema.CurrentYear = int(year_str)
        self.person_schema = self.parameters_schema.years[self.current_year].Person
        self.user, self.config = parse_parameters(year=int(self.current_year))

    def save_raw_data(self):
        self.parameters_schema.years[self.current_year].Person = self.person_schema
        self.parameters_schema.CurrentYear = int(self.current_year)
        dumped = self.parameters_schema.model_dump(mode="json")
        out = {"CurrentYear": dumped["CurrentYear"]}
        for year_k, year_v in dumped.get("years", {}).items():
            out[year_k] = year_v
        with open("config/parameters.json", "w") as f:
            json.dump(out, f, indent=4)
        self.user, self.config = parse_parameters(year=int(self.current_year))


app_state = AppState()


def get_budget_pie_chart_options(user: Person, config: GlobalParameters) -> dict:
    pie_data = calculate_income_distribution_data(user, config)
    user_tax = (
        pie_data.get("Federal Income tax", Decimal("0"))
        + pie_data.get("Medicare Tax", Decimal("0"))
        + pie_data.get("Social Security Tax", Decimal("0"))
        + pie_data.get("State Tax", Decimal("0"))
        + pie_data.get("Local Tax", Decimal("0"))
    )
    retirement_deductions_excess = calculate_retirement_deductions_excess(
        user, config, user_tax
    )

    data = [{"value": round(float(v), 2), "name": k} for k, v in pie_data.items()]
    total = sum(float(v) for v in pie_data.values())
    total_formatted = f"{total:,.2f}"
    tax_savings_formatted = f"{float(retirement_deductions_excess):,.2f}"

    return {
        "animation": True,
        "animationDuration": 500,
        "title": {
            "text": "Annual Spending & Taxes",
            "subtext": (
                f"Total: ${total_formatted}  |  Taxes saved by retirement accounts: ${tax_savings_formatted}"
            ),
            "left": "center",
            "textStyle": {"fontSize": 13, "fontWeight": "bold", "color": "#222222"},
            "subtextStyle": {"fontSize": 11, "color": "#555555"},
        },
        "tooltip": {
            "trigger": "item",
            ":formatter": """(params) => {
                var val = Number(params.value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                return params.marker + ' ' + params.name + '<br/><b>$' + val + '</b> (' + Number(params.percent).toFixed(2) + '%)';
            }""",
        },
        "legend": {
            "bottom": "2%",
            "left": "center",
            "type": "scroll",
            "textStyle": {"fontSize": 11, "color": "#333333"},
        },
        "series": [
            {
                "name": "Spending",
                "type": "pie",
                "radius": ["35%", "65%"],
                "center": ["50%", "48%"],
                "avoidLabelOverlap": True,
                "itemStyle": {
                    "borderRadius": 2,
                    "borderColor": "#ffffff",
                    "borderWidth": 1,
                },
                "label": {
                    "show": True,
                    ":formatter": """(params) => {
                        var val = Number(params.value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        return params.name + '\\n$' + val + ' (' + Number(params.percent).toFixed(2) + '%)';
                    }""",
                    "fontSize": 11,
                    "color": "#333333",
                },
                "data": data,
            }
        ],
    }


def get_retirement_line_chart_options(user: Person, config: GlobalParameters) -> dict:
    simulator = RetirementSimulator(user, config)
    results = simulator.simulate()

    series = []
    total_savings_graph_labels = []
    total_savings_graph_values: list[Decimal] = []

    for account_name, (graph_labels, graph_savings_values) in results.items():
        float_values = [round(float(v), 2) for v in graph_savings_values]
        series.append(
            {
                "name": account_name,
                "type": "line",
                "data": float_values,
                "showSymbol": False,
                "lineStyle": {"width": 1.75},
            }
        )
        if len(graph_labels) > len(total_savings_graph_labels):
            total_savings_graph_labels = graph_labels

        for i, val in enumerate(graph_savings_values):
            if i >= len(total_savings_graph_values):
                total_savings_graph_values.append(Decimal("0"))
            total_savings_graph_values[i] += val

    float_total_savings = [round(float(v), 2) for v in total_savings_graph_values]
    series.append(
        {
            "name": "Total Savings",
            "type": "line",
            "data": float_total_savings,
            "showSymbol": False,
            "lineStyle": {"width": 2.5, "color": "#2b5c8f"},
        }
    )

    yearly_retirement_expense = float(user.annual_retirement_post_tax_expense)
    expense_formatted = f"{yearly_retirement_expense:,.2f}"

    return {
        "animation": True,
        "animationDuration": 500,
        "title": {
            "text": "Retirement Savings Projection",
            "subtext": f"Yearly retirement post-tax expense: ${expense_formatted}",
            "left": "center",
            "textStyle": {"fontSize": 13, "fontWeight": "bold", "color": "#222222"},
            "subtextStyle": {"fontSize": 11, "color": "#555555"},
        },
        "tooltip": {
            "trigger": "axis",
            ":formatter": """(params) => {
                var res = '<div style="font-size:11px;"><b>Age: ' + params[0].name + '</b><br/>';
                for (var i = 0; i < params.length; i++) {
                    var val = Number(params[i].value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    res += params[i].marker + ' ' + params[i].seriesName + ': <b>$' + val + '</b><br/>';
                }
                res += '</div>';
                return res;
            }""",
        },
        "legend": {
            "bottom": "2%",
            "left": "center",
            "type": "scroll",
            "textStyle": {"fontSize": 11, "color": "#333333"},
        },
        "grid": {
            "left": "3%",
            "right": "3%",
            "top": "14%",
            "bottom": "12%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": total_savings_graph_labels,
            "name": "Age",
            "nameLocation": "middle",
            "nameGap": 25,
            "axisLabel": {"fontSize": 11, "color": "#333333"},
        },
        "yAxis": {
            "type": "value",
            "name": "Savings ($)",
            "axisLabel": {
                ":formatter": """(val) => {
                    return '$' + Number(val).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                }""",
                "fontSize": 11,
                "color": "#333333",
            },
        },
        "series": series,
    }


def init_ui():
    ui.add_head_html(
        """
<style>
/* Desktop native aesthetic (HomeBank / Calibre style) */
:root {
  --q-primary: #3a5874;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
  font-size: 12px !important;
  background-color: #ececec !important;
  color: #222222 !important;
}
/* Toolbar */
.desktop-toolbar {
  background-color: #e4e4e4 !important;
  border-bottom: 1px solid #b8b8b8 !important;
  color: #222222 !important;
  height: 38px !important;
  min-height: 38px !important;
  padding: 0 12px !important;
  box-shadow: none !important;
}
/* Sidebar drawer */
.desktop-drawer {
  background-color: #f4f4f4 !important;
  border-right: 1px solid #c2c2c2 !important;
}
/* Quasar input overrides for compact desktop density */
.q-field--dense .q-field__control {
  height: 26px !important;
  min-height: 26px !important;
  max-height: 26px !important;
  padding: 0 6px !important;
  border-radius: 2px !important;
  background-color: #ffffff !important;
  display: flex !important;
  align-items: center !important;
  box-sizing: border-box !important;
}
.q-field__control-container {
  height: 100% !important;
  min-height: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
}
.q-field--dense .q-field__marginal {
  height: 100% !important;
  min-height: 100% !important;
  display: flex !important;
  align-items: center !important;
  padding: 0 2px !important;
}
.q-field--dense .q-field__marginal .q-icon {
  font-size: 14px !important;
  line-height: 1 !important;
}
.q-field--outlined .q-field__control:before {
  border-color: #b0b0b0 !important;
  border-radius: 2px !important;
}
.q-field--outlined:hover .q-field__control:before {
  border-color: #707070 !important;
}
.q-field--focused .q-field__control:before {
  border-color: #3a5874 !important;
  border-width: 1px !important;
}
.q-field__native, .q-field__input {
  font-size: 12px !important;
  color: #222222 !important;
  padding: 0 2px !important;
  margin: 0 !important;
  height: 100% !important;
  min-height: 100% !important;
  box-sizing: border-box !important;
}
input.q-field__native {
  height: 100% !important;
  line-height: normal !important;
  padding: 0 2px 2px 2px !important;
  margin: 0 !important;
}
/* Center dropdown text vertically and prevent overflow */
.desktop-drawer .q-field,
.desktop-drawer .q-select {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
.desktop-drawer .q-field__control {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
.desktop-drawer .q-field__control-container {
  min-width: 0 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
}
.desktop-toolbar .q-field,
.desktop-toolbar .q-select {
  width: 85px !important;
  max-width: 85px !important;
  min-width: 85px !important;
  box-sizing: border-box !important;
}
.q-select .q-field__native {
  height: 100% !important;
  min-height: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  padding: 0 2px !important;
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.q-select .q-field__native > span {
  display: inline-flex !important;
  align-items: center !important;
  line-height: normal !important;
  height: 100% !important;
  padding-bottom: 2px !important;
  margin: 0 !important;
  min-width: 0 !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
/* Compact dropdown popup menu items */
.q-menu .q-item {
  min-height: 24px !important;
  height: 24px !important;
  padding: 2px 8px !important;
  font-size: 12px !important;
}
.q-menu .q-item__section {
  min-height: 24px !important;
}
/* Hide Quasar internal floating labels completely */
.q-field__label {
  display: none !important;
}
/* Completely remove all transitions, animations, and ripples from inputs and buttons */
.q-btn,
.q-btn *,
.desktop-btn,
.desktop-btn *,
.q-field,
.q-field *,
.q-field__control,
.q-field__control:before,
.q-field__control:after,
.q-field__native,
.q-field__input,
.q-select,
.q-select *,
.q-menu,
.q-menu * {
  transition: none !important;
  animation: none !important;
}
.q-ripple {
  display: none !important;
}
/* Remove shadows from tab selection and button groups */
.q-tabs,
.q-tab,
.q-btn-group,
.q-btn-toggle,
.q-btn-group *,
.q-btn-toggle * {
  box-shadow: none !important;
}
/* Desktop Buttons */
.desktop-btn {
  background: linear-gradient(to bottom, #ffffff, #e6e6e6) !important;
  border: 1px solid #ababab !important;
  border-radius: 2px !important;
  color: #222222 !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  padding: 3px 10px !important;
  min-height: 25px !important;
  box-shadow: 0 1px 1px rgba(0,0,0,0.06) !important;
  text-transform: none !important;
}
.desktop-btn:hover {
  background: linear-gradient(to bottom, #f5f5f5, #dadada) !important;
  border-color: #888888 !important;
}
.desktop-btn-primary {
  background: linear-gradient(to bottom, #4a6f91, #335372) !important;
  border: 1px solid #233b52 !important;
  color: #ffffff !important;
}
.desktop-btn-primary:hover {
  background: linear-gradient(to bottom, #547da3, #3b5f82) !important;
}
/* Desktop Group Container */
.desktop-group {
  background-color: #fdfdfd;
  border: 1px solid #d0d0d0;
  border-radius: 2px;
  padding: 8px 10px;
  margin-bottom: 8px;
}
.desktop-group-title {
  font-size: 11px;
  font-weight: 700;
  color: #4a4a4a;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  border-bottom: 1px solid #e8e8e8;
  padding-bottom: 3px;
}
/* Main panel for charts */
.desktop-panel {
  background-color: #ffffff;
  border: 1px solid #c8c8c8;
  border-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  width: 100% !important;
  box-sizing: border-box !important;
}
/* Page container & Scrolling */
.q-page-container {
  height: calc(100vh - 38px) !important;
  overflow: hidden !important;
  display: flex !important;
  width: 100% !important;
}
.q-page {
  display: flex !important;
  flex-direction: column !important;
  width: 100% !important;
  height: 100% !important;
  padding: 0 !important;
  min-height: 0 !important;
  overflow: hidden !important;
  align-items: stretch !important;
}
.nicegui-content {
  width: 100% !important;
  height: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  flex: 1 1 0% !important;
  min-height: 0 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
}
.charts-scroll-container {
  flex: 1 1 0% !important;
  min-height: 0 !important;
  height: 100% !important;
  width: 100% !important;
  overflow-y: scroll !important;
  overflow-x: hidden !important;
  -webkit-overflow-scrolling: touch;
  padding: 12px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  gap: 12px !important;
  box-sizing: border-box !important;
}
</style>
"""
    )

    # Top Toolbar
    with ui.header().classes("desktop-toolbar flex items-center justify-between no-wrap"):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label("When Can I Retire?").classes("font-bold text-xs tracking-tight")
            ui.label("|").classes("text-gray-400 mx-1")
            ui.label("Tax Year:").classes("text-xs text-gray-700")

            def on_year_change(e):
                app_state.set_year(e.value)
                render_config_form()
                update_charts()
                ui.notify(
                    f"Switched to Tax Year {e.value}", type="info", position="top"
                )

            ui.select(
                options=app_state.get_available_years(),
                value=app_state.current_year,
                on_change=on_year_change,
            ).props("dense outlined options-dense").classes("w-20 bg-white")

        with ui.row().classes("items-center gap-2 no-wrap"):

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

            ui.button("Save & Calculate", on_click=save_and_calculate).classes(
                "desktop-btn desktop-btn-primary"
            )

    # Left Drawer (Form inputs)
    with ui.left_drawer(value=True).classes("desktop-drawer p-3 overflow-y-auto").style(
        "width: 400px;"
    ):
        form_container = ui.column().classes("w-full gap-2")

        def render_config_form():
            form_container.clear()
            with form_container:
                # Personal Information Group
                with ui.element("div").classes("desktop-group w-full"):
                    ui.label("Personal Information").classes("desktop-group-title")

                    with ui.grid(columns=2).classes("w-full gap-2 min-w-0"):
                        with ui.column().classes("gap-0.5 w-full min-w-0"):
                            ui.label("Current Age").classes(
                                "text-[11px] text-gray-700 font-medium"
                            )
                            ui.number(
                                value=app_state.person_schema.current_age,
                                on_change=lambda e: setattr(
                                    app_state.person_schema,
                                    "current_age",
                                    int(e.value or 0),
                                ),
                            ).props("dense outlined").classes("w-full")

                        with ui.column().classes("gap-0.5 w-full min-w-0"):
                            ui.label("Retirement Age").classes(
                                "text-[11px] text-gray-700 font-medium"
                            )
                            ui.number(
                                value=app_state.person_schema.retirement_age,
                                on_change=lambda e: setattr(
                                    app_state.person_schema,
                                    "retirement_age",
                                    int(e.value or 0),
                                ),
                            ).props("dense outlined").classes("w-full")

                        with ui.column().classes("gap-0.5 w-full min-w-0"):
                            ui.label("Lifespan").classes(
                                "text-[11px] text-gray-700 font-medium"
                            )
                            ui.number(
                                value=app_state.person_schema.lifespan,
                                on_change=lambda e: setattr(
                                    app_state.person_schema,
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
                                value=app_state.person_schema.filing,
                                on_change=lambda e: setattr(
                                    app_state.person_schema, "filing", e.value
                                ),
                            ).props("dense outlined options-dense").classes("w-full")

                    with ui.column().classes("w-full gap-0.5 mt-2"):
                        ui.label("Pre-tax Income ($)").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.number(
                            value=float(app_state.person_schema.pre_tax_income),
                            format="%.2f",
                            on_change=lambda e: setattr(
                                app_state.person_schema,
                                "pre_tax_income",
                                Decimal(str(e.value or 0)),
                            ),
                        ).props("dense outlined").classes("w-full")

                    with ui.column().classes("w-full gap-0.5 mt-1.5"):
                        ui.label("Additional Tax Deductions ($)").classes(
                            "text-[11px] text-gray-700 font-medium"
                        )
                        ui.number(
                            value=float(
                                app_state.person_schema.additional_income_tax_deductions
                            ),
                            format="%.2f",
                            on_change=lambda e: setattr(
                                app_state.person_schema,
                                "additional_income_tax_deductions",
                                Decimal(str(e.value or 0)),
                            ),
                        ).props("dense outlined").classes("w-full")

                    with ui.grid(columns=2).classes("w-full gap-2 mt-2 min-w-0"):
                        with ui.column().classes("gap-0.5 w-full min-w-0"):
                            ui.label("State").classes(
                                "text-[11px] text-gray-700 font-medium"
                            )

                            def on_state_change(e):
                                val = (
                                    None
                                    if (e.value is None or e.value == "(None)")
                                    else e.value
                                )
                                setattr(app_state.person_schema, "state_of_residence", val)

                            ui.select(
                                ["(None)"] + [e.value for e in State],
                                value=(
                                    app_state.person_schema.state_of_residence
                                    if app_state.person_schema.state_of_residence
                                    else "(None)"
                                ),
                                on_change=on_state_change,
                            ).props("dense outlined options-dense clearable").classes("w-full")

                        with ui.column().classes("gap-0.5 w-full min-w-0"):
                            ui.label("City").classes(
                                "text-[11px] text-gray-700 font-medium"
                            )

                            def on_city_change(e):
                                val = (
                                    None
                                    if (e.value is None or e.value == "(None)")
                                    else e.value
                                )
                                setattr(app_state.person_schema, "city_of_residence", val)

                            ui.select(
                                ["(None)"] + [e.value for e in City],
                                value=(
                                    app_state.person_schema.city_of_residence
                                    if app_state.person_schema.city_of_residence
                                    else "(None)"
                                ),
                                on_change=on_city_change,
                            ).props("dense outlined options-dense clearable").classes("w-full")

                # Expenses Group
                with ui.element("div").classes("desktop-group w-full"):
                    with ui.row().classes("items-center justify-between w-full mb-1"):
                        ui.label("Accumulation Expenses").classes(
                            "desktop-group-title mb-0"
                        )

                        def add_expense():
                            app_state.person_schema.Expenses.append(
                                ExpenseSchema(
                                    name="New Expense",
                                    expense=Decimal("0.00"),
                                    frequency=Frequency.MONTHLY,
                                )
                            )
                            render_config_form()

                        ui.button("+ Add", on_click=add_expense).classes(
                            "desktop-btn text-xs py-0 px-2"
                        )

                    for i, exp in enumerate(app_state.person_schema.Expenses):
                        with ui.element("div").classes(
                            "border border-gray-300 bg-white p-2 mb-2 rounded-sm"
                        ):
                            with ui.row().classes(
                                "items-center justify-between w-full mb-1"
                            ):
                                ui.label("Expense Name").classes(
                                    "text-[11px] text-gray-700 font-medium"
                                )

                                def remove_expense(idx: int):
                                    app_state.person_schema.Expenses.pop(idx)
                                    render_config_form()

                                ui.button(
                                    "✕ Remove",
                                    on_click=lambda _, idx=i: remove_expense(idx),
                                ).props("dense flat").classes(
                                    "text-red-700 text-xs p-0 h-5"
                                )

                            ui.input(
                                value=exp.name,
                                on_change=lambda e, idx=i: setattr(
                                    app_state.person_schema.Expenses[idx],
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
                                            app_state.person_schema.Expenses[idx],
                                            "expense",
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
                                        value=exp.frequency,
                                        on_change=lambda e, idx=i: setattr(
                                            app_state.person_schema.Expenses[idx],
                                            "frequency",
                                            e.value,
                                        ),
                                    ).props("dense outlined options-dense").classes(
                                        "w-full"
                                    )

                # Accounts Group
                with ui.element("div").classes("desktop-group w-full"):
                    with ui.row().classes("items-center justify-between w-full mb-1"):
                        ui.label("Investment Accounts").classes(
                            "desktop-group-title mb-0"
                        )

                        def add_account():
                            name = f"Account {len(app_state.person_schema.Accounts) + 1}"
                            app_state.person_schema.Accounts[name] = AccountSchema()
                            render_config_form()

                        ui.button("+ Add", on_click=add_account).classes(
                            "desktop-btn text-xs py-0 px-2"
                        )

                    for acc_name, acc in list(
                        app_state.person_schema.Accounts.items()
                    ):
                        with ui.element("div").classes(
                            "border border-gray-300 bg-white p-2 mb-2 rounded-sm"
                        ):
                            with ui.row().classes(
                                "items-center justify-between w-full mb-1"
                            ):
                                ui.label(acc_name).classes(
                                    "font-semibold text-xs text-gray-800"
                                )

                                def remove_account(name: str):
                                    del app_state.person_schema.Accounts[name]
                                    render_config_form()

                                ui.button(
                                    "✕ Remove",
                                    on_click=lambda _, name=acc_name: remove_account(
                                        name
                                    ),
                                ).props("dense flat").classes(
                                    "text-red-700 text-xs p-0 h-5"
                                )

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
                                            app_state.person_schema.Accounts[name],
                                            "account_type",
                                            e.value,
                                        ),
                                    ).props("dense outlined options-dense").classes(
                                        "w-full"
                                    )

                                with ui.column().classes("gap-0.5 w-full min-w-0"):
                                    ui.label("Initial ($)").classes(
                                        "text-[11px] text-gray-700 font-medium"
                                    )
                                    ui.number(
                                        value=float(acc.initial_savings),
                                        format="%.2f",
                                        on_change=lambda e, name=acc_name: setattr(
                                            app_state.person_schema.Accounts[name],
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
                                            app_state.person_schema.Accounts[name],
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
                                            app_state.person_schema.Accounts[name],
                                            "regular_investment_frequency",
                                            e.value,
                                        ),
                                    ).props("dense outlined options-dense").classes(
                                        "w-full"
                                    )

                # Bottom Save Button in sidebar
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
                    budget_chart.style(
                        "width: 100%; height: 440px; min-height: 440px;"
                    )
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

                ui.timer(0.05, lambda: budget_chart.run_chart_method("resize"), once=True)
                ui.timer(0.05, lambda: retirement_chart.run_chart_method("resize"), once=True)

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

    def update_charts():
        budget_chart.options.clear()
        budget_chart.options.update(
            get_budget_pie_chart_options(app_state.user, app_state.config)
        )
        budget_chart.update()
        ui.timer(0.05, lambda: budget_chart.run_chart_method("resize"), once=True)

        retirement_chart.options.clear()
        retirement_chart.options.update(
            get_retirement_line_chart_options(app_state.user, app_state.config)
        )
        retirement_chart.update()
        ui.timer(0.05, lambda: retirement_chart.run_chart_method("resize"), once=True)

    # Initial resize after window mount
    ui.timer(0.1, lambda: budget_chart.run_chart_method("resize"), once=True)
    ui.timer(0.1, lambda: retirement_chart.run_chart_method("resize"), once=True)
