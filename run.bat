@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000 --settings=config.settings.development
) else (
  python manage.py runserver 0.0.0.0:8000 --settings=config.settings.development
)
pause
