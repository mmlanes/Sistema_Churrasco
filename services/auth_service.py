import hashlib
from typing import Dict, List, Optional
from config import GLOBAL_USERS_FILE
from services.storage_service import read_json, write_json


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_default_users() -> None:
    users = read_json(GLOBAL_USERS_FILE, default=None)
    if not users:
        # Cria usuários iniciais se o arquivo não existir
        default_users = {
            "admin": {
                "username": "admin",
                "name": "Administrador Master",
                "role": "master",  # master, colaborador, visualizador
                "password_hash": hash_password("admin123"),
                "plain_password": "admin123",
                "email": "admin@churrasco.local",
                "allowed_events": ["*"],
                "active": True
            },
            "matusalem": {
                "username": "matusalem",
                "name": "Matusalém",
                "role": "master",  # Também organizador master
                "password_hash": hash_password("matu123"),
                "plain_password": "matu123",
                "email": "matusalem@churrasco.local",
                "allowed_events": ["*"],
                "active": True
            },
            "manuela": {
                "username": "manuela",
                "name": "Manuela",
                "role": "colaborador",
                "password_hash": hash_password("manu123"),
                "plain_password": "manu123",
                "email": "manuela@churrasco.local",
                "allowed_events": ["churrasco_3_ele_2025"],
                "active": True
            },
            "marcelle": {
                "username": "marcelle",
                "name": "Marcelle",
                "role": "colaborador",
                "password_hash": hash_password("marcelle123"),
                "plain_password": "marcelle123",
                "email": "marcelle@churrasco.local",
                "allowed_events": ["churrasco_3_ele_2025"],
                "active": True
            },
            "julia": {
                "username": "julia",
                "name": "Júlia Marinho",
                "role": "colaborador",
                "password_hash": hash_password("julia123"),
                "plain_password": "julia123",
                "email": "julia@churrasco.local",
                "allowed_events": ["churrasco_3_ele_2025"],
                "active": True
            },
            "convidado": {
                "username": "convidado",
                "name": "Convidado / Visualizador",
                "role": "visualizador",
                "password_hash": hash_password("1234"),
                "plain_password": "1234",
                "email": "convidado@churrasco.local",
                "allowed_events": ["churrasco_3_ele_2025"],
                "active": True
            }
        }
        write_json(GLOBAL_USERS_FILE, default_users)


def get_all_users() -> Dict[str, dict]:
    init_default_users()
    users = read_json(GLOBAL_USERS_FILE, default={})
    
    # Migração / Garantia de integridade para usuários existentes
    changed = False
    for u in users.values():
        if "allowed_events" not in u:
            if u.get("role") == "master":
                u["allowed_events"] = ["*"]
            else:
                u["allowed_events"] = ["churrasco_3_ele_2025"]
            changed = True
        elif u.get("role") == "visualizador" and len(u["allowed_events"]) > 1:
            # Regra: cada login de visualização permite ver apenas um evento associado
            u["allowed_events"] = u["allowed_events"][:1]
            changed = True
    
    if changed:
        write_json(GLOBAL_USERS_FILE, users)

    return users


def authenticate(username: str, password: str) -> Optional[dict]:
    users = get_all_users()
    u = users.get(username.strip().lower())
    if u and u.get("active", True):
        if u.get("password_hash") == hash_password(password):
            return {
                "username": u["username"],
                "name": u["name"],
                "role": u["role"],
                "email": u.get("email", ""),
                "allowed_events": u.get("allowed_events", [])
            }
    return None


def save_user(
    username: str,
    name: str,
    role: str,
    password: Optional[str] = None,
    email: str = "",
    allowed_events: Optional[List[str]] = None
) -> bool:
    users = get_all_users()
    username = username.strip().lower()
    
    # Ajusta allowed_events conforme as regras de negócio
    if role == "master":
        events_to_store = ["*"]
    elif role == "visualizador":
        # Visualizador é estritamente associado a exatamente 1 evento
        events_to_store = allowed_events[:1] if allowed_events else ["churrasco_3_ele_2025"]
    else:
        # Colaborador pode ter múltiplos eventos autorizados pelo master
        events_to_store = allowed_events if allowed_events is not None else ["churrasco_3_ele_2025"]

    if username in users:
        # Atualização
        users[username]["name"] = name
        users[username]["role"] = role
        users[username]["email"] = email
        users[username]["allowed_events"] = events_to_store
        if password:
            users[username]["password_hash"] = hash_password(password)
            users[username]["plain_password"] = password
    else:
        # Novo usuário
        if not password:
            password = "mudar123"
        users[username] = {
            "username": username,
            "name": name,
            "role": role,
            "password_hash": hash_password(password),
            "plain_password": password,
            "email": email,
            "allowed_events": events_to_store,
            "active": True
        }
    
    write_json(GLOBAL_USERS_FILE, users)
    return True


def delete_user(username: str) -> bool:
    users = get_all_users()
    username = username.strip().lower()
    if username not in users:
        return False
    # Garante que sempre exista pelo menos 1 master ativo
    masters = [u for u in users.values() if u.get("role") == "master" and u.get("active", True)]
    if len(masters) <= 1 and users[username].get("role") == "master":
        return False  # Não pode deletar o único master
    
    del users[username]
    write_json(GLOBAL_USERS_FILE, users)
    return True

