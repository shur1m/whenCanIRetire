from pydantic import BaseModel, Field, RootModel, model_validator
from typing import Dict, List, Optional
from decimal import Decimal
from utils.enums import Filing, Frequency, AccountType, State, MonthlyCompoundType


class ExpenseSchema(BaseModel):
    name: str
    expense: Decimal
    frequency: Frequency


class AccountSchema(BaseModel):
    account_type: AccountType = AccountType.GENERIC
    regular_investment_frequency: Frequency = Frequency.MONTHLY
    initial_savings: Decimal = Decimal("0")
    regular_investment_dollar: Decimal = Decimal("0")
    annual_investment_increase: Decimal = Decimal("0")
    annual_investment_return: Decimal = Decimal("0.07")
    annual_retirement_return: Decimal = Decimal("0.05")
    annual_retirement_post_tax_expense: Decimal = Decimal("72000")
    compound_frequency: Frequency = Frequency.MONTHLY
    compound_type: MonthlyCompoundType = MonthlyCompoundType.ROOT


class PersonSchema(BaseModel):
    current_age: int = 22
    retirement_age: int = 65
    lifespan: int = 120
    pre_tax_income: Decimal = Decimal("115000")
    additional_income_tax_deductions: Decimal = Decimal("0")
    state_of_residence: Optional[State] = None
    filing: Filing = Filing.INDIVIDUAL
    Accounts: Dict[str, AccountSchema] = Field(default_factory=dict)
    Expenses: List[ExpenseSchema] = Field(default_factory=list)


class YearlyConfigSchema(BaseModel):
    Person: PersonSchema


class ParametersSchema(BaseModel):
    CurrentYear: int
    years: Dict[str, YearlyConfigSchema] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_years(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        current_year = data.get("CurrentYear")
        years_dict = {}
        for k, v in data.items():
            if k == "CurrentYear":
                continue
            years_dict[k] = v
        return {"CurrentYear": current_year, "years": years_dict}


class TaxBracketSchema(BaseModel):
    LowerBounds: List[Decimal]
    Percents: List[Decimal]


class FederalTaxSchema(BaseModel):
    Individual: TaxBracketSchema
    Joint: TaxBracketSchema
    StandardTaxDeduction: Decimal
    JointTaxDeduction: Decimal


class StateTaxSchema(BaseModel):
    Individual: TaxBracketSchema
    Joint: TaxBracketSchema
    StandardTaxDeduction: Decimal
    JointTaxDeduction: Decimal
    SDITaxPercent: Optional[Decimal] = None
    MHSTaxPercent: Optional[Decimal] = None
    MHSTaxThreshold: Optional[Decimal] = None


class FicaTaxSchema(BaseModel):
    SocialSecurityMaxTaxable: Decimal
    SocialSecurityTaxPercent: Decimal
    MedicareHighEarnerTax: Decimal
    MedicareHighEarnerSalaryIndividual: Decimal
    MedicareHighEarnerSalaryJoint: Decimal
    MedicareTaxPercent: Decimal


class YearlyTaxSchema(BaseModel):
    InflationRate: Decimal = Decimal("0.03")
    FederalTax: FederalTaxSchema
    StateTax: Dict[State, StateTaxSchema] = Field(default_factory=dict)
    FicaTax: FicaTaxSchema


class TaxSchema(RootModel[Dict[str, YearlyTaxSchema]]):
    pass
