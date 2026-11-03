import os
from datetime import datetime, timezone, timedelta
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
GLOBAL_SETTINGS_FILE = GLOBAL_DIR / "settings.json"
APP_TITLE = "🔥 Calculadora & Gestão de Churrasco"
DEFAULT_EXCEL_FILE = BASE_DIR / "Gastos com churrasco - 3º ELE 2025.xlsx"

# Configuração de Fuso Horário Padrão do Sistema (Horário Oficial de Brasília / America/Sao_Paulo, UTC-3)
try:
    from zoneinfo import ZoneInfo
    APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except Exception:
    APP_TIMEZONE = timezone(timedelta(hours=-3))


def get_now() -> datetime:
    """Retorna o datetime atual no fuso horário do Brasil (America/Sao_Paulo, UTC-3)."""
    return datetime.now(APP_TIMEZONE)
