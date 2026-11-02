import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EVENTS_DIR = DATA_DIR / "events"
GLOBAL_DIR = DATA_DIR / "global"

# Garante que os diretórios base existam
DATA_DIR.mkdir(exist_ok=True)
EVENTS_DIR.mkdir(exist_ok=True)
GLOBAL_DIR.mkdir(exist_ok=True)

GLOBAL_USERS_FILE = GLOBAL_DIR / "users.json"
APP_TITLE = "🔥 Calculadora & Gestão de Churrasco"
DEFAULT_EXCEL_FILE = BASE_DIR / "Gastos com churrasco - 3º ELE 2025.xlsx"

