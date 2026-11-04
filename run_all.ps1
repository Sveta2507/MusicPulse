$ErrorActionPreference = "Stop"

# створюється локальне середовище, якщо його ще немає
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

# встановлюються зафіксовані залежності проєкту
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

# ініціалізується SQLite і створюється RDF/Turtle
& ".venv\Scripts\python.exe" scripts/bootstrap.py

# виконуються автоматичні тести з вимірюванням покриття
& ".venv\Scripts\python.exe" -m pytest --cov=. --cov-report=term-missing --cov-report=html:htmlcov

# запускається локальний production-сервер
& ".venv\Scripts\waitress-serve.exe" --host=127.0.0.1 --port=5000 app:app

