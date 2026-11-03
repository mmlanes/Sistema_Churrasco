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
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_") or str(uuid.uuid4())[:8]


def list_events() -> List[Dict[str, Any]]:
    # 1. Tenta carregar eventos diretamente do Supabase
    try:
        from services.supabase_service import is_supabase_available, list_events_from_db
        if is_supabase_available():
            db_events = list_events_from_db()
            if db_events:
                return db_events
    except Exception:
        pass

    # 2. Fallback para arquivos locais em disco
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


def list_events_for_user(user: dict) -> List[Dict[str, Any]]:
    """
    Retorna a lista de eventos permitidos para o usuário.
    - Master: tem acesso a TODOS os eventos.
    - Visualizador: tem permissão estrita para APENAS 1 evento associado.
    - Colaborador / outros: tem acesso aos eventos liberados pelo Master.
    """
    all_events = list_events()
    role = user.get("role", "visualizador")
    if role == "master":
        return all_events
    
    allowed = user.get("allowed_events", [])
    if "*" in allowed:
        return all_events

    if role == "visualizador":
        if allowed:
            target_id = allowed[0]
            matched = [e for e in all_events if e["id"] == target_id]
            if matched:
                return matched
        return all_events[:1]

    # Para colaboradores:
    if not allowed:
        return all_events[:1]
    
    return [e for e in all_events if e["id"] in allowed]


def get_initial_event_id(user: Optional[dict] = None) -> str:
    """
    Determina o evento a ser selecionado quando o usuário acessa o sistema.
    Prioridades:
    1. Query param da URL (st.query_params['event']), se válido e permitido.
    2. Último evento acessado pelo usuário (user['last_event_id']).
    3. Último evento acessado globalmente no sistema (settings.json / Supabase).
    4. Primeiro evento disponível/autorizado.
    """
    user = user or {}
    user_events = list_events_for_user(user)
    if not user_events:
        return ""

    user_event_ids = [e["id"] for e in user_events]

    # 1. URL Query Param
    try:
        import streamlit as st
        qp_ev = st.query_params.get("event")
        if qp_ev and qp_ev in user_event_ids:
            return qp_ev
    except Exception:
        pass

    # 2. Último evento acessado pelo usuário
    user_last = user.get("last_event_id")
    if not user_last and user.get("username"):
        from services.auth_service import get_user_last_event
        user_last = get_user_last_event(user["username"])
    if user_last and user_last in user_event_ids:
        return user_last

    # 3. Último evento acessado globalmente
    try:
        from services.storage_service import get_system_last_event
        sys_last = get_system_last_event()
        if sys_last and sys_last in user_event_ids:
            return sys_last
    except Exception:
        pass

    # 4. Primeiro evento disponível
    return user_event_ids[0]


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
    """Verifica se a senha fornecida corresponde exatamente à senha geral do evento."""
    meta = get_event(event_id)
    if not meta:
        return False
    expected_pwd = meta.get("access_password", "churras2025") or "churras2025"
    return input_password.strip() == expected_pwd.strip()


def delete_event(event_id: str, user_name: str = "Master") -> bool:
    """
    Exclui permanentemente o evento selecionado (no Supabase e no disco local).
    Devido ao isolamento total, a exclusão afeta estritamente este evento.
    """
    events = list_events()
    if len(events) <= 1:
        return False  # Garante que sempre reste ao menos 1 evento

    # Deleta do Supabase
    try:
        from services.supabase_service import delete_event_from_db
        delete_event_from_db(event_id)
    except Exception:
        pass

    # Deleta pasta local se existir
    event_dir = get_event_dir(event_id)
    if event_dir.exists() and event_dir.is_dir():
        shutil.rmtree(event_dir, ignore_errors=True)
    return True


