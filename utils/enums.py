from enum import Enum
class Frequency(str, Enum):
    MONTHLY = "monthly"
    ANNUALLY = "annually"

class MonthlyCompoundType(Enum):
    DIVIDE = 1
    ROOT = 2

class AccountType(str, Enum):
    GENERIC = "generic"
    PRETAX = TRADITIONAL = "traditional"
    ROTH = "roth"
    HSA = "hsa"

class Filing(str, Enum):
    INDIVIDUAL = "individual"
    JOINT = "joint"

class State(str, Enum):
    TEXAS = "Texas"
    CALIFORNIA = "California"