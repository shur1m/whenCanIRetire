import argparse
import logging
import json
from decimal import Decimal
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from calculate.aggregate import (
    calculate_income_distribution_data,
    calculate_retirement_deductions_excess,
)
from utils.parameters import Person
from utils.parse_parameters import parse_parameters
from utils.globals import GlobalParameters
from calculate.simulator import RetirementSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_investment_growth_graph(user: Person, config: GlobalParameters, ax: Axes):
    # calculate and show retirement simulation
    total_savings_graph_labels = []
    total_savings_graph_values: list[Decimal] = []

    simulator = RetirementSimulator(user, config)
    results = simulator.simulate()

    for account_name, (graph_labels, graph_savings_values) in results.items():
        float_savings_values = [float(v) for v in graph_savings_values]
        ax.plot(graph_labels, float_savings_values, label=account_name)

        if len(graph_labels) > len(total_savings_graph_labels):
            total_savings_graph_labels = graph_labels

        # add to total
        for i in range(len(graph_savings_values)):
            if i >= len(total_savings_graph_values):
                total_savings_graph_values.append(Decimal("0"))
            total_savings_graph_values[i] += graph_savings_values[i]

    yearly_retirement_expense = simulator.annual_retirement_expense
    logger.info(
        f"Calculated yearly retirement expense to reach lifespan: ${yearly_retirement_expense:,.2f}"
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
        + pie_data.get("Local Tax", Decimal("0"))
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


def run_matplotlib():
    user, config = parse_parameters()

    fig, (ax1, ax2) = plt.subplots(1, 2)  # type: ignore
    generate_investment_growth_graph(user, config, ax1)
    generate_income_distribution_graph(user, config, ax2)
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="whenCanIRetire Application")
    parser.add_argument(
        "--matplotlib",
        action="store_true",
        help="Run the application with the matplotlib UI instead of the NiceGUI desktop app",
    )
    args = parser.parse_args()

    if args.matplotlib:
        run_matplotlib()
    else:
        # Import inside the block so nicegui isn't loaded unnecessarily if running matplotlib
        import ui.app as app
        from nicegui import ui

        app.init_ui()
        ui.run(
            native=True,
            window_size=(1200, 800),
            title="When Can I Retire?",
            reload=False,
        )


if __name__ == "__main__":
    main()
