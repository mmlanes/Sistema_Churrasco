import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import get_now, EVENTS_DIR, GLOBAL_USERS_FILE
from services.supabase_service import (
    is_supabase_available,
    get_global_doc,
    save_global_doc,
    get_event_doc,
    save_event_doc,
    get_upload_from_db,
    save_upload_to_db,
    list_uploads_from_db
)


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


def _parse_event_and_doc(file_path: Path):
    """Identifica se o caminho do arquivo refere-se a um documento de evento ou global."""
    try:
        resolved = file_path.resolve()
        if resolved.name == "users.json":
            return "__global__", "users"
        if resolved.name == "settings.json":
            return "__global__", "settings"
        
        parts = resolved.parts
        # Procura por "events" no caminho
        if "events" in parts:
            idx = parts.index("events")
            if idx + 2 < len(parts):
                event_id = parts[idx + 1]
                filename = parts[idx + 2]
                if filename.endswith(".json"):
                    doc_type = filename[:-5]
                    return event_id, doc_type
    except Exception:
        pass
    return None, None


def read_json(file_path: Path, default: Any = None) -> Any:
    # 1. Tenta carregar do Supabase se disponível
    event_id, doc_type = _parse_event_and_doc(file_path)
    if event_id:
        try:
            if event_id == "__global__":
                data = get_global_doc(doc_type, default=None)
            else:
                data = get_event_doc(event_id, doc_type, default=None)
            
            if data is not None and data != {} and data != []:
                return data
        except Exception:
            pass

    # 2. Fallback para arquivo local em disco
    if not file_path.exists():
        return default if default is not None else {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def write_json(file_path: Path, data: Any) -> None:
    # 1. Grava no Supabase se for documento gerenciado
    event_id, doc_type = _parse_event_and_doc(file_path)
    if event_id:
        try:
            if event_id == "__global__":
                save_global_doc(doc_type, data)
            else:
                save_event_doc(event_id, doc_type, data)
        except Exception as e:
            print(f"Erro ao sincronizar com Supabase ({file_path}): {e}")

    # 2. Grava também localmente (como cache/espelho local)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(file_path)
    except Exception:
        pass


def append_audit_log(event_id: str, user_name: str, action: str, details: str) -> None:
    """Registra qualquer alteração na base do evento com autor e data/hora no Supabase e local."""
    if not event_id:
        return
    log_entry = {
        "timestamp": get_now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_name or "Anônimo",
        "action": action,
        "details": details
    }
    
    # Grava no Supabase
    logs = get_event_doc(event_id, "audit_log", default=[])
    if not isinstance(logs, list):
        logs = []
    logs.append(log_entry)
    save_event_doc(event_id, "audit_log", logs)

    # Espelha localmente
    try:
        log_file = get_event_dir(event_id) / "audit_log.json"
        write_json(log_file, logs)
    except Exception:
        pass


def get_audit_logs(event_id: str) -> List[Dict[str, Any]]:
    # Tenta obter do Supabase
    logs = get_event_doc(event_id, "audit_log", default=None)
    if logs is not None and isinstance(logs, list):
        return list(reversed(logs))

    # Fallback local
    log_file = get_event_dir(event_id) / "audit_log.json"
    local_logs = read_json(log_file, default=[])
    return list(reversed(local_logs))


def get_system_last_event() -> Optional[str]:
    """Retorna o ID do último evento acessado globalmente no sistema."""
    from config import get_now, GLOBAL_SETTINGS_FILE
    data = read_json(GLOBAL_SETTINGS_FILE, default={})
    if isinstance(data, dict):
        return data.get("last_accessed_event_id")
    return None


def set_system_last_event(event_id: str) -> None:
    """Registra o último evento acessado no sistema global."""
    if not event_id:
        return
    from config import get_now, GLOBAL_SETTINGS_FILE
    data = read_json(GLOBAL_SETTINGS_FILE, default={})
    if not isinstance(data, dict):
        data = {}
    if data.get("last_accessed_event_id") != event_id:
        data["last_accessed_event_id"] = event_id
        data["updated_at"] = get_now().isoformat()
        write_json(GLOBAL_SETTINGS_FILE, data)


def get_default_event_id() -> Optional[str]:
    """Retorna o ID do evento padrão configurado para o sistema."""
    from config import get_now, GLOBAL_SETTINGS_FILE
    data = read_json(GLOBAL_SETTINGS_FILE, default={})
    if isinstance(data, dict):
        return data.get("default_event_id")
    return None


def set_default_event_id(event_id: str) -> None:
    """Configura o evento padrão global do sistema e persiste no settings.json e Supabase."""
    if not event_id:
        return
    from config import get_now, GLOBAL_SETTINGS_FILE
    data = read_json(GLOBAL_SETTINGS_FILE, default={})
    if not isinstance(data, dict):
        data = {}
    data["default_event_id"] = event_id
    data["last_accessed_event_id"] = event_id
    data["updated_at"] = get_now().isoformat()
    write_json(GLOBAL_SETTINGS_FILE, data)
