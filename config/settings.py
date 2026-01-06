# config/settings.py

import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8562811620:AAHYNmfY37lrYWchKdUe0gCZvbS9v9tCxzk")

# ID основной Google-таблицы (из URL таблицы)
GOOGLE_SPREADSHEET_ID = os.getenv(
    "GOOGLE_SPREADSHEET_ID", "18ZpfUkMo_3I303LOfLT1_kyuCug6FE5uSCBZa93SFDk"
)

# Названия листов и диапазоны
SHEET_GROUPS_RANGE = "Groups!A2:A"  # колонка id в листе Groups
SHEET_USER_GROUPS_RANGE = "userGroups!A2:B"  # колонки userId, groupId

# диапазон для листа users
SHEET_USERS_RANGE = "users!A2:B"  # A: userId, B: userName

# GID листа userGroups (sheetId), для batchUpdate deleteDimension
SHEET_ID_USER_GROUPS = 1924028603  

# Диапазоны для операций
SHEET_OPERATIONS_RANGE = "operations!A2:H"       # Date, Id, OperationType, Person, Category, Comment, Amount, Active
SHEET_OPERATION_ROWS_RANGE = "operationsRows!A2:H"  # Date, Operation, Person, IsExpense, Category, Type, Amount, Active