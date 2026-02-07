# Telegram bot (aiogram) — деплой на сервере

Бот работает на сервере Timeweb под Ubuntu, запускается как systemd‑сервис `telegram-bot.service` и использует виртуальное окружение Python (`venv`) и Google Sheets через сервисный аккаунт (`credentials.json`). [web:27][web:94][web:97]

## Структура проекта на сервере

- Путь к проекту: `/home/botuser/cost2`
- Виртуальное окружение: `/home/botuser/cost2/venv`
- Файл сервиса systemd: `/etc/systemd/system/telegram-bot.service`
- Файл с ключами Google: `/home/botuser/cost2/credentials.json` (НЕ в git) [web:27][web:97]

## Как подключиться к серверу

Через SSH (пример):

```bash
ssh botuser@IP_СЕРВЕРА