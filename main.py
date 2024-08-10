from utils.calc import calculate_annual_income_tax, calculate_pre_tax_income, simulate_account, calculate_annual_federal_income_tax, calculate_annual_social_security_tax, calculate_annual_medicare_tax
from utils.enums import AccountType, Filing, Frequency, MonthlyCompoundType
from utils.parameters import Account, Person
from utils.globals import GlobalParameters
import matplotlib.pyplot as plt

user = Person(pre_tax_income=115_000, retirement_age=65, lifespan=150)
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=23000/12,
                         annual_investment_increase=0.02,
                         account_type= AccountType.TRADITIONAL,
                         annual_retirement_post_tax_expense=50_000), "401(k)")
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=7000/12,
                         annual_investment_increase=0.02,
                         account_type= AccountType.ROTH,
                         annual_retirement_post_tax_expense=50_000), "ROTH")

fig, (ax1, ax2) = plt.subplots(1, 2)

# calculate and show retirement simulation
total_savings_graph_labels = []
total_savings_graph_values = []

for account_name, account in user.accounts.items():
    graph_labels, graph_savings_values = simulate_account(user.accounts[account_name])
    ax1.plot(graph_labels, graph_savings_values, label=account_name)
    
    if len(graph_labels) > len(total_savings_graph_labels):
        total_savings_graph_labels = graph_labels

    # add to total
    for i in range(len(graph_savings_values)):
        if i >= len(total_savings_graph_values):
            total_savings_graph_values.append(0)
        total_savings_graph_values[i] += graph_savings_values[i]

ax1.plot(total_savings_graph_labels, total_savings_graph_values, label='Total Savings')

ax1.set_title('Retirement Savings', fontweight='semibold')
ax1.legend(loc='best')
ax1.set_xlabel('age (years)')
ax1.set_ylabel('investment savings (dollars)')

# calculate and show income pie chart
pie_labels = ['Federal Income tax', 'Medicare Tax', 'Social Security Tax']
pie_sizes = [calculate_annual_federal_income_tax(user), calculate_annual_medicare_tax(user), calculate_annual_social_security_tax(user)]

for account_name, account in user.accounts.items():
    retirement_contributions: int

    if account.regular_investment_frequency == Frequency.MONTHLY:
        retirement_contributions = account.regular_investment_dollar * 12
    elif account.regular_investment_frequency == Frequency.ANNUALLY:
        retirement_contributions = account.regular_investment_dollar

    pie_labels.append(account_name + ' contribution')
    pie_sizes.append(retirement_contributions)

taxes_owed = calculate_annual_income_tax(user)
remaining_income = user.pre_tax_income  - sum(pie_sizes) # annual value including 401k contributions
pie_labels.append('Remaining Income')
pie_sizes.append(remaining_income)

def autopct_format(values):
    def percent_and_dollar_value(pct):
        total = sum(values)
        val = pct/100 * total
        return '{:.1f}% (${:.2f})'.format(pct, val)
    return percent_and_dollar_value

ax2.pie(pie_sizes, labels=pie_labels, autopct=autopct_format(pie_sizes))
ax2.set_title('Annual Spending', fontweight='semibold')
ax2.text(-1.2, -1.5,f'Total: ${sum(pie_sizes):.2f}', fontstyle='italic')
plt.show()

# ! allow user to add fixed costs, savings, other categories to split remaining costs