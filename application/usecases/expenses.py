# application/usecases/expenses.py

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
    """
    Сервис работы с финансовыми операциями.

    Сейчас умеет:
    - создавать затраты типа 'expense' за всех участников группы;
    - (ниже добавим) создавать передачи типа 'transfer' между двумя пользователями.
    """

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
            group_id=group_id,
            date=now,
            id=op_id,
            operation_type="expense",
            person_id=user_id,
            is_expense=True,
            category=category,
            comment=comment,
            amount=amount,
            active=True,
        )
        self.operation_repo.create(op)

        # 2. Список участников группы из userGroups
        # TODO: лучше вынести в отдельный метод репозитория,
        # сейчас используем внутренний вспомогательный метод.
        links, _ = self.user_group_repo._read_all_rows()

        member_ids: list[str] = []
        for row in links:
            if not row:
                continue
            row_user_id = row[0].strip()
            row_group_id = row[1].strip().upper() if len(row) > 1 else ""
            if row_group_id == group_id.strip().upper():
                member_ids.append(row_user_id)

        if not member_ids:
            # На практике лучше бросить исключение, здесь просто вернём id операции.
            return op_id

        k = len(member_ids)
        share = amount / k

        rows: list[OperationRow] = []

        # 2.1 debit строка для потратившего
        rows.append(
            OperationRow(
                group_id=group_id, 
                date=now,
                operation_id=op_id,
                person_id=user_id,
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
                    group_id=group_id, 
                    date=now,
                    operation_id=op_id,
                    person_id=pid,
                    category=category,
                    row_type="credit",
                    amount=share,
                    active=True,
                )
            )

        self.operation_row_repo.create_many(rows)
        return op_id

    # ---------- НОВЫЙ МЕТОД: ПЕРЕДАЧА ДЕНЕГ МЕЖДУ ДВУМЯ ПОЛЬЗОВАТЕЛЯМИ ----------

    def create_transfer(
        self,
        group_id: str,
        from_user_id: str,
        to_user_id: str,
        comment: str,
        amount: float,
    ) -> str:
        """
        Создать операцию передачи денег между двумя пользователями.

        Правила:
        - в таблице Operations создаётся одна строка с типом 'transfer';
        - в таблице OperationRows создаются две строки:
          * debit — для пользователя, который передаёт деньги;
          * credit — для пользователя, который получает деньги.

        Параметры:
        - from_user_id: id пользователя-отправителя (кто регистрирует операцию);
        - to_user_id: id пользователя-получателя (выбран из меню);
        - comment: текст описания передачи;
        - amount: сумма передачи.

        Возвращает:
        - UUID созданной операции.
        """
        now = datetime.now()
        op_id = str(uuid.uuid4())

        # 1. Основная операция в листе operations
        #    Тип — 'transfer', категория — 'transfer', активна по умолчанию.
        op = Operation(
            group_id=group_id,
            date=now,
            id=op_id,
            operation_type="transfer",  # <== тип операции
            person_id=from_user_id,     # инициатор передачи
            is_expense=False,  
            category="transfer",
            comment=comment,
            amount=amount,
            active=True,
        )
        self.operation_repo.create(op)

        # 2. Две строки проводок в листе operationsRows
        rows: list[OperationRow] = []

        # 2.1 Строка отправителя: debit
        rows.append(
            OperationRow(
                group_id=group_id, 
                date=now,
                operation_id=op_id,
                person_id=from_user_id,
                category="transfer",
                row_type="debit",       # у отправителя долг уменьшается
                amount=amount,
                active=True,
            )
        )

        # 2.2 Строка получателя: credit
        rows.append(
            OperationRow(
                group_id=group_id, 
                date=now,
                operation_id=op_id,
                person_id=to_user_id,
                category="transfer",
                row_type="credit",      # у получателя долг/баланс увеличивается
                amount=amount,
                active=True,
            )
        )

        # 3. Сохраняем обе строки сразу
        self.operation_row_repo.create_many(rows)

        return op_id
