from dataclasses import dataclass
from datetime import datetime
from typing import Literal


OperationType = Literal["expense", "transfer"]
RowType = Literal["debit", "credit"]


@dataclass
class Operation:
    date: datetime
    id: str                # UUID
    operation_type: OperationType
    person_id: str         # кто регистрирует
    is_expense: bool       # True, если это строка затрат
    category: str
    comment: str
    amount: float
    active: bool = True


@dataclass
class OperationRow:
    date: datetime
    operation_id: str      # UUID родительской операции
    person_id: str
    category: str
    row_type: RowType      # "debit" или "credit"
    amount: float
    active: bool = True
