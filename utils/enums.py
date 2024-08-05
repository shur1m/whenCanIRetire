from enum import Enum
class Frequency(Enum):
    MONTHLY = 1
    ANNUALLY = 2

class MonthlyCompoundType(Enum):
    DIVIDE = 1
    ROOT = 2