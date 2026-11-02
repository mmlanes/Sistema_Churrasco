import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

# Import psycopg2 de forma tolerante (caso não esteja disponível em algum ambiente local)
try:
    import psycopg2
    from psycopg2 import pool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    psycopg2 = None
    pool = None

# Gerenciamento de Conexões e Cache de Status
_pool_lock = threading.Lock()
_connection_pool = None
_rest_session: Optional[requests.Session] = None
_last_avail_check_time = 0
_last_avail_check_result = False


def get_supabase_credentials() -> Dict[str, Any]:
    """
    Obtém credenciais do Supabase estritamente de fontes seguras:
    1. st.secrets["supabase"] ou st.secrets raiz (Streamlit Cloud ou local .streamlit/secrets.toml)
    2. Leitura direta de .streamlit/secrets.toml via tomllib (fora do contexto Streamlit)
    3. Variáveis de ambiente
    """
    creds = {
        "url": "",
        "key": "",
        "host": "",
        "port": 5432,
        "user": "postgres",
        "password": "",
        "database": "postgres"
    }

    # 1. Tenta carregar através de st.secrets do Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            # Seção dedicada [supabase]
            if "supabase" in st.secrets:
                sec = st.secrets["supabase"]
                creds["url"] = str(sec.get("url", sec.get("SUPABASE_URL", ""))).strip()
                creds["key"] = str(sec.get("key", sec.get("SUPABASE_KEY", ""))).strip()
                creds["host"] = str(sec.get("db_host", sec.get("host", ""))).strip()
                creds["port"] = int(sec.get("db_port", sec.get("port", 5432)))
                creds["user"] = str(sec.get("db_user", sec.get("user", "postgres"))).strip()
                creds["password"] = str(sec.get("db_password", sec.get("password", ""))).strip()
                creds["database"] = str(sec.get("db_name", sec.get("database", "postgres"))).strip()
            # Chaves na raiz dos secrets
            if not creds["url"] and "SUPABASE_URL" in st.secrets:
                creds["url"] = str(st.secrets["SUPABASE_URL"]).strip()
            if not creds["key"] and "SUPABASE_KEY" in st.secrets:
                creds["key"] = str(st.secrets["SUPABASE_KEY"]).strip()
    except Exception:
        pass

    # 2. Tenta carregar do arquivo local seguro .streamlit/secrets.toml (ignorado pelo git)
    if not (creds["url"] and creds["key"]) and not (creds["host"] and creds["password"]):
        try:
            import tomllib
            from config import BASE_DIR
            local_secrets_file = BASE_DIR / ".streamlit" / "secrets.toml"
            if local_secrets_file.exists():
                with open(local_secrets_file, "rb") as f:
                    data = tomllib.load(f)
                if "supabase" in data:
                    sec = data["supabase"]
                    creds["url"] = str(sec.get("url", sec.get("SUPABASE_URL", ""))).strip()
                    creds["key"] = str(sec.get("key", sec.get("SUPABASE_KEY", ""))).strip()
                    creds["host"] = str(sec.get("db_host", sec.get("host", ""))).strip()
                    creds["port"] = int(sec.get("db_port", sec.get("port", 5432)))
                    creds["user"] = str(sec.get("db_user", sec.get("user", "postgres"))).strip()
                    creds["password"] = str(sec.get("db_password", sec.get("password", ""))).strip()
                    creds["database"] = str(sec.get("db_name", sec.get("database", "postgres"))).strip()
                if not creds["url"] and "SUPABASE_URL" in data:
                    creds["url"] = str(data["SUPABASE_URL"]).strip()
                if not creds["key"] and "SUPABASE_KEY" in data:
                    creds["key"] = str(data["SUPABASE_KEY"]).strip()
        except Exception:
            pass

    # 3. Variáveis de ambiente
    if not creds["url"]:
        creds["url"] = os.getenv("SUPABASE_URL", "").strip()
    if not creds["key"]:
        creds["key"] = os.getenv("SUPABASE_KEY", "").strip()
    if not creds["host"]:
        creds["host"] = os.getenv("SUPABASE_DB_HOST", "").strip()
    if not creds["password"]:
        creds["password"] = os.getenv("SUPABASE_DB_PASSWORD", "").strip()

    return creds


