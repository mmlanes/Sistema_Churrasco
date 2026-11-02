import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2 import pool

# Configurações padrão do Supabase fornecidas
DEFAULT_SUPABASE_URL = "https://eyxmzryarmdjeekchdsh.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_s3NGM-oDsUvM4nwwsJsDCA_tMHxDe1f"
DEFAULT_DB_HOST = "db.eyxmzryarmdjeekchdsh.supabase.co"
DEFAULT_DB_PORT = 5432
DEFAULT_DB_USER = "postgres"
DEFAULT_DB_PASS = "2Fe_/!&wzyHaF@k"
DEFAULT_DB_NAME = "postgres"

_pool_lock = threading.Lock()
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def get_db_credentials() -> Dict[str, Any]:
    """Obtém credenciais do Supabase a partir de st.secrets ou variáveis de ambiente ou padrões."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "supabase" in st.secrets:
            sec = st.secrets["supabase"]
            return {
                "host": sec.get("db_host", DEFAULT_DB_HOST),
                "port": int(sec.get("db_port", DEFAULT_DB_PORT)),
                "user": sec.get("db_user", DEFAULT_DB_USER),
                "password": sec.get("db_password", DEFAULT_DB_PASS),
                "database": sec.get("db_name", DEFAULT_DB_NAME)
            }
    except Exception:
        pass

    return {
        "host": os.getenv("SUPABASE_DB_HOST", DEFAULT_DB_HOST),
        "port": int(os.getenv("SUPABASE_DB_PORT", DEFAULT_DB_PORT)),
        "user": os.getenv("SUPABASE_DB_USER", DEFAULT_DB_USER),
        "password": os.getenv("SUPABASE_DB_PASSWORD", DEFAULT_DB_PASS),
        "database": os.getenv("SUPABASE_DB_NAME", DEFAULT_DB_NAME)
    }


def get_pool() -> pool.ThreadedConnectionPool:
    global _connection_pool
    with _pool_lock:
        if _connection_pool is None or _connection_pool.closed:
            creds = get_db_credentials()
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=creds["host"],
                port=creds["port"],
                user=creds["user"],
                password=creds["password"],
                database=creds["database"],
                connect_timeout=10
            )
        return _connection_pool


@contextmanager
def get_db_cursor(commit=False):
    """Context manager para executar queries reutilizando conexões do pool de forma segura."""
    p = get_pool()
    conn = None
    try:
        conn = p.getconn()
        # Validação de conexão viva
        try:
            with conn.cursor() as test_cur:
                test_cur.execute("SELECT 1;")
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            creds = get_db_credentials()
            conn = psycopg2.connect(
                host=creds["host"],
                port=creds["port"],
                user=creds["user"],
                password=creds["password"],
                database=creds["database"],
                connect_timeout=10
            )

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


def is_supabase_available() -> bool:
    """Verifica se o Supabase está online e acessível."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT 1;")
            return True
    except Exception:
        return False


def init_supabase_schema():
    """Garante que as tabelas necessárias existam no Supabase."""
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


# ========================================================
# DOCUMENTOS GLOBAIS (ex: users)
# ========================================================

def get_global_doc(doc_name: str, default: Any = None) -> Any:
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT data FROM global_documents WHERE doc_name = %s;", (doc_name,))
            row = cur.fetchone()
            if row:
                return row[0]
            return default if default is not None else {}
    except Exception as e:
        print(f"Erro em get_global_doc({doc_name}): {e}")
        return default if default is not None else {}


def save_global_doc(doc_name: str, data: Any) -> None:
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO global_documents (doc_name, data, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (doc_name)
                DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
            """, (doc_name, json.dumps(data, ensure_ascii=False)))
    except Exception as e:
        print(f"Erro em save_global_doc({doc_name}): {e}")


# ========================================================
# DOCUMENTOS DE EVENTO (meta, participants, consumables, etc.)
# ========================================================

def get_event_doc(event_id: str, doc_type: str, default: Any = None) -> Any:
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT data FROM event_documents WHERE event_id = %s AND doc_type = %s;",
                (event_id, doc_type)
            )
            row = cur.fetchone()
            if row:
                return row[0]
            return default if default is not None else ([] if doc_type != "meta" else {})
    except Exception as e:
        print(f"Erro em get_event_doc({event_id}, {doc_type}): {e}")
        return default if default is not None else ([] if doc_type != "meta" else {})


def save_event_doc(event_id: str, doc_type: str, data: Any) -> None:
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO event_documents (event_id, doc_type, data, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (event_id, doc_type)
                DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
            """, (event_id, doc_type, json.dumps(data, ensure_ascii=False)))
    except Exception as e:
        print(f"Erro em save_event_doc({event_id}, {doc_type}): {e}")


def list_events_from_db() -> List[Dict[str, Any]]:
    """Lista todos os eventos cadastrados a partir dos metadados gravados no Supabase."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT data FROM event_documents WHERE doc_type = 'meta';")
            rows = cur.fetchall()
            events = [r[0] for r in rows if r and r[0]]
            events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return events
    except Exception as e:
        print(f"Erro em list_events_from_db: {e}")
        return []


def delete_event_from_db(event_id: str) -> bool:
    """Exclui todos os documentos e uploads de um evento no Supabase."""
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM event_documents WHERE event_id = %s;", (event_id,))
            cur.execute("DELETE FROM event_uploads WHERE event_id = %s;", (event_id,))
            return True
    except Exception as e:
        print(f"Erro em delete_event_from_db({event_id}): {e}")
        return False


# ========================================================
# UPLOADS E COMPROVANTES (Fotos e Anexos)
# ========================================================

def save_upload_to_db(event_id: str, folder: str, filename: str, file_bytes: bytes, content_type: str = "") -> None:
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
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT file_bytes FROM event_uploads WHERE event_id = %s AND folder = %s AND filename = %s;",
                (event_id, folder, filename)
            )
            row = cur.fetchone()
            if row and row[0]:
                return bytes(row[0])
            return None
    except Exception as e:
        print(f"Erro em get_upload_from_db: {e}")
        return None


def list_uploads_from_db(event_id: str, folder: str = "") -> List[str]:
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
    except Exception as e:
        print(f"Erro em list_uploads_from_db: {e}")
        return []
