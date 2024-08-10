from utils.calc import calculate_annual_income_tax, calculate_pre_tax_income, simulate_account, calculate_annual_federal_income_tax, calculate_annual_social_security_tax, calculate_annual_medicare_tax
from utils.enums import AccountType, Filing, Frequency, MonthlyCompoundType
from utils.parameters import Account, Person
from utils.globals import GlobalParameters
import matplotlib.pyplot as plt

user = Person(pre_tax_income=115_000, retirement_age=65, lifespan=150)
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=1600,
                         annual_investment_increase=0.02,
                         account_type= AccountType.ROTH,
                         annual_retirement_post_tax_expense=50_000,
                         ))
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=1600,
                         annual_investment_increase=0.02,
                         account_type= AccountType.TRADITIONAL,
                         annual_retirement_post_tax_expense=50_000,
                         ))

fig, (ax1, ax2) = plt.subplots(1, 2)

# calculate and show retirement simulation
for account_name, account in user.accounts.items():
    graph_labels, graph_savings_values = simulate_account(user.accounts[account_name])
    ax1.plot(graph_labels, graph_savings_values, label=account_name)

ax1.set_title('Retirement Savings')
ax1.legend(loc='best')
ax1.set_xlabel('age (years)')
ax1.set_ylabel('investment savings (dollars)')

# calculate and show income pie chart
taxes_owed = calculate_annual_income_tax(user)
remaining_income = user.pre_tax_income  - taxes_owed #including 401k contributions

def autopct_format(values):
    def percent_and_dollar_value(pct):
        total = sum(values)
        val = pct/100 * total
        return '{:.1f}% (${:.2f})'.format(pct, val)
    return percent_and_dollar_value

pie_labels = 'Federal Income tax', 'Medicare Tax', 'Social Security Tax', 'Remaining Income'
pie_sizes = [calculate_annual_federal_income_tax(user), calculate_annual_medicare_tax(user), calculate_annual_social_security_tax(user), remaining_income]
ax2.pie(pie_sizes, labels=pie_labels, autopct=autopct_format(pie_sizes))
ax2.set_title('Annual Spending')
plt.show()


# ! add investment contributions (401k, roth... all accounts) to pie chart (part of post tax income)
# ! allow user to add fixed costs, savings, other categories to split post_tax_income