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
                "email": "admin@churrasco.local",
                "active": True
            },
            "matusalem": {
                "username": "matusalem",
                "name": "Matusalém",
                "role": "master",  # Também organizador master
                "password_hash": hash_password("matu123"),
                "email": "matusalem@churrasco.local",
                "active": True
            },
            "manuela": {
                "username": "manuela",
                "name": "Manuela",
                "role": "colaborador",
                "password_hash": hash_password("manu123"),
                "email": "manuela@churrasco.local",
                "active": True
            },
            "marcelle": {
                "username": "marcelle",
                "name": "Marcelle",
                "role": "colaborador",
                "password_hash": hash_password("marcelle123"),
                "email": "marcelle@churrasco.local",
                "active": True
            },
            "julia": {
                "username": "julia",
                "name": "Júlia Marinho",
                "role": "colaborador",
                "password_hash": hash_password("julia123"),
                "email": "julia@churrasco.local",
                "active": True
            },
            "convidado": {
                "username": "convidado",
                "name": "Convidado / Visualizador",
                "role": "visualizador",
                "password_hash": hash_password("1234"),
                "email": "convidado@churrasco.local",
                "active": True
            }
        }
        write_json(GLOBAL_USERS_FILE, default_users)


def get_all_users() -> Dict[str, dict]:
    init_default_users()
    return read_json(GLOBAL_USERS_FILE, default={})


def authenticate(username: str, password: str) -> Optional[dict]:
    users = get_all_users()
    u = users.get(username.strip().lower())
    if u and u.get("active", True):
        if u.get("password_hash") == hash_password(password):
            return {
                "username": u["username"],
                "name": u["name"],
                "role": u["role"],
                "email": u.get("email", "")
            }
    return None


def save_user(username: str, name: str, role: str, password: Optional[str] = None, email: str = "") -> bool:
    users = get_all_users()
    username = username.strip().lower()
    
    if username in users:
        # Atualização
        users[username]["name"] = name
        users[username]["role"] = role
        users[username]["email"] = email
        if password:
            users[username]["password_hash"] = hash_password(password)
    else:
        # Novo usuário
        if not password:
            password = "mudar123"
        users[username] = {
            "username": username,
            "name": name,
            "role": role,
            "password_hash": hash_password(password),
            "email": email,
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

