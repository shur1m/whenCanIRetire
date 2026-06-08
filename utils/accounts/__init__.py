from utils.accounts.base import Account, to_decimal
from utils.accounts.traditional import TraditionalAccount
from utils.accounts.roth import RothAccount
from utils.accounts.hsa import HsaAccount
from utils.accounts.brokerage import BrokerageAccount
from utils.enums import AccountType


def _create_account(cls, *args, **kwargs) -> Account:
    """Dynamic factory method to instantiate the correct subclass based on account_type."""
    account_type = kwargs.get("account_type")
    if account_type is None and len(args) >= 12:
        account_type = args[11]
    if account_type is None:
        account_type = AccountType.GENERIC

    if account_type == AccountType.TRADITIONAL:
        return TraditionalAccount(*args, **kwargs)
    elif account_type == AccountType.ROTH:
        return RothAccount(*args, **kwargs)
    elif account_type == AccountType.HSA:
        return HsaAccount(*args, **kwargs)
    else:
        return BrokerageAccount(*args, **kwargs)


Account.create = classmethod(_create_account)  # type: ignore

__all__ = [
    "Account",
    "to_decimal",
    "TraditionalAccount",
    "RothAccount",
    "HsaAccount",
    "BrokerageAccount",
]
