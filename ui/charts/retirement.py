from decimal import Decimal

from calculate.simulator import RetirementSimulator
from utils.globals import GlobalParameters
from utils.parameters import Person


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

    yearly_retirement_expense = float(simulator.annual_retirement_expense)
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
