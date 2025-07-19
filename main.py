from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import copy
import logging

from calculate.tax import calculate_annual_income_tax, calculate_annual_state_income_tax, calculate_annual_federal_income_tax, calculate_annual_social_security_tax, calculate_annual_medicare_tax
from calculate.retirement import simulate_account
from utils.enums import Frequency
from utils.parameters import Person
from utils.globals import GlobalParameters
from utils.parse_parameters import parse_parameters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_investment_growth_graph(user: Person, ax: Axes):
    # calculate and show retirement simulation
    total_savings_graph_labels = []
    total_savings_graph_values = []

    for account_name, account in user.accounts.items():
        graph_labels, graph_savings_values = simulate_account(account)
        ax.plot(graph_labels, graph_savings_values, label=account_name)
        
        if len(graph_labels) > len(total_savings_graph_labels):
            total_savings_graph_labels = graph_labels

        # add to total
        for i in range(len(graph_savings_values)):
            if i >= len(total_savings_graph_values):
                total_savings_graph_values.append(0)
            total_savings_graph_values[i] += graph_savings_values[i]

    yearly_retirement_expense = sum([account.annual_retirement_post_tax_expense for account in user.accounts.values()])

    ax.plot(total_savings_graph_labels, total_savings_graph_values, label='Total Savings')
    ax.set_title('Retirement Savings', fontweight='semibold')
    ax.legend(loc='best')
    ax.set_xlabel(f"age (years)\nTotal yearly expense during retirement phase (today's dollars): ${yearly_retirement_expense:.2f}")
    ax.set_ylabel('investment savings (dollars)')

def generate_income_distribution_graph(user: Person, ax: Axes):
    # calculate and show income pie chart
    # add taxes
    pie_labels = ['Federal Income tax', 'Medicare Tax', 'Social Security Tax']
    pie_sizes = [
        calculate_annual_federal_income_tax(user),
        calculate_annual_medicare_tax(user),
        calculate_annual_social_security_tax(user)
    ]

    if calculate_annual_state_income_tax(user) > 0:
        pie_labels.append('State Tax')
        pie_sizes.append(calculate_annual_state_income_tax(user))

    # add account contributions
    for account_name, account in user.accounts.items():
        retirement_contributions: int

        if account.regular_investment_frequency == Frequency.MONTHLY:
            retirement_contributions = account.regular_investment_dollar * 12
        elif account.regular_investment_frequency == Frequency.ANNUALLY:
            retirement_contributions = account.regular_investment_dollar

        pie_labels.append(account_name + ' contribution')
        pie_sizes.append(retirement_contributions)

    # add other expenses
    for expense_name, expense in user.accumulation_phase_expenses.items():
        pie_labels.append(expense_name)
        pie_sizes.append(expense)

    remaining_income = user.pre_tax_income  - sum(pie_sizes) # annual value including 401k contributions
    pie_labels.append('Remaining Income')
    pie_sizes.append(remaining_income)

    def autopct_format(values):
        def percent_and_dollar_value(pct):
            total = sum(values)
            val = pct/100 * total
            return '{:.2f}% (${:.2f})'.format(pct, val)
        return percent_and_dollar_value


    # calculate post tax income  without 401k/hsa deductions
    no_deduction_user = copy.copy(user)
    no_deduction_user.accounts = dict()
    no_deduction_user.income_tax_deductions = 0
    retirement_deductions_excess = calculate_annual_income_tax(no_deduction_user) - calculate_annual_income_tax(user)
    
    ax.pie(pie_sizes, labels=pie_labels, autopct=autopct_format(pie_sizes), explode=[0.02 for _ in range(len(pie_sizes))])
    ax.set_title('Annual Spending', fontweight='semibold')
    ax.text(-1.2, -1.5,f'Total: ${sum(pie_sizes):.2f}\nTaxes saved by retirement accounts: ${retirement_deductions_excess:.2f}', fontstyle='italic')

    logger.info(f"Pie Sizes: {[(name, size) for (name,size) in zip(pie_labels, pie_sizes)]}")

def main():
    user = parse_parameters()
    GlobalParameters.configure(2024, user)
    
    # TODO company match, needs to be changed so that contribution does not subtract from pay
    # HSA company match
    # user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
    #                     regular_investment_dollar=500/12,
    #                     annual_investment_increase=0.02,
    #                     account_type=AccountType.HSA,
    #                     annual_retirement_post_tax_expense=16_000), "HSA company match")

    fig, (ax1, ax2) = plt.subplots(1, 2)
    generate_investment_growth_graph(user, ax1)
    generate_income_distribution_graph(user, ax2)
    plt.show()

if __name__ == "__main__":
    main()

# ! calculate how much to withdraw each year from account in order to end at the death age
#   - should be a toggle in account T/F
# ! allow company contributions to retirement accounts to not affect your total money in pie chart
# ! allow users to compare two different plans for investment in one run
# ! add toggle for post tax income, so that tax is not calculated
# ! add toggle for company matches that does not subtract from pay, also add another text for company match total. Company match should not show up in pie. 
# ! show how much money withdrawn from each account during retirement phase
# ! calculate total money spent (post tax income during accumulation + post tax withdrawal during retirement)
# ! automatically calculate retirement expense to end at life expectancy
# ! allow user to set timespan during the accumulation phase where they are contributing
#  - (useful for hsa where only young people can contribute because they are healthy)
# ! allow user to set timespan during retirement phase where they are withdrawing
# ! nice to have: ui and dynamic changes, options for bankers rounding vs normal rounding to whole numbers