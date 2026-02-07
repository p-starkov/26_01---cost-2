#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/botuser/cost2"
SERVICE_NAME="telegram-bot.service"
BRANCH="main"
CREDENTIALS_FILE="credentials.json"
BACKUP_DIR="$PROJECT_DIR/backup"
BACKUP_FILE="$BACKUP_DIR/credentials.json.bak"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== НАЧАЛО ДЕПЛОЯ ==="

log "Остановка сервиса: $SERVICE_NAME"
sudo systemctl stop "$SERVICE_NAME" || log "ВНИМАНИЕ: сервис уже остановлен или не запущен"

cd "$PROJECT_DIR"

log "Подготовка каталога для бэкапа: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

log "Проверка и бэкап $CREDENTIALS_FILE"
if [ -f "$CREDENTIALS_FILE" ]; then
  cp "$CREDENTIALS_FILE" "$BACKUP_FILE"
  log "Бэкап $CREDENTIALS_FILE сохранён в $BACKUP_FILE"
else
  log "ВНИМАНИЕ: $CREDENTIALS_FILE не найден в $PROJECT_DIR, бэкап не создан"
fi

log "Обновление кода из GitHub (ветка $BRANCH)"
log "Текущая версия до обновления:"
git rev-parse HEAD

git fetch origin
git reset --hard "origin/$BRANCH"
git clean -fd

log "Новая версия после обновления:"
git rev-parse HEAD
log "Код успешно обновлён из GitHub (ветка $BRANCH)"

log "Восстановление $CREDENTIALS_FILE из бэкапа (если есть)"
if [ -f "$BACKUP_FILE" ]; then
  cp "$BACKUP_FILE" "$CREDENTIALS_FILE"
  log "Файл $CREDENTIALS_FILE успешно восстановлен из $BACKUP_FILE"
else
  log "ВНИМАНИЕ: бэкап $BACKUP_FILE не найден. Убедись, что $CREDENTIALS_FILE существует перед запуском бота."
fi

log "Обновление зависимостей (venv + requirements.txt)"
source venv/bin/activate
pip install -r requirements.txt
deactivate
log "Зависимости успешно обновлены"

log "Запуск сервиса: $SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

if systemctl is-active --quiet "$SERVICE_NAME"; then
  log "Сервис $SERVICE_NAME успешно запущен (status: active)"
else
  log "ОШИБКА: сервис $SERVICE_NAME не запустился. Смотри логи:"
  systemctl status "$SERVICE_NAME" --no-pager || true
  log "=== ДЕПЛОЙ ЗАВЕРШЁН С ОШИБКОЙ ==="
  exit 1
fi

log "=== ДЕПЛОЙ УСПЕШНО ЗАВЕРШЁН ==="
