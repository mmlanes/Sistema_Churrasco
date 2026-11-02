import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import EVENTS_DIR, GLOBAL_USERS_FILE


def get_event_dir(event_id: str) -> Path:
    return EVENTS_DIR / event_id


def get_event_uploads_dir(event_id: str, subfolder: str = "") -> Path:
    base = get_event_dir(event_id) / "uploads"
    if subfolder:
        folder = base / subfolder
    else:
        folder = base
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def read_json(file_path: Path, default: Any = None) -> Any:
    if not file_path.exists():
        return default if default is not None else {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def write_json(file_path: Path, data: Any) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_file.replace(file_path)


def append_audit_log(event_id: str, user_name: str, action: str, details: str) -> None:
    """Registra qualquer alteração na base do evento com autor e data/hora."""
    if not event_id:
        return
    log_file = get_event_dir(event_id) / "audit_log.json"
    logs = read_json(log_file, default=[])
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_name or "Anônimo",
        "action": action,
        "details": details
    })
    write_json(log_file, logs)


def get_audit_logs(event_id: str) -> List[Dict[str, Any]]:
    log_file = get_event_dir(event_id) / "audit_log.json"
    logs = read_json(log_file, default=[])
    # Retorna mais recentes primeiro
    return list(reversed(logs))

