from typing import Tuple

from ui.charts.budget import get_budget_pie_chart_options
from ui.charts.retirement import get_retirement_line_chart_options
from utils.globals import GlobalParameters
from utils.parameters import Person


def compute_chart_options(user: Person, config: GlobalParameters) -> Tuple[dict, dict]:
    budget_options = get_budget_pie_chart_options(user, config)
    retirement_options = get_retirement_line_chart_options(user, config)
    return budget_options, retirement_options


__all__ = [
    "get_budget_pie_chart_options",
    "get_retirement_line_chart_options",
    "compute_chart_options",
]
