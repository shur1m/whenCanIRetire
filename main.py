from utils.calc import calculate_annual_income_tax, simulate_account, calculate_annual_federal_income_tax, calculate_annual_social_security_tax, calculate_annual_medicare_tax
from utils.enums import AccountType, Filing, Frequency, MonthlyCompoundType
from utils.parameters import Account, Person
from utils.globals import GlobalParameters
import matplotlib.pyplot as plt

user = Person(pre_tax_income=115_000, retirement_age=65, lifespan=150)
user.add_account(Account(regular_investment_frequency=Frequency.MONTHLY,
                         regular_investment_dollar=1600,
                         annual_investment_increase=0.02,
                         account_type= AccountType.GENERIC,
                         annual_retirement_expense=70_000,
                         ))

fig, (ax1, ax2) = plt.subplots(1, 2)

for account_name, account in user.accounts.items():
    graph_labels, graph_savings_values = simulate_account(user.accounts[account_name])
    ax1.plot(graph_labels, graph_savings_values, label=account_name)
    print(account_name)

ax1.set_title('Retirement Savings')
ax1.legend(loc='best')
ax1.set_xlabel('age (years)')
ax1.set_ylabel('investment savings (dollars)')

taxes_owed = calculate_annual_income_tax(user)
post_tax_income = user.pre_tax_income  - taxes_owed #including 401k contributions

labels = 'Federal Income tax', 'Medicare Tax', 'Social Security Tax', 'Post-tax income'
sizes = [calculate_annual_federal_income_tax(user), calculate_annual_medicare_tax(user), calculate_annual_social_security_tax(user), post_tax_income]
ax2.pie(sizes, labels=labels)
plt.show()

print(taxes_owed, post_tax_income)

# ! implement roth withdrawals vs 401k withdrawals given a post-tax retirement expense (retirement phase simulation)
#   - expense is currently subtracted as a pre-tax value adjusted for inflation
# ! add investment contributinos (401k and roth) to pie chart (part of post tax income)
# ! allow user to add fixed costs, savings, other categories to split post_tax_income