def get_db_credentials() -> Dict[str, Any]:
    """Compatibilidade com chamadas diretas de banco de dados."""
    return get_supabase_credentials()


def _get_rest_session() -> Optional[requests.Session]:
    """Retorna uma sessão HTTP persistente e autenticada para a API REST do Supabase."""
    global _rest_session
    creds = get_supabase_credentials()
    if not creds["url"] or not creds["key"]:
        return None
    if _rest_session is None:
        s = requests.Session()
        s.headers.update({
            "apikey": creds["key"],
            "Authorization": f"Bearer {creds['key']}",
            "Content-Type": "application/json"
        })
        _rest_session = s
    return _rest_session


def _get_rest_base_url() -> str:
    creds = get_supabase_credentials()
    return creds["url"].rstrip("/") + "/rest/v1"


# ========================================================
# CONEXÃO POSTGRESQL (Fallback ou Uso Local Direto)
# ========================================================

def get_pool():
    global _connection_pool
    if not HAS_PSYCOPG2:
        return None
    with _pool_lock:
        if _connection_pool is None or _connection_pool.closed:
            creds = get_supabase_credentials()
            if not creds.get("host") or not creds.get("password"):
                return None
            try:
                _connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=5,
                    host=creds["host"],
                    port=creds["port"],
                    user=creds["user"],
                    password=creds["password"],
                    database=creds["database"],
                    connect_timeout=5
                )
            except Exception:
                _connection_pool = None
        return _connection_pool


