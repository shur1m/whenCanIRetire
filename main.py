from utils.calc import calculate_annual_income_tax, calculate_annual_state_income_tax, calculate_pre_tax_income, simulate_account, calculate_annual_federal_income_tax, calculate_annual_social_security_tax, calculate_annual_medicare_tax
from utils.enums import AccountType, Filing, Frequency, MonthlyCompoundType, State
from utils.parameters import Account, Person
from utils.globals import GlobalParameters
import matplotlib.pyplot as plt

user = Person(pre_tax_income=115_000, retirement_age=65, lifespan=120, filing=Filing.INDIVIDUAL, state_of_residence=State.TEXAS)
user.add_accumulation_expense('fixed costs', 2_475.07*1.15, Frequency.MONTHLY)
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=23000/12,
                         annual_investment_increase=0.02,
                         account_type= AccountType.TRADITIONAL,
                         annual_retirement_post_tax_expense=70_000), "401(k)")
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=4150/12,
                         annual_investment_increase=0.02,
                         account_type= AccountType.TRADITIONAL,
                         annual_retirement_post_tax_expense=14_500), "HSA")
# user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
#                          regular_investment_dollar=7000/12,
#                          annual_investment_increase=0.02,
#                          account_type= AccountType.ROTH,
#                          annual_retirement_post_tax_expense=27_000), "ROTH")

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
# add taxes
pie_labels = ['Federal Income tax', 'Medicare Tax', 'Social Security Tax']
pie_sizes = [calculate_annual_federal_income_tax(user), calculate_annual_medicare_tax(user), calculate_annual_social_security_tax(user)]

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

handles, texts, autopcts = ax2.pie(pie_sizes, labels=pie_labels, autopct=autopct_format(pie_sizes), explode=[0.02 for _ in range(len(pie_sizes))])
ax2.set_title('Annual Spending', fontweight='semibold')
ax2.text(-1.2, -1.5,f'Total: ${sum(pie_sizes):.2f}', fontstyle='italic')
# plt.setp(autopcts, fontsize=5)
plt.show()

print([(name, size) for (name,size) in zip(pie_labels, pie_sizes)])

# ! show how much money withdrawn from each account during retirement phase
# ! automatically calculate retirement expense to end at life expectancy
# ! hsa account (hsa not subject to fica or income tax, can be subject to taxes if withdrawn after 65 to be used on normal stuff)
# ! allow user to set timespan during the accumulation phase where they are contributing
#  - (useful for hsa where only young people can contribute because they are healthy)
# ! allow user to set timespan during retirement phase where they are withdrawing
# ! nice to have: ui and dynamic changes, options for bankers rounding vs normal rounding to whole numbers