#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/botuser/cost2"
SERVICE_NAME="telegram-bot.service"
BRANCH="main"
CREDENTIALS_FILE="credentials.json"
BACKUP_DIR="$PROJECT_DIR/backup"
BACKUP_FILE="$BACKUP_DIR/credentials.json.bak"

echo "== Остановка сервиса =="
sudo systemctl stop "$SERVICE_NAME"

cd "$PROJECT_DIR"

echo "== Подготовка каталога для бэкапа =="
mkdir -p "$BACKUP_DIR"

echo "== Проверка и бэкап $CREDENTIALS_FILE =="
if [ -f "$CREDENTIALS_FILE" ]; then
  cp "$CREDENTIALS_FILE" "$BACKUP_FILE"
  echo "Бэкап сохранён в $BACKUP_FILE"
else
  echo "ВНИМАНИЕ: $CREDENTIALS_FILE не найден в $PROJECT_DIR"
  echo "Скрипт продолжит работу, но после обновления файл нужно будет вернуть вручную."
fi

echo "== Обновление кода из GitHub =="
git fetch origin
git reset --hard "origin/$BRANCH"
git clean -fd

echo "== Восстановление $CREDENTIALS_FILE из бэкапа (если есть) =="
if [ -f "$BACKUP_FILE" ]; then
  cp "$BACKUP_FILE" "$CREDENTIALS_FILE"
  echo "Файл $CREDENTIALS_FILE восстановлен из бэкапа."
else
  echo "Бэкап $BACKUP_FILE не найден. Убедись, что $CREDENTIALS_FILE существует перед запуском бота."
fi

echo "== Обновление зависимостей =="
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo "== Запуск сервиса =="
sudo systemctl start "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager