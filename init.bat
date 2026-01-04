@echo off
REM Создание директорий
mkdir transport
mkdir transport\telegram

mkdir application
mkdir application\dialogs
mkdir application\usecases

mkdir domain
mkdir domain\models
mkdir domain\services

mkdir infrastructure
mkdir infrastructure\google_sheets

mkdir config
mkdir common

REM Файлы верхнего уровня
type NUL > main.py
type NUL > config\__init__.py
type NUL > common\__init__.py

REM transport / telegram
type NUL > transport\__init__.py
type NUL > transport\telegram\__init__.py
type NUL > transport\telegram\bot.py
type NUL > transport\telegram\registration_handlers.py
type NUL > transport\telegram\expense_handlers.py

REM application
type NUL > application\__init__.py
type NUL > application\dialogs\__init__.py
type NUL > application\dialogs\registration_dialog.py
type NUL > application\dialogs\expense_dialog.py
type NUL > application\usecases\__init__.py
type NUL > application\usecases\user_groups.py
type NUL > application\usecases\expenses.py

REM domain
type NUL > domain\__init__.py
type NUL > domain\models\__init__.py
type NUL > domain\models\groups.py
type NUL > domain\models\expenses.py
type NUL > domain\services\__init__.py
type NUL > domain\services\balance_service.py
type NUL > domain\repositories.py

REM infrastructure / google_sheets
type NUL > infrastructure\__init__.py
type NUL > infrastructure\google_sheets\__init__.py
type NUL > infrastructure\google_sheets\client.py
type NUL > infrastructure\google_sheets\group_repository.py
type NUL > infrastructure\google_sheets\user_group_repository.py
type NUL > infrastructure\google_sheets\expense_repository.py
type NUL > infrastructure\google_sheets\payment_repository.py

REM config и common
type NUL > config\settings.py
type NUL > common\logger.py
type NUL > common\errors.py

echo Project structure created.
pause