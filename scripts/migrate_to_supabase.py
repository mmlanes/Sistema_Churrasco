import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR, EVENTS_DIR, GLOBAL_USERS_FILE
from services.supabase_service import (
    init_supabase_schema,
    is_supabase_available,
    save_event_doc,
    save_global_doc,
    save_upload_to_db,
    list_events_from_db
)


def migrate_local_data():
    print("Iniciando migração de dados locais para o Supabase...")
    if not is_supabase_available():
        print("ERRO: Não foi possível conectar ao Supabase.")
        return False

    init_supabase_schema()
    print("Esquema do Supabase verificado!")

    # 1. Migra usuários globais
    if GLOBAL_USERS_FILE.exists():
        with open(GLOBAL_USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        save_global_doc("users", users)
        print(f"[OK] Usuários globais migrados ({len(users)} contas salvas no Supabase).")

    # 2. Migra cada evento
    if EVENTS_DIR.exists():
        for event_dir in EVENTS_DIR.iterdir():
            if not event_dir.is_dir():
                continue
            event_id = event_dir.name
            print(f"Migrando evento: '{event_id}'...")

            # Migra todos os arquivos JSON do evento
            for json_file in event_dir.glob("*.json"):
                doc_type = json_file.stem
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    save_event_doc(event_id, doc_type, data)
                    print(f"  - Documento '{doc_type}' gravado.")
                except Exception as e:
                    print(f"  - Erro ao ler '{json_file}': {e}")

            # Migra uploads se existirem
            uploads_dir = event_dir / "uploads"
            if uploads_dir.exists():
                for subfolder in uploads_dir.iterdir():
                    if subfolder.is_dir():
                        folder_name = subfolder.name
                        for file_path in subfolder.iterdir():
                            if file_path.is_file():
                                try:
                                    with open(file_path, "rb") as f:
                                        file_bytes = f.read()
                                    save_upload_to_db(event_id, folder_name, file_path.name, file_bytes)
                                    print(f"  - Upload '{folder_name}/{file_path.name}' gravado.")
                                except Exception as e:
                                    print(f"  - Erro no upload '{file_path}': {e}")

    # Verifica os eventos gravados
    events_in_db = list_events_from_db()
    print(f"\nMigração concluída com sucesso! Eventos presentes no Supabase:")
    for ev in events_in_db:
        print(f" - {ev.get('name')} (ID: {ev.get('id')}) | Data: {ev.get('date')}")

    return True


if __name__ == "__main__":
    migrate_local_data()