@contextmanager
def get_db_cursor(commit=False):
    """Context manager para executar queries PostgreSQL diretas quando aplicável."""
    p = get_pool()
    if p is None:
        raise ConnectionError("Pool de conexão PostgreSQL não disponível.")
    conn = None
    try:
        conn = p.getconn()
        cur = conn.cursor()
        try:
            yield cur
            if commit:
                conn.commit()
        finally:
            cur.close()
    finally:
        if conn and p and not p.closed:
            try:
                p.putconn(conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass


# ========================================================
# VERIFICAÇÃO DE DISPONIBILIDADE
# ========================================================

def is_supabase_available(force_refresh=False) -> bool:
    """
    Verifica se o Supabase está online e funcional.
    Prioriza verificação via HTTPS REST (porta 443, compatível com IPv4 e Streamlit Cloud).
    Utiliza cache em memória de 30s para não onerar o fluxo do Streamlit.
    """
    global _last_avail_check_time, _last_avail_check_result
    now = time.time()
    if not force_refresh and (now - _last_avail_check_time < 30):
        return _last_avail_check_result

    creds = get_supabase_credentials()

    # 1. Testa via REST HTTPS (ideal para Streamlit Cloud e compatibilidade com IPv4)
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            r = sess.get(f"{base}/global_documents?select=doc_name&limit=1", timeout=5)
            if r.status_code in (200, 206):
                _last_avail_check_result = True
                _last_avail_check_time = now
                return True
        except Exception:
            pass

    # 2. Testa via PostgreSQL direto (se REST não configurado)
    if HAS_PSYCOPG2 and creds["host"] and creds["password"]:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT 1;")
                _last_avail_check_result = True
                _last_avail_check_time = now
                return True
        except Exception:
            pass

    _last_avail_check_result = False
    _last_avail_check_time = now
    return False


# ========================================================
# DOCUMENTOS GLOBAIS (ex: users, permissions)
# ========================================================

def get_global_doc(doc_name: str, default: Any = None) -> Any:
    """Lê um documento global (como a lista de usuários)."""
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            r = sess.get(f"{base}/global_documents?doc_name=eq.{doc_name}&select=data", timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return data[0].get("data", default)
                return default if default is not None else {}
        except Exception as e:
            print(f"Aviso REST get_global_doc({doc_name}): {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT data FROM global_documents WHERE doc_name = %s;", (doc_name,))
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass

    return default if default is not None else {}


def save_global_doc(doc_name: str, data: Any) -> bool:
    """Grava ou atualiza um documento global com upsert."""
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            payload = [{
                "doc_name": doc_name,
                "data": data
            }]
            r = sess.post(
                f"{base}/global_documents?on_conflict=doc_name",
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json=payload,
                timeout=8
            )
            if r.status_code in (200, 201, 204):
                return True
        except Exception as e:
            print(f"Aviso REST save_global_doc({doc_name}): {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO global_documents (doc_name, data, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (doc_name)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
                """, (doc_name, json.dumps(data, ensure_ascii=False)))
                return True
        except Exception:
            pass

    return False


# ========================================================
# DOCUMENTOS DE EVENTO (meta, participants, consumables, etc.)
# ========================================================

def get_event_doc(event_id: str, doc_type: str, default: Any = None) -> Any:
    """Lê um documento específico de um evento."""
    fallback_val = default if default is not None else ([] if doc_type != "meta" else {})

    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            r = sess.get(
                f"{base}/event_documents?event_id=eq.{event_id}&doc_type=eq.{doc_type}&select=data",
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return data[0].get("data", fallback_val)
                return fallback_val
        except Exception as e:
            print(f"Aviso REST get_event_doc({event_id}, {doc_type}): {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute(
                    "SELECT data FROM event_documents WHERE event_id = %s AND doc_type = %s;",
                    (event_id, doc_type)
                )
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass

    return fallback_val


def save_event_doc(event_id: str, doc_type: str, data: Any) -> bool:
    """Grava ou atualiza um documento de evento com upsert."""
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            payload = [{
                "event_id": event_id,
                "doc_type": doc_type,
                "data": data
            }]
            r = sess.post(
                f"{base}/event_documents?on_conflict=event_id,doc_type",
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json=payload,
                timeout=8
            )
            if r.status_code in (200, 201, 204):
                return True
        except Exception as e:
            print(f"Aviso REST save_event_doc({event_id}, {doc_type}): {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO event_documents (event_id, doc_type, data, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (event_id, doc_type)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
                """, (event_id, doc_type, json.dumps(data, ensure_ascii=False)))
                return True
        except Exception:
            pass

    return False


def list_events_from_db() -> List[Dict[str, Any]]:
    """Lista todos os eventos cadastrados a partir dos metadados gravados no Supabase."""
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            r = sess.get(f"{base}/event_documents?doc_type=eq.meta&select=data", timeout=8)
            if r.status_code == 200:
                rows = r.json()
                events = [item["data"] for item in rows if "data" in item and item["data"]]
                events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return events
        except Exception as e:
            print(f"Aviso REST list_events_from_db: {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT data FROM event_documents WHERE doc_type = 'meta';")
                rows = cur.fetchall()
                events = [r[0] for r in rows if r and r[0]]
                events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return events
        except Exception:
            pass

    return []


def delete_event_from_db(event_id: str) -> bool:
    """Exclui todos os documentos e uploads de um evento no Supabase."""
    success = False
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            r1 = sess.delete(f"{base}/event_documents?event_id=eq.{event_id}", timeout=8)
            r2 = sess.delete(f"{base}/event_uploads?event_id=eq.{event_id}", timeout=8)
            if r1.status_code in (200, 204) and r2.status_code in (200, 204):
                success = True
        except Exception as e:
            print(f"Aviso REST delete_event_from_db({event_id}): {e}")

    # 2. Fallback via PostgreSQL direto
    if not success and HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM event_documents WHERE event_id = %s;", (event_id,))
                cur.execute("DELETE FROM event_uploads WHERE event_id = %s;", (event_id,))
                success = True
        except Exception:
            pass

    return success


# ========================================================
# UPLOADS E COMPROVANTES (Fotos e Anexos)
# ========================================================

def save_upload_to_db(event_id: str, folder: str, filename: str, file_bytes: bytes, content_type: str = "") -> None:
    """Salva foto/comprovante binário no banco de dados na nuvem."""
    # 1. Tenta via REST API (envia bytea formatado em hex string com prefixo \\x)
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            payload = [{
                "event_id": event_id,
                "folder": folder,
                "filename": filename,
                "file_bytes": "\\x" + file_bytes.hex(),
                "content_type": content_type
            }]
            r = sess.post(
                f"{base}/event_uploads?on_conflict=event_id,folder,filename",
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json=payload,
                timeout=15
            )
            if r.status_code in (200, 201, 204):
                return
        except Exception as e:
            print(f"Aviso REST save_upload_to_db: {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO event_uploads (event_id, folder, filename, file_bytes, content_type, uploaded_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (event_id, folder, filename)
                    DO UPDATE SET file_bytes = EXCLUDED.file_bytes, content_type = EXCLUDED.content_type, uploaded_at = NOW();
                """, (event_id, folder, filename, psycopg2.Binary(file_bytes), content_type))
        except Exception as e:
            print(f"Erro em save_upload_to_db: {e}")


def get_upload_from_db(event_id: str, folder: str, filename: str) -> Optional[bytes]:
    """Recupera foto/comprovante binário salvo no banco de dados."""
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            r = sess.get(
                f"{base}/event_uploads?event_id=eq.{event_id}&folder=eq.{folder}&filename=eq.{filename}&select=file_bytes",
                timeout=15
            )
            if r.status_code == 200:
                rows = r.json()
                if rows and isinstance(rows, list) and len(rows) > 0:
                    raw_hex = rows[0].get("file_bytes")
                    if raw_hex:
                        if raw_hex.startswith("\\x"):
                            raw_hex = raw_hex[2:]
                        return bytes.fromhex(raw_hex)
        except Exception as e:
            print(f"Aviso REST get_upload_from_db: {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute(
                    "SELECT file_bytes FROM event_uploads WHERE event_id = %s AND folder = %s AND filename = %s;",
                    (event_id, folder, filename)
                )
                row = cur.fetchone()
                if row and row[0]:
                    return bytes(row[0])
        except Exception:
            pass

    return None


def list_uploads_from_db(event_id: str, folder: str = "") -> List[str]:
    """Lista os nomes de arquivos salvos para um evento."""
    # 1. Tenta via REST API
    creds = get_supabase_credentials()
    if creds["url"] and creds["key"]:
        try:
            sess = _get_rest_session()
            base = _get_rest_base_url()
            query = f"{base}/event_uploads?event_id=eq.{event_id}"
            if folder:
                query += f"&folder=eq.{folder}"
            query += "&select=filename"
            r = sess.get(query, timeout=8)
            if r.status_code == 200:
                rows = r.json()
                return [item["filename"] for item in rows if "filename" in item]
        except Exception as e:
            print(f"Aviso REST list_uploads_from_db: {e}")

    # 2. Fallback via PostgreSQL direto
    if HAS_PSYCOPG2:
        try:
            with get_db_cursor(commit=False) as cur:
                if folder:
                    cur.execute(
                        "SELECT filename FROM event_uploads WHERE event_id = %s AND folder = %s ORDER BY uploaded_at DESC;",
                        (event_id, folder)
                    )
                else:
                    cur.execute(
                        "SELECT filename FROM event_uploads WHERE event_id = %s ORDER BY uploaded_at DESC;",
                        (event_id,)
                    )
                rows = cur.fetchall()
                return [r[0] for r in rows]
        except Exception:
            pass

    return []


def init_supabase_schema():
    """Garante que as tabelas necessárias existam no Supabase quando conectado via PostgreSQL."""
    if not HAS_PSYCOPG2:
        return
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS event_documents (
                event_id VARCHAR(100) NOT NULL,
                doc_type VARCHAR(50) NOT NULL,
                data JSONB NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                PRIMARY KEY (event_id, doc_type)
            );

            CREATE INDEX IF NOT EXISTS idx_event_docs_event_id ON event_documents(event_id);

            CREATE TABLE IF NOT EXISTS global_documents (
                doc_name VARCHAR(50) PRIMARY KEY,
                data JSONB NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS event_uploads (
                event_id VARCHAR(100) NOT NULL,
                folder VARCHAR(50) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_bytes BYTEA NOT NULL,
                content_type VARCHAR(100),
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                PRIMARY KEY (event_id, folder, filename)
            );
            """)
    except Exception as e:
        print(f"Aviso ao inicializar schema: {e}")
