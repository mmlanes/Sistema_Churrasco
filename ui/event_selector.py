import streamlit as st
from services.event_service import (
    list_events,
    list_events_for_user,
    create_event,
    clone_event,
    get_event,
    update_event_password,
    delete_event
)
from ui.auth_view import can_edit, is_master


def render_event_selector() -> str:
    """Renderiza a seleção do evento ativo no topo, respeitando rigorosamente as permissões de eventos concedidas pelo Master."""
    current_user = st.session_state.get("user", {})
    events = list_events_for_user(current_user)

    if not events:
        st.warning("⚠️ Nenhum evento autorizado para o seu usuário. Solicite permissão de acesso ao Administrador Master.")
        return ""

    event_ids = [e["id"] for e in events]
    event_names = {e["id"]: f"📅 {e['name']} ({e.get('date', '')})" for e in events}

    current_id = st.session_state.get("active_event_id")
    if current_id not in event_ids:
        current_id = event_ids[0]
        st.session_state["active_event_id"] = current_id

    # REGRA: Login de Visualização permite ver apenas o seu único evento associado
    if current_user.get("role") == "visualizador":
        chosen_id = events[0]["id"]
        st.session_state["active_event_id"] = chosen_id
        st.markdown(
            f"<div style='background: rgba(127,127,127,0.08); padding: 8px 14px; border-radius: 6px; font-size: 0.95rem;'>"
            f"🎯 <b>Evento Autorizado:</b> 📅 <b>{events[0]['name']}</b> ({events[0].get('date', '')}) &nbsp;|&nbsp; <i>(Acesso exclusivo a este evento)</i></div>",
            unsafe_allow_html=True
        )
        return chosen_id

    selected_index = event_ids.index(current_id)

    # Colunas: Seletor, Novo, Clonar, Senha e Exclusão (se Master)
    if is_master():
        col1, col2, col3, col4, col5 = st.columns([2.8, 1.1, 1.1, 1.3, 0.9])
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
            key="event_selector_box"
        )
        if chosen_id != current_id:
            st.session_state["active_event_id"] = chosen_id
            st.rerun()

    if can_edit():
        with col2:
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
                        unlocked = st.session_state.setdefault("unlocked_events", set())
                        unlocked.add(ev["id"])
                        st.success(f"Evento '{new_name}' criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe um nome para o evento.")

        with col3:
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
                                st.session_state["active_event_id"] = remaining[0] if remaining else None
                                st.rerun()
                            else:
                                st.error("Não foi possível excluir o evento.")
                        else:
                            st.error("Digite 'EXCLUIR' exatamente para prosseguir.")

    return st.session_state.get("active_event_id", "")

