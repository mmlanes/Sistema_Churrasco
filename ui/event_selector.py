import streamlit as st
from services.event_service import (
    list_events,
    list_events_for_user,
    get_initial_event_id,
    create_event,
    clone_event,
    get_event,
    update_event_password,
    delete_event
)
from ui.auth_view import can_edit, is_master


def record_event_access(user: dict, event_id: str) -> None:
    """Registra o evento como o último acessado pelo usuário e pelo sistema."""
    if not event_id:
        return
    username = user.get("username")
    if username and user.get("last_event_id") != event_id:
        user["last_event_id"] = event_id
        from services.auth_service import set_user_last_event
        set_user_last_event(username, event_id)

    if st.session_state.get("_cached_system_last_event") != event_id:
        st.session_state["_cached_system_last_event"] = event_id
        from services.storage_service import set_system_last_event
        set_system_last_event(event_id)


def render_event_selector() -> str:
    """Renderiza a seleção do evento ativo no topo com combo de eventos e opção de definir o evento padrão."""
    current_user = st.session_state.get("user", {})
    events = list_events_for_user(current_user)

    if not events:
        st.warning("⚠️ Nenhum evento autorizado para o seu usuário. Solicite permissão de acesso ao Administrador Master.")
        return ""

    event_ids = [e["id"] for e in events]

    from services.storage_service import get_default_event_id, set_default_event_id
    default_id = get_default_event_id() or "churrasco_3_ele_2026"
    if default_id not in event_ids and event_ids:
        default_id = event_ids[0]

    event_names = {}
    for e in events:
        is_def = (e["id"] == default_id)
        pfx = "⭐ " if is_def else "📅 "
        sfx = " [PADRÃO]" if is_def else ""
        event_names[e["id"]] = f"{pfx}{e['name']} ({e.get('date', '')}){sfx}"

    # 1. Determinação do evento ativo:
    # Ao acessar o app ou atualizar a página, o evento padrão global SEMPRE tem prioridade,
    # a menos que o usuário tenha explicitamente trocado de evento no combo durante esta sessão.
    if not st.session_state.get("_user_manually_switched_event"):
        current_id = default_id
        st.session_state["active_event_id"] = current_id
    else:
        current_id = st.session_state.get("active_event_id") or default_id
        if current_id not in event_ids:
            current_id = default_id
            st.session_state["active_event_id"] = current_id

    # Sincroniza query parameter no navegador com o evento ativo
    try:
        if st.query_params.get("event") != current_id:
            st.query_params["event"] = current_id
    except Exception:
        pass

    selected_index = event_ids.index(current_id) if current_id in event_ids else 0

    # Colunas: Seletor, Botão de Padrão (exclusivo Master), Novo, Clonar, Senha e Exclusão (se Master)
    if is_master():
        col1, col_star, col2, col3, col4, col5 = st.columns([2.6, 1.2, 1.0, 1.0, 1.1, 0.8])
    elif can_edit():
        col1, col2, col3 = st.columns([3.5, 1.2, 1.2])
    else:
        col1 = st.container()

    with col1:
        chosen_id = st.selectbox(
            "Selecione o Evento de Churrasco:",
            options=event_ids,
            format_func=lambda x: event_names.get(x, x),
            index=selected_index,
            key=f"event_sel_{current_id}"
        )
        if chosen_id != current_id:
            st.session_state["_user_manually_switched_event"] = True
            st.session_state["active_event_id"] = chosen_id
            try:
                st.query_params["event"] = chosen_id
            except Exception:
                pass
            record_event_access(current_user, chosen_id)
            st.rerun()
        else:
            record_event_access(current_user, chosen_id)

    # Apenas o Administrador Master tem permissão para alterar o evento padrão global do sistema
    if is_master():
        with col_star:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            is_default = (chosen_id == default_id)
            if is_default:
                st.button(
                    "⭐ Padrão Atual",
                    key="btn_is_default_disabled",
                    disabled=True,
                    use_container_width=True,
                    help="Este já é o evento padrão oficial configurado para abrir automaticamente ao acessar o site."
                )
            else:
                if st.button(
                    "⭐ Definir Padrão",
                    key="btn_set_default_active",
                    use_container_width=True,
                    help=f"Exclusivo Master: Define este evento como o padrão oficial que abrirá automaticamente para todos ao acessar https://mml-churrasco.streamlit.app"
                ):
                    set_default_event_id(chosen_id)
                    st.toast(f"⭐ '{chosen_id}' agora é o evento padrão do sistema!", icon="⭐")
                    st.rerun()

    if can_edit():
        with col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("➕ Novo Evento"):
                st.subheader("Criar Novo Evento")
                st.caption("Cria uma base de dados em pasta própria e isolada.")
                new_name = st.text_input("Nome do Evento (ex: Natal 2024, Formatura 2026)", key="new_ev_name")
                new_date = st.date_input("Data do Churrasco", key="new_ev_date")
                new_pwd = st.text_input("Senha Geral de Acesso ao Evento *", value="churras2025", key="new_ev_pwd", help="Senha exigida para qualquer pessoa visualizar este evento")
                new_desc = st.text_area("Descrição / Local", key="new_ev_desc")

                if st.button("Salvar Evento", type="primary", use_container_width=True):
                    if new_name.strip():
                        user_name = st.session_state.get("user", {}).get("name", "Admin")
                        ev = create_event(
                            name=new_name.strip(),
                            description=new_desc,
                            date=str(new_date),
                            created_by=user_name,
                            access_password=new_pwd.strip() or "churras2025"
                        )
                        st.session_state["active_event_id"] = ev["id"]
                        st.session_state["event_selector_box"] = ev["id"]
                        try:
                            st.query_params["event"] = ev["id"]
                        except Exception:
                            pass
                        record_event_access(current_user, ev["id"])
                        unlocked = st.session_state.setdefault("unlocked_events", set())
                        unlocked.add(ev["id"])
                        st.success(f"Evento '{new_name}' criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe um nome para o evento.")

        with col3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("📋 Clonar de Outro"):
                st.subheader("Clonar Registros de Evento Existente")
                st.caption("Copia consumíveis, fornecedores, receitas e tarefas mantendo total isolamento (sem vínculos).")
                
                source_id = st.selectbox(
                    "Copiar a partir de qual evento?",
                    options=event_ids,
                    format_func=lambda x: event_names.get(x, x),
                    key="clone_source_id"
                )
                clone_name = st.text_input("Nome do Novo Evento", placeholder="Ex: Churrasco 4º ELE 2026", key="clone_new_name")
                clone_date = st.date_input("Nova Data", key="clone_new_date")
                clone_pwd = st.text_input("Senha Geral de Acesso ao Novo Evento *", value="churras2025", key="clone_new_pwd")
                
                st.write("**Selecione o que deseja copiar:**")
                c_consumables = st.checkbox("Consumíveis (Carnes, Bebidas, Descartáveis etc.)", value=True)
                c_recipes = st.checkbox("Receitas Fabricadas (Farofa, Vinagrete etc.)", value=True)
                c_suppliers = st.checkbox("Fornecedores cadastrados", value=True)
                c_collabs = st.checkbox("Lista de Colaboradores", value=True)
                c_tasks = st.checkbox("Tarefas como modelo (com status Pendente)", value=True)

                if st.button("Efetuar Clonagem Isolada", type="primary", use_container_width=True):
                    if clone_name.strip():
                        user_name = st.session_state.get("user", {}).get("name", "Admin")
                        ev = clone_event(
                            source_event_id=source_id,
                            new_name=clone_name.strip(),
                            new_date=str(clone_date),
                            copy_consumables=c_consumables,
                            copy_recipes=c_recipes,
                            copy_suppliers=c_suppliers,
                            copy_collaborators=c_collabs,
                            copy_tasks_as_pending=c_tasks,
                            access_password=clone_pwd.strip() or "churras2025",
                            created_by=user_name
                        )
                        st.session_state["active_event_id"] = ev["id"]
                        st.session_state["event_selector_box"] = ev["id"]
                        try:
                            st.query_params["event"] = ev["id"]
                        except Exception:
                            pass
                        record_event_access(current_user, ev["id"])
                        unlocked = st.session_state.setdefault("unlocked_events", set())
                        unlocked.add(ev["id"])
                        st.success(f"Novo evento '{clone_name}' clonado com sucesso com isolamento total!")
                        st.rerun()
                    else:
                        st.error("Informe o nome para o novo evento.")

    # Se for Master, exibe botão de visualização/edição de senha e botão de exclusão
    if is_master():
        curr_event = get_event(chosen_id) or {}
        with col4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            curr_pwd = curr_event.get("access_password", "churras2025")
            with st.popover("🔐 Senha do Evento"):
                st.subheader("Senha Geral do Evento")
                st.caption("Controle exclusivo Master: defina quem pode visualizar este evento.")
                st.info(f"Senha Atual: **`{curr_pwd}`**")

                new_event_pwd = st.text_input("Definir Nova Senha Geral:", value=curr_pwd, key="master_change_ev_pwd")
                if st.button("Salvar Nova Senha", type="primary", use_container_width=True):
                    if new_event_pwd.strip():
                        user_name = st.session_state.get("user", {}).get("name", "Master")
                        update_event_password(chosen_id, new_event_pwd.strip(), user_name)
                        st.success("Senha geral do evento atualizada com sucesso!")
                        st.rerun()
                    else:
                        st.error("A senha não pode ser vazia.")

        with col5:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("🗑️ Excluir"):
                st.subheader(f"Excluir Evento '{curr_event.get('name')}'")
                st.caption("⚠️ Esta ação apagará apenas a pasta deste evento (`data/events/`). Devido ao isolamento total, nenhum outro evento será afetado.")
                if len(events) <= 1:
                    st.warning("Não é possível excluir o único evento existente no sistema.")
                else:
                    confirm_text = st.text_input("Digite 'EXCLUIR' para confirmar:", key=f"confirm_del_{chosen_id}")
                    if st.button("Confirmar Exclusão Definitiva", type="primary", use_container_width=True):
                        if confirm_text.strip().upper() == "EXCLUIR":
                            user_name = st.session_state.get("user", {}).get("name", "Master")
                            if delete_event(chosen_id, user_name):
                                st.success(f"Evento '{curr_event.get('name')}' excluído com sucesso!")
                                remaining = [e["id"] for e in list_events()]
                                next_id = remaining[0] if remaining else None
                                st.session_state["active_event_id"] = next_id
                                st.session_state["event_selector_box"] = next_id
                                if next_id:
                                    try:
                                        st.query_params["event"] = next_id
                                    except Exception:
                                        pass
                                    record_event_access(current_user, next_id)
                                st.rerun()
                            else:
                                st.error("Não foi possível excluir o evento.")
                        else:
                            st.error("Digite 'EXCLUIR' exatamente para prosseguir.")

    return st.session_state.get("active_event_id", "")

