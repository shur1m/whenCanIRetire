from enum import Enum
class Frequency(Enum):
    MONTHLY = 1
    ANNUALLY = 2

class MonthlyCompoundType(Enum):
    DIVIDE = 1
    ROOT = 2

class AccountType(Enum):
    GENERIC = 1
    PRETAX = TRADITIONAL = 2
    ROTH = 3
    HSA = 4

class Filing(Enum):
    INDIVIDUAL = 1
    JOINT = 2

class State(Enum):
    TEXAS = 1
    CALIFORNIA = 2