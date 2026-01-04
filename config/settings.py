# config/settings.py

import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ЗАМЕНИ_НА_СВОЙ_ТОКЕН")

# ID основной Google-таблицы (из URL таблицы)
GOOGLE_SPREADSHEET_ID = os.getenv(
    "GOOGLE_SPREADSHEET_ID", "18ZpfUkMo_3I303LOfLT1_kyuCug6FE5uSCBZa93SFDk"
)

# Названия листов и диапазоны
SHEET_GROUPS_RANGE = "Groups!A2:A"  # колонка id в листе Groups
SHEET_USER_GROUPS_RANGE = "userGroups!A2:B"  # колонки userId, groupId
