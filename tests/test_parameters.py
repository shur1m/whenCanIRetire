"""
Regression tests for utils/parameters.py

Covers Person and Account model behaviors:
  - get_reduced_income (deductions from Traditional/HSA accounts)
  - get_fica_taxable_income (HSA reduces FICA, 401k does not)
  - add_account validation (owner check, duplicate names)
  - income_tax_deductions accumulation
  - add_accumulation_expense (monthly vs annual normalization)
"""

import pytest
from utils.parameters import Person, Account
from utils.enums import Frequency, AccountType

# ===========================================================================
# Person.get_reduced_income
# ===========================================================================


class TestGetReducedIncome:
    def test_no_deductions_returns_full_income(self):
        user = Person(pre_tax_income=100_000)
        assert user.get_reduced_income() == 100_000

    def test_traditional_monthly_reduces_income(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "401k",
            regular_investment_dollar=1_000,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.TRADITIONAL,
        )
        # $1,000/month × 12 = $12,000 deduction
        assert user.get_reduced_income() == 88_000

    def test_traditional_annual_reduces_income(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "401k",
            regular_investment_dollar=12_000,
            regular_investment_frequency=Frequency.ANNUALLY,
            account_type=AccountType.TRADITIONAL,
        )
        assert user.get_reduced_income() == 88_000

    def test_hsa_monthly_reduces_income(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "HSA",
            regular_investment_dollar=250,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.HSA,
        )
        # $250/month × 12 = $3,000
        assert user.get_reduced_income() == 97_000

    def test_roth_does_not_reduce_income(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "Roth",
            regular_investment_dollar=500,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.ROTH,
        )
        assert user.get_reduced_income() == 100_000

    def test_generic_does_not_reduce_income(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "Brokerage",
            regular_investment_dollar=500,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.GENERIC,
        )
        assert user.get_reduced_income() == 100_000

    def test_multiple_deductible_accounts_stack(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "401k",
            regular_investment_dollar=1_000,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.TRADITIONAL,
        )
        user.create_account(
            "HSA",
            regular_investment_dollar=250,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.HSA,
        )
        # 12,000 + 3,000 = 15,000 deduction
        assert user.get_reduced_income() == 85_000

    def test_additional_income_tax_deductions_parameter(self):
        user = Person(
            pre_tax_income=100_000,
            additional_income_tax_deductions=5_000,
        )
        assert user.get_reduced_income() == 95_000


# ===========================================================================
# Person.get_fica_taxable_income
# ===========================================================================


class TestGetFicaTaxableIncome:
    def test_no_accounts_full_income(self):
        user = Person(pre_tax_income=100_000)
        assert user.get_fica_taxable_income() == 100_000

    def test_hsa_monthly_reduces_fica(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "HSA",
            regular_investment_dollar=250,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.HSA,
        )
        # $250 × 12 = $3,000 reduction
        assert user.get_fica_taxable_income() == 97_000

    def test_hsa_annual_reduces_fica(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "HSA",
            regular_investment_dollar=3_000,
            regular_investment_frequency=Frequency.ANNUALLY,
            account_type=AccountType.HSA,
        )
        assert user.get_fica_taxable_income() == 97_000

    def test_traditional_401k_does_not_reduce_fica(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "401k",
            regular_investment_dollar=1_000,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.TRADITIONAL,
        )
        # FICA taxable income is NOT reduced by 401(k)
        assert user.get_fica_taxable_income() == 100_000

    def test_roth_does_not_reduce_fica(self):
        user = Person(pre_tax_income=100_000)
        user.create_account(
            "Roth",
            regular_investment_dollar=500,
            regular_investment_frequency=Frequency.MONTHLY,
            account_type=AccountType.ROTH,
        )
        assert user.get_fica_taxable_income() == 100_000


# ===========================================================================
# Person.add_account – validation
# ===========================================================================


class TestAddAccount:
    def test_wrong_owner_raises_value_error(self):
        user1 = Person(pre_tax_income=100_000)
        user2 = Person(pre_tax_income=80_000)
        account = Account(owner=user1)
        with pytest.raises(ValueError, match="owner"):
            user2.add_account(account)

    def test_duplicate_account_name_raises(self):
        user = Person(pre_tax_income=100_000)
        user.create_account("401k", account_type=AccountType.TRADITIONAL)
        with pytest.raises(Exception):
            user.create_account("401k", account_type=AccountType.ROTH)

    def test_auto_generated_name_is_unique(self):
        user = Person(pre_tax_income=100_000)
        a1 = user.create_account()
        a2 = user.create_account()
        names = list(user.accounts.keys())
        assert len(names) == len(set(names)), "Auto-generated names must be unique"

    def test_account_appears_in_accounts_dict(self):
        user = Person(pre_tax_income=100_000)
        user.create_account("myAccount", account_type=AccountType.ROTH)
        assert "myAccount" in user.accounts


# ===========================================================================
# Person.add_accumulation_expense
# ===========================================================================


class TestAddAccumulationExpense:
    def test_monthly_expense_stored_as_annual(self):
        user = Person(pre_tax_income=100_000)
        user.add_accumulation_expense("rent", 2_000, Frequency.MONTHLY)
        assert user.accumulation_phase_expenses["rent"] == 24_000

    def test_annual_expense_stored_as_is(self):
        user = Person(pre_tax_income=100_000)
        user.add_accumulation_expense("insurance", 3_600, Frequency.ANNUALLY)
        assert user.accumulation_phase_expenses["insurance"] == 3_600

    def test_multiple_expenses_are_independent(self):
        user = Person(pre_tax_income=100_000)
        user.add_accumulation_expense("rent", 2_000, Frequency.MONTHLY)
        user.add_accumulation_expense("car", 500, Frequency.MONTHLY)
        assert user.accumulation_phase_expenses["rent"] == 24_000
        assert user.accumulation_phase_expenses["car"] == 6_000
