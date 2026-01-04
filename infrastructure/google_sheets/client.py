# infrastructure/google_sheets/client.py

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config.settings import GOOGLE_SPREADSHEET_ID

# Область доступа: чтение и запись в Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Имя файла с ключом сервисного аккаунта
SERVICE_ACCOUNT_FILE = "credentials.json"


def get_sheets_service():
    """
    Создаёт и возвращает клиент Google Sheets API.

    Требуется:
    - файл credentials.json в корне проекта;
    - таблица, доступ к которой выдан сервисному аккаунту.
    """
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service


# ID таблицы будем использовать из настроек
SPREADSHEET_ID = GOOGLE_SPREADSHEET_ID
