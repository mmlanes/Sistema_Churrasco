import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import EVENTS_DIR
from services.storage_service import (
    get_event_dir,
    get_event_uploads_dir,
    read_json,
    write_json,
    append_audit_log,
)


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text or str(uuid.uuid4())[:8]


def list_events() -> List[Dict[str, Any]]:
    events = []
    if not EVENTS_DIR.exists():
        return events
    for p in EVENTS_DIR.iterdir():
        if p.is_dir():
            meta_file = p / "meta.json"
            if meta_file.exists():
                meta = read_json(meta_file, {})
                events.append(meta)
    # Ordena pelo mais recente
    events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return events


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    meta_file = get_event_dir(event_id) / "meta.json"
    if meta_file.exists():
        return read_json(meta_file)
    return None


def create_event(name: str, description: str = "", date: str = "", created_by: str = "Admin", access_password: str = "churras2025") -> Dict[str, Any]:
    event_id = slugify(name)
    event_dir = get_event_dir(event_id)
    
    # Se já existir id com esse slug, adiciona sufixo
    if event_dir.exists():
        event_id = f"{event_id}_{int(datetime.now().timestamp())}"
        event_dir = get_event_dir(event_id)
        
    event_dir.mkdir(parents=True, exist_ok=True)
    (event_dir / "uploads" / "receipts").mkdir(parents=True, exist_ok=True)
    (event_dir / "uploads" / "suppliers").mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now().isoformat()
    meta = {
        "id": event_id,
        "name": name,
        "description": description,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "created_at": now_iso,
        "updated_at": now_iso,
        "created_by": created_by,
        "access_password": (access_password or "churras2025").strip(),
        "default_fee_aluno": 25.0,
        "default_fee_servidor": 25.0,
        "default_fee_geral": 25.0
    }
    write_json(event_dir / "meta.json", meta)
    
    # Inicializa arquivos vazios
    write_json(event_dir / "participants.json", [])
    write_json(event_dir / "collaborators.json", [])
    write_json(event_dir / "suppliers.json", [])
    write_json(event_dir / "consumables.json", [])
    write_json(event_dir / "recipes.json", [])
    write_json(event_dir / "tasks.json", [])
    write_json(event_dir / "cashflow.json", [])
    write_json(event_dir / "suggestions.json", [])
    write_json(event_dir / "audit_log.json", [])

    append_audit_log(event_id, created_by, "CRIAR_EVENTO", f"Evento '{name}' criado com sucesso.")
    return meta


def clone_event(
    source_event_id: str,
    new_name: str,
    new_date: str = "",
    copy_consumables: bool = True,
    copy_recipes: bool = True,
    copy_suppliers: bool = True,
    copy_collaborators: bool = True,
    copy_tasks_as_pending: bool = False,
    access_password: str = "churras2025",
    created_by: str = "Admin"
) -> Dict[str, Any]:
    """
    Clona os dados selecionados de um evento para um novo evento completamente independente,
    sem nenhuma dependência ou vínculo ativo com o evento de origem.
    """
    src_dir = get_event_dir(source_event_id)
    if not src_dir.exists():
        raise ValueError(f"Evento de origem '{source_event_id}' não encontrado.")

    # Cria novo evento
    new_event = create_event(
        name=new_name,
        description=f"Clonado a partir do evento '{source_event_id}'",
        date=new_date or datetime.now().strftime("%Y-%m-%d"),
        created_by=created_by,
        access_password=access_password
    )
    dest_dir = get_event_dir(new_event["id"])

    # Copia fornecedores se solicitado
    if copy_suppliers:
        suppliers = read_json(src_dir / "suppliers.json", [])
        write_json(dest_dir / "suppliers.json", suppliers)

    # Copia consumíveis se solicitado
    if copy_consumables:
        consumables = read_json(src_dir / "consumables.json", [])
        write_json(dest_dir / "consumables.json", consumables)

    # Copia receitas (farofas, vinagretes etc.) se solicitado
    if copy_recipes:
        recipes = read_json(src_dir / "recipes.json", [])
        write_json(dest_dir / "recipes.json", recipes)

    # Copia colaboradores cadastrados se solicitado
    if copy_collaborators:
        collaborators = read_json(src_dir / "collaborators.json", [])
        write_json(dest_dir / "collaborators.json", collaborators)

    # Copia tarefas como modelo (com status resetado para 'Pendente')
    if copy_tasks_as_pending:
        src_tasks = read_json(src_dir / "tasks.json", [])
        new_tasks = []
        for t in src_tasks:
            new_t = dict(t)
            new_t["id"] = str(uuid.uuid4())[:8]
            new_t["status"] = "Pendente"
            new_t["actual_spent"] = 0.0
            new_t["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_tasks.append(new_t)
        write_json(dest_dir / "tasks.json", new_tasks)

    append_audit_log(
        new_event["id"],
        created_by,
        "CLONAR_EVENTO",
        f"Evento clonado de '{source_event_id}' para '{new_name}' com isolamento total."
    )
    return new_event


def get_event_data(event_id: str, entity_name: str) -> Any:
    file_path = get_event_dir(event_id) / f"{entity_name}.json"
    return read_json(file_path, default=[])


def save_event_data(event_id: str, entity_name: str, data: Any, user_name: str = "Admin", action_desc: str = "") -> None:
    file_path = get_event_dir(event_id) / f"{entity_name}.json"
    write_json(file_path, data)
    if action_desc:
        append_audit_log(event_id, user_name, f"ATUALIZAR_{entity_name.upper()}", action_desc)


def update_event_password(event_id: str, new_password: str, user_name: str = "Master") -> bool:
    """Atualiza a senha geral de acesso ao evento (permitido para usuário Master)."""
    meta_file = get_event_dir(event_id) / "meta.json"
    if not meta_file.exists():
        return False
    meta = read_json(meta_file, {})
    meta["access_password"] = new_password.strip()
    meta["updated_at"] = datetime.now().isoformat()
    write_json(meta_file, meta)
    append_audit_log(
        event_id,
        user_name,
        "ALTERAR_SENHA_EVENTO",
        f"A senha geral de acesso do evento foi alterada com sucesso."
    )
    return True


def verify_event_password(event_id: str, input_password: str) -> bool:
    """Verifica se a senha fornecida corresponde à senha geral do evento."""
    meta = get_event(event_id)
    if not meta:
        return False
    expected_pwd = meta.get("access_password", "churras2025")
    # Se por algum motivo o evento não tiver senha cadastrada, padrão é 'churras2025'
    if not expected_pwd:
        expected_pwd = "churras2025"
    return input_password.strip() == expected_pwd.strip()


def delete_event(event_id: str, user_name: str = "Master") -> bool:
    """
    Exclui permanentemente a pasta e os dados do evento selecionado.
    Devido ao isolamento total de pastas (data/events/{event_id}),
    a exclusão afeta estritamente este evento, com zero impacto
    ou dependência em relação a outros eventos do sistema.
    """
    events = list_events()
    if len(events) <= 1:
        return False  # Garante que sempre reste ao menos 1 evento

    event_dir = get_event_dir(event_id)
    if event_dir.exists() and event_dir.is_dir():
        shutil.rmtree(event_dir)
        return True
    return False