def sync_participants_fees_to_cashflow(
    event_id: str,
    participants: Optional[List[Dict[str, Any]]] = None,
    user_name: str = "Sistema"
) -> float:
    """
    Sincroniza o valor arrecadado com as cotas dos participantes no Caixa (Extrato de Movimentações).
    Cria ou atualiza uma entrada consolidada com as cotas quitadas.
    """
    if participants is None:
        participants = get_event_data(event_id, "participants")

    event_meta = get_event(event_id) or {}
    default_fee = float(event_meta.get("default_fee_aluno", 25.0))
    paid_parts = [p for p in participants if p.get("paid")]

    total_paid = 0.0
    for p in paid_parts:
        amt = float(p.get("paid_amount", 0) or 0)
        if amt <= 0:
            amt = float(p.get("fee", default_fee) or default_fee)
        total_paid += amt
    total_paid = round(total_paid, 2)

    cashflow = get_event_data(event_id, "cashflow")

    # Procura entrada consolidada de cotas existente
    cota_entry = next((
        c for c in cashflow
        if c.get("is_participant_fee") or c.get("category") == "Cotas dos Participantes" or "cotas dos participantes" in str(c.get("description", "")).lower()
    ), None)

    now_str = datetime.now().strftime("%Y-%m-%d")
    desc = f"Arrecadação de Cotas dos Participantes ({len(paid_parts)} pagantes quitados)"

    if cota_entry:
        cota_entry["amount"] = total_paid
        cota_entry["description"] = desc
        cota_entry["category"] = "Cotas dos Participantes"
        cota_entry["is_participant_fee"] = True
        cota_entry["notes"] = f"Atualizado automaticamente a partir de {len(paid_parts)} participantes pagos."
    else:
        if total_paid > 0:
            cota_entry = {
                "id": f"csh_cotas_{str(uuid.uuid4())[:6]}",
                "date": now_str,
                "type": "ENTRADA",
                "category": "Cotas dos Participantes",
                "description": desc,
                "amount": total_paid,
                "payment_method": "PIX / Dinheiro",
                "payer_or_receiver": "Participantes do Evento",
                "attachment_name": "",
                "is_participant_fee": True,
                "notes": f"Gerado automaticamente a partir de {len(paid_parts)} participantes pagos."
            }
            cashflow.insert(0, cota_entry)

    if total_paid > 0 or cota_entry:
        save_event_data(event_id, "cashflow", cashflow, user_name, f"Sincronizou cotas dos participantes no Caixa (R$ {total_paid:.2f})")

    return total_paid


def sync_cashflow_expenses_to_consumables(event_id: str, user_name: str = "Sistema") -> int:
    """
    Identifica despesas de eventos lançadas no Caixa (como Futebol de Sabão, Aluguel de Espaço, Som, etc.)
    e as adiciona aos consumíveis/itens de estrutura do evento caso ainda não estejam cadastrados.
    """
    cashflow = get_event_data(event_id, "cashflow")
    consumables = get_event_data(event_id, "consumables")

    consumable_names_lower = {str(c.get("name", "")).strip().lower() for c in consumables}
    added_count = 0

    for s in cashflow:
        if s.get("type") == "SAIDA":
            s_desc = str(s.get("description", "")).strip()
            s_cat = str(s.get("category", "")).strip()
            is_structure = (
                any(k in s_desc.lower() for k in ["futebol", "sabão", "sabao", "brinquedo", "pula-pula", "chácara", "chacara", "aluguel", "som", "dj", "tenda", "locação", "locacao"])
                or "estrutura" in s_cat.lower()
                or "atração" in s_cat.lower()
                or "serviço" in s_cat.lower()
                or s.get("include_in_event_budget", False)
            )
            if is_structure and s_desc.lower() not in consumable_names_lower:
                new_item = {
                    "id": f"c_{str(uuid.uuid4())[:8]}",
                    "name": s_desc,
                    "category": "🎪 Estrutura & Atrações",
                    "unit": "un",
                    "per_person": 0.0,
                    "fixed_quantity": 1.0,
                    "package_size": 1.0,
                    "package_unit_name": "Locação / Serviço",
                    "unit_price": float(s.get("amount", 0)),
                    "price_is_per_package": False,
                    "supplier_id": "",
                    "assigned_collaborator": s.get("payer_or_receiver", "") or "Comissão",
                    "notes": f"Lançado no Caixa em {s.get('date', '')}. {s.get('notes', '')}".strip()
                }
                consumables.append(new_item)
                consumable_names_lower.add(s_desc.lower())
                added_count += 1

    if added_count > 0:
        save_event_data(event_id, "consumables", consumables, user_name, f"Adicionou {added_count} item(ns) de estrutura/atração a partir dos lançamentos de caixa")

    return added_count


