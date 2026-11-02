import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from services.auth_service import get_all_users, save_user
from services.event_service import get_event, get_event_data, list_events, save_event_data
from services.storage_service import (
    get_audit_logs,
    get_event_dir,
    get_event_uploads_dir,
    read_json,
    write_json,
)
from services.supabase_service import (
    get_upload_from_db,
    is_supabase_available,
    list_uploads_from_db,
    save_event_doc,
    save_global_doc,
)

DOCUMENT_TYPES = [
    "meta",
    "participants",
    "collaborators",
    "consumables",
    "recipes",
    "tasks",
    "cashflow",
    "suppliers",
    "suggestions",
]


def export_event_database(event_id: str) -> Dict[str, Any]:
    """Exporta todos os documentos e dados de um único evento em um dicionário estruturado."""
    meta = get_event(event_id) or {}
    ev_data: Dict[str, Any] = {
        "export_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "type": "single_event_backup",
        "id": event_id,
        "event_id": event_id,
        "name": meta.get("name", event_id),
        "documents": {}
    }

    for dt in DOCUMENT_TYPES:
        ev_data["documents"][dt] = get_event_data(event_id, dt)

    ev_data["documents"]["audit_log"] = get_audit_logs(event_id)
    return ev_data


def export_full_database() -> Dict[str, Any]:
    """
    Exporta a base de dados completa do sistema (dados globais e todos os eventos)
    em formato dicionário pronto para serialização JSON.
    """
    users = get_all_users()
    events = list_events()

    total_participants = 0
    total_consumables = 0

    exported_events = []
    for ev in events:
        eid = ev.get("id")
        if not eid:
            continue
        ev_bundle = export_event_database(eid)
        
        parts = ev_bundle["documents"].get("participants", [])
        conss = ev_bundle["documents"].get("consumables", [])
        total_participants += len(parts)
        total_consumables += len(conss)

        exported_events.append(ev_bundle)

    full_backup = {
        "export_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "type": "full_system_backup",
        "system_title": "Sistema de Gestão e Calculadora de Churrasco",
        "stats": {
            "total_users": len(users),
            "total_events": len(exported_events),
            "total_participants": total_participants,
            "total_consumables": total_consumables
        },
        "global_documents": {
            "users": users
        },
        "events": exported_events
    }

    return full_backup


def export_full_database_json_bytes(indent: int = 2) -> bytes:
    """Gera o arquivo JSON completo de backup em bytes UTF-8 para download."""
    data = export_full_database()
    json_str = json.dumps(data, ensure_ascii=False, indent=indent)
    return json_str.encode("utf-8")


def export_event_database_json_bytes(event_id: str, indent: int = 2) -> bytes:
    """Gera o arquivo JSON de um único evento em bytes UTF-8 para download."""
    data = export_event_database(event_id)
    json_str = json.dumps(data, ensure_ascii=False, indent=indent)
    return json_str.encode("utf-8")


def export_full_database_zip() -> bytes:
    """
    Gera um arquivo .ZIP completo contendo:
    1. backup_completo.json consolidado
    2. Pasta com todos os JSONs individuais separados
    3. Todas as fotos e comprovantes anexados
    """
    full_data = export_full_database()
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. JSON Consolidado
        full_json = json.dumps(full_data, ensure_ascii=False, indent=2)
        zf.writestr("backup_completo_churrasco.json", full_json.encode("utf-8"))

        # 2. Usuários globais
        users_json = json.dumps(full_data.get("global_documents", {}).get("users", {}), ensure_ascii=False, indent=2)
        zf.writestr("global/users.json", users_json.encode("utf-8"))

        # 3. Documentos individuais por evento
        for ev in full_data.get("events", []):
            eid = ev.get("event_id")
            docs = ev.get("documents", {})
            for dt, content in docs.items():
                d_str = json.dumps(content, ensure_ascii=False, indent=2)
                zf.writestr(f"events/{eid}/{dt}.json", d_str.encode("utf-8"))

            # 4. Fotos e Comprovantes de cada evento
            for folder in ["receipts", "suppliers"]:
                try:
                    filenames = list_uploads_from_db(eid, folder)
                    for fn in filenames:
                        raw_bytes = get_upload_from_db(eid, folder, fn)
                        if raw_bytes:
                            zf.writestr(f"events/{eid}/uploads/{folder}/{fn}", raw_bytes)
                except Exception:
                    pass

                # Fallback de arquivos em disco local se existirem
                local_folder = get_event_uploads_dir(eid, folder)
                if local_folder.exists():
                    for f in local_folder.iterdir():
                        if f.is_file():
                            arc_name = f"events/{eid}/uploads/{folder}/{f.name}"
                            if arc_name not in zf.namelist():
                                try:
                                    zf.write(f, arc_name)
                                except Exception:
                                    pass

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def import_database_from_json(json_content: Any, current_user: str = "Admin") -> Tuple[bool, str, Dict[str, Any]]:
    """
    Restaura ou migra uma base de dados completa ou um evento único a partir de um JSON.
    Aceita string JSON, bytes ou dict.
    Atualiza Supabase e armazenamento local com segurança.
    """
    try:
        if isinstance(json_content, bytes):
            data = json.loads(json_content.decode("utf-8"))
        elif isinstance(json_content, str):
            data = json.loads(json_content)
        elif isinstance(json_content, dict):
            data = json_content
        else:
            return False, "Formato inválido de arquivo.", {}

        backup_type = data.get("type", "unknown")

        # 1. Restauração de Evento Único
        if backup_type == "single_event_backup" or ("event_id" in data and "documents" in data):
            eid = data.get("event_id")
            if not eid:
                return False, "JSON de evento não possui campo 'event_id'.", {}

            docs = data.get("documents", {})
            for dt, content in docs.items():
                if dt in DOCUMENT_TYPES or dt == "audit_log":
                    save_event_data(eid, dt, content, user_name=current_user, action_desc=f"Restauração de backup do evento '{eid}'")

            return True, f"Evento '{eid}' restaurado com sucesso com {len(docs)} documentos!", {
                "events_imported": 1,
                "users_imported": 0
            }

        # 2. Restauração de Base Completa
        elif backup_type == "full_system_backup" or "global_documents" in data or "events" in data:
            users_imported = 0
            events_imported = 0

            # Restaura usuários globais
            users = data.get("global_documents", {}).get("users", {})
            if users and isinstance(users, dict):
                for uname, udata in users.items():
                    save_user(
                        username=uname,
                        name=udata.get("name", uname),
                        role=udata.get("role", "visualizador"),
                        password=udata.get("plain_password") or udata.get("password", "123456"),
                        email=udata.get("email", ""),
                        allowed_events=udata.get("allowed_events", ["*"])
                    )
                    users_imported += 1

            # Restaura eventos
            events_list = data.get("events", [])
            for ev in events_list:
                eid = ev.get("event_id") or ev.get("id")
                if not eid:
                    continue

                docs = ev.get("documents", {})
                for dt, content in docs.items():
                    if dt in DOCUMENT_TYPES or dt == "audit_log":
                        save_event_data(eid, dt, content, user_name=current_user, action_desc=f"Importação completa do evento '{eid}'")
                events_imported += 1

            return True, f"Base importada com sucesso: {events_imported} eventos e {users_imported} usuários restaurados!", {
                "events_imported": events_imported,
                "users_imported": users_imported
            }

        else:
            return False, "Estrutura do JSON não reconhecida como backup válido deste sistema.", {}

    except Exception as e:
        return False, f"Erro ao processar importação: {str(e)}", {}
