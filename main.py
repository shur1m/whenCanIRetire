from decimal import Decimal
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import logging
import json

from calculate.aggregate import (
    calculate_income_distribution_data,
    calculate_retirement_deductions_excess,
)
from utils.parameters import Person
from utils.parse_parameters import parse_parameters
from utils.globals import GlobalParameters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_investment_growth_graph(user: Person, config: GlobalParameters, ax: Axes):
    # calculate and show retirement simulation
    total_savings_graph_labels = []
    total_savings_graph_values: list[Decimal] = []

    for account_name, account in user.accounts.items():
        graph_labels, graph_savings_values = account.simulate(config)
        float_savings_values = [float(v) for v in graph_savings_values]
        ax.plot(graph_labels, float_savings_values, label=account_name)

        if len(graph_labels) > len(total_savings_graph_labels):
            total_savings_graph_labels = graph_labels

        # add to total
        for i in range(len(graph_savings_values)):
            if i >= len(total_savings_graph_values):
                total_savings_graph_values.append(Decimal("0"))
            total_savings_graph_values[i] += graph_savings_values[i]

    yearly_retirement_expense = sum(
        [
            account.annual_retirement_post_tax_expense
            for account in user.accounts.values()
        ]
    )

    float_total_savings = [float(v) for v in total_savings_graph_values]
    ax.plot(total_savings_graph_labels, float_total_savings, label="Total Savings")
    ax.set_title("Retirement Savings", fontweight="semibold")
    ax.legend(loc="best")
    ax.set_xlabel(
        f"age (years)\nTotal yearly expense during retirement phase (today's dollars): ${yearly_retirement_expense:.2f}"
    )
    ax.set_ylabel("investment savings (dollars)")


def generate_income_distribution_graph(
    user: Person, config: GlobalParameters, ax: Axes
):
    # Retrieve decoupled income distribution data
    pie_data = calculate_income_distribution_data(user, config)

    pie_labels = list(pie_data.keys())
    pie_sizes = list(pie_data.values())

    # Calculate user_tax to find tax savings excess
    user_tax = (
        pie_data.get("Federal Income tax", Decimal("0"))
        + pie_data.get("Medicare Tax", Decimal("0"))
        + pie_data.get("Social Security Tax", Decimal("0"))
        + pie_data.get("State Tax", Decimal("0"))
    )

    retirement_deductions_excess = calculate_retirement_deductions_excess(
        user, config, user_tax
    )

    def autopct_format(values):
        def percent_and_dollar_value(pct):
            total = sum(values)
            val = Decimal(str(pct)) / Decimal("100") * total
            return "{:.2f}% (${:.2f})".format(pct, val)

        return percent_and_dollar_value

    ax.pie(
        [float(size) for size in pie_sizes],
        labels=pie_labels,
        autopct=autopct_format(pie_sizes),
        explode=[0.02 for _ in range(len(pie_sizes))],
    )
    ax.set_title("Annual Spending", fontweight="semibold")
    ax.text(
        -1.2,
        -1.5,
        f"Total: ${sum(pie_sizes):.2f}\nTaxes saved by retirement accounts: ${retirement_deductions_excess:.2f}",
        fontstyle="italic",
    )

    pie_sizes_map = {name: float(size) for (name, size) in zip(pie_labels, pie_sizes)}
    logger.info(f"Pie Sizes: {json.dumps(pie_sizes_map, indent=4)}")


def main():
    user, config = parse_parameters()

    # TODO company match, needs to be changed so that contribution does not subtract from pay
    # HSA company match
    # user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
    #                     regular_investment_dollar=500/12,
    #                     annual_investment_increase=0.02,
    #                     account_type=AccountType.HSA,
    #                     annual_retirement_post_tax_expense=16_000), "HSA company match")

    fig, (ax1, ax2) = plt.subplots(1, 2)  # type: ignore
    generate_investment_growth_graph(user, config, ax1)
    generate_income_distribution_graph(user, config, ax2)
    plt.show()


if __name__ == "__main__":
    main()
