# -*- coding: utf-8 -*-
"""
Script de Compilação e Versionamento Incremental do Sistema de Churrasco.
Incrementa o número do build, registra data/hora no fuso de Brasília e o hash do commit git.
Gera version.json e version.py para consumo direto pelo Streamlit e pela interface.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent

# Fuso Horário Oficial de Brasília
try:
    from zoneinfo import ZoneInfo
    APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except Exception:
    APP_TIMEZONE = timezone(timedelta(hours=-3))

VERSION_JSON = ROOT_DIR / "version.json"
VERSION_PY = ROOT_DIR / "version.py"


def get_git_commit_short() -> str:
    """Tenta obter o hash curto do commit git atual."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def build_next_version(
    increment_build: bool = True,
    inc_patch: bool = False,
    inc_minor: bool = False,
    inc_major: bool = False
) -> dict:
    """Carrega a versão atual, incrementa conforme parâmetros e regrava version.json e version.py."""
    data = {
        "major": 1,
        "minor": 1,
        "patch": 0,
        "build": 0,
        "version_str": "1.1.0",
        "built_at": "",
        "commit_hash": ""
    }

    if VERSION_JSON.exists():
        try:
            with open(VERSION_JSON, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data.update(loaded)
        except Exception:
            pass

    if inc_major:
        data["major"] = int(data.get("major", 1)) + 1
        data["minor"] = 0
        data["patch"] = 0
        data["build"] = 1
    elif inc_minor:
        data["minor"] = int(data.get("minor", 0)) + 1
        data["patch"] = 0
        data["build"] = 1
    elif inc_patch:
        data["patch"] = int(data.get("patch", 0)) + 1
        data["build"] = 1
    elif increment_build or data["build"] == 0:
        data["build"] = int(data.get("build", 0)) + 1

    now_sp = datetime.now(APP_TIMEZONE)
    data["built_at"] = now_sp.strftime("%d/%m/%Y %H:%M")
    data["commit_hash"] = get_git_commit_short() or data.get("commit_hash", "")
    data["version_str"] = f"{data['major']}.{data['minor']}.{data['patch']}"

    # Salva version.json
    with open(VERSION_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Gera version.py
    py_content = f'''# -*- coding: utf-8 -*-
"""Arquivo gerado automaticamente por scripts/build.py. Não edite manualmente."""

APP_VERSION = "{data['version_str']}"
BUILD_NUMBER = {data['build']}
BUILD_DATETIME = "{data['built_at']}"
GIT_COMMIT = "{data['commit_hash']}"
VERSION_DISPLAY = "v{data['version_str']} (Build #{data['build']})"
BUILD_FULL_DISPLAY = "v{data['version_str']} (Build #{data['build']} • {data['built_at']})"
'''
    with open(VERSION_PY, "w", encoding="utf-8") as f:
        f.write(py_content)

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incrementa versão e compila metadados.")
    parser.add_argument("--patch", action="store_true", help="Incrementa versão patch")
    parser.add_argument("--minor", action="store_true", help="Incrementa versão minor")
    parser.add_argument("--major", action="store_true", help="Incrementa versão major")
    parser.add_argument("--no-inc", action="store_true", help="Apenas atualiza timestamp sem incrementar build")
    args = parser.parse_args()

    info = build_next_version(
        increment_build=not args.no_inc,
        inc_patch=args.patch,
        inc_minor=args.minor,
        inc_major=args.major
    )
    print(f"Compilação concluída: {info['version_str']} (Build #{info['build']}) em {info['built_at']} [{info['commit_hash']}]")
