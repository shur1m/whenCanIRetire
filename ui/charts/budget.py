from decimal import Decimal

from calculate.aggregate import (
    calculate_income_distribution_data,
    calculate_retirement_deductions_excess,
)
from utils.globals import GlobalParameters
from utils.parameters import Person


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