def get_event_financial_summary(event_id: str, count_for_calc: int = 0) -> Dict[str, Any]:
    """
    Retorna o resumo financeiro unificado do evento:
    - Total de cotas recebidas dos participantes
    - Outras entradas do caixa (comissão, patrocínios)
    - Total arrecadado consolidado
    - Gastos reais efetuados (saídas do caixa)
    - Saldo atual / sobra em caixa
    - Orçamento previsto total (consumíveis + receitas + estrutura/serviços)
    - Custo médio por participante
    """
    from services.calculation_service import calculate_consumables_totals, calculate_recipes_totals

    participants = get_event_data(event_id, "participants")
    consumables = get_event_data(event_id, "consumables")
    recipes = get_event_data(event_id, "recipes")
    cashflow = get_event_data(event_id, "cashflow")

    total_parts = len(participants)
    confirmed_parts = len([p for p in participants if p.get("confirmed", True)])
    if count_for_calc <= 0:
        count_for_calc = confirmed_parts if confirmed_parts > 0 else (total_parts or 1)

    calc_consumables, cons_summary = calculate_consumables_totals(consumables, count_for_calc)
    calc_recipes, rec_summary = calculate_recipes_totals(recipes, count_for_calc)

    previsto_direto = cons_summary.get("grand_total", 0.0)
    previsto_receitas = rec_summary.get("recipes_grand_total", 0.0)

    # Identifica saídas do caixa que representam custos/atrações do evento que ainda não foram para consumíveis
    consumable_names_lower = {str(c.get("name", "")).strip().lower() for c in consumables}
    saidas_estrutura_extra = []
    for s in cashflow:
        if s.get("type") == "SAIDA":
            s_desc = str(s.get("description", "")).strip()
            s_cat = str(s.get("category", "")).strip()
            is_structure = (
                any(k in s_desc.lower() for k in ["futebol", "sabão", "sabao", "brinquedo", "pula-pula", "chácara", "chacara", "aluguel", "som", "dj", "tenda", "locação", "locacao"])
                or "estrutura" in s_cat.lower()
                or "atração" in s_cat.lower()
                or "serviço" in s_cat.lower()
                or s.get("include_in_event_budget", False)
            )
            if is_structure and s_desc.lower() not in consumable_names_lower:
                saidas_estrutura_extra.append({
                    "name": s_desc,
                    "category": "🎪 Estrutura & Atrações",
                    "total_cost": float(s.get("amount", 0)),
                    "notes": s.get("notes", "")
                })

    total_estrutura_extra = sum(float(x["total_cost"]) for x in saidas_estrutura_extra)
    previsto_total = previsto_direto + previsto_receitas + total_estrutura_extra
    custo_por_pessoa = previsto_total / count_for_calc if count_for_calc > 0 else 0.0

    # Unificação de arrecadação (Cotas + Caixa)
    event_meta = get_event(event_id) or {}
    default_fee = float(event_meta.get("default_fee_aluno", 25.0))
    total_cotas_pagas = sum(
        float(p.get("paid_amount", p.get("fee", default_fee))) if float(p.get("paid_amount", 0) or 0) > 0 else float(p.get("fee", default_fee) or default_fee)
        for p in participants if p.get("paid")
    )

    entradas_caixa_cotas = sum(
        float(c.get("amount", 0)) for c in cashflow
        if c.get("type") == "ENTRADA" and (c.get("is_participant_fee") or "cotas dos participantes" in str(c.get("description", "")).lower() or c.get("category") == "Cotas dos Participantes")
    )
    entradas_caixa_avulsas = sum(
        float(c.get("amount", 0)) for c in cashflow
        if c.get("type") == "ENTRADA" and not (c.get("is_participant_fee") or "cotas dos participantes" in str(c.get("description", "")).lower() or c.get("category") == "Cotas dos Participantes")
    )

    total_arrecadado = entradas_caixa_avulsas + max(entradas_caixa_cotas, total_cotas_pagas)
    total_gasto_real = sum(float(c.get("amount", 0)) for c in cashflow if c.get("type") == "SAIDA")
    saldo_caixa = total_arrecadado - total_gasto_real

    return {
        "previsto_direto": round(previsto_direto, 2),
        "previsto_receitas": round(previsto_receitas, 2),
        "total_estrutura_extra": round(total_estrutura_extra, 2),
        "saidas_estrutura_extra": saidas_estrutura_extra,
        "previsto_total": round(previsto_total, 2),
        "custo_por_pessoa": round(custo_por_pessoa, 2),
        "total_cotas_pagas": round(total_cotas_pagas, 2),
        "entradas_caixa_avulsas": round(entradas_caixa_avulsas, 2),
        "entradas_caixa_cotas": round(entradas_caixa_cotas, 2),
        "total_arrecadado": round(total_arrecadado, 2),
        "total_gasto_real": round(total_gasto_real, 2),
        "saldo_caixa": round(saldo_caixa, 2),
        "count_for_calc": count_for_calc,
        "total_parts": total_parts,
        "confirmed_parts": confirmed_parts,
        "calc_consumables": calc_consumables,
        "cons_summary": cons_summary,
        "calc_recipes": calc_recipes,
        "rec_summary": rec_summary
    }


