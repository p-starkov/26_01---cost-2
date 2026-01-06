from dataclasses import dataclass
from datetime import datetime
import uuid

from domain.models.expenses import Operation, OperationRow
from domain.repositories import (
    IOperationRepository,
    IOperationRowRepository,
    IUserGroupRepository,
)


@dataclass
class ExpenseService:
    operation_repo: IOperationRepository
    operation_row_repo: IOperationRowRepository
    user_group_repo: IUserGroupRepository

    def create_expense_for_all(
        self,
        user_id: str,
        group_id: str,
        category: str,
        comment: str,
        amount: float,
    ) -> str:
        """
        Создать затрату типа 'expense' для всех участников группы.

        Правило:
        - у потратившего пользователя debit на всю сумму X;
        - у всех участников группы (включая его) credit на X / k,
          где k — количество участников группы.

        Возвращает:
        - UUID созданной операции.
        """
        now = datetime.now()
        op_id = str(uuid.uuid4())

        # 1. Основная операция
        op = Operation(
            date=now,
            id=op_id,
            operation_type="expense",
            person_id=user_id,
            category=category,
            comment=comment,
            amount=amount,
            active=True,
        )
        self.operation_repo.create(op)

        # 2. Список участников группы из userGroups
        links, _ = self.user_group_repo._read_all_rows()  # лучше сделать отдельный метод,
        # но пока можно использовать уже имеющийся вспомогательный метод.
        member_ids: list[str] = []
        for row in links:
            if not row:
                continue
            row_user_id = row[0].strip()
            row_group_id = row[1].strip().upper() if len(row) > 1 else ""
            if row_group_id == group_id.strip().upper():
                member_ids.append(row_user_id)

        if not member_ids:
            # На практике лучше бросить исключение, здесь просто вернём id операции
            return op_id

        k = len(member_ids)
        share = amount / k

        rows: list[OperationRow] = []

        # 2.1 debit строка для потратившего
        rows.append(
            OperationRow(
                date=now,
                operation_id=op_id,
                person_id=user_id,
                is_expense=True,
                category=category,
                row_type="debit",
                amount=amount,
                active=True,
            )
        )

        # 2.2 credit строки для всех участников
        for pid in member_ids:
            rows.append(
                OperationRow(
                    date=now,
                    operation_id=op_id,
                    person_id=pid,
                    is_expense=True,
                    category=category,
                    row_type="credit",
                    amount=share,
                    active=True,
                )
            )

        self.operation_row_repo.create_many(rows)

        return op_id
