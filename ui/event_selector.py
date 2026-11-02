import streamlit as st
from services.event_service import list_events, create_event, clone_event, get_event
from ui.auth_view import can_edit, is_master


def render_event_selector() -> str:
    """Renderiza a seleção do evento ativo no topo ou sidebar, com opções de criação e clonagem."""
    events = list_events()
    if not events:
        st.warning("Nenhum evento encontrado.")
        return ""

    event_ids = [e["id"] for e in events]
    event_names = {e["id"]: f"📅 {e['name']} ({e.get('date', '')})" for e in events}

    current_id = st.session_state.get("active_event_id")
    if current_id not in event_ids:
        current_id = event_ids[0]
        st.session_state["active_event_id"] = current_id

    selected_index = event_ids.index(current_id)

    col1, col2, col3 = st.columns([4, 1.2, 1.2])

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

    with col2:
        if can_edit():
            with st.popover("➕ Novo Evento"):
                st.subheader("Criar Novo Evento")
                st.caption("Cria uma base de dados em pasta própria e isolada.")
                new_name = st.text_input("Nome do Evento (ex: Natal 2024, Formatura 2026)", key="new_ev_name")
                new_date = st.date_input("Data do Churrasco", key="new_ev_date")
                new_desc = st.text_area("Descrição / Local", key="new_ev_desc")

                if st.button("Salvar Evento", type="primary", use_container_width=True):
                    if new_name.strip():
                        user_name = st.session_state.get("user", {}).get("name", "Admin")
                        ev = create_event(
                            name=new_name.strip(),
                            description=new_desc,
                            date=str(new_date),
                            created_by=user_name
                        )
                        st.session_state["active_event_id"] = ev["id"]
                        st.success(f"Evento '{new_name}' criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe um nome para o evento.")

    with col3:
        if can_edit():
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
                            created_by=user_name
                        )
                        st.session_state["active_event_id"] = ev["id"]
                        st.success(f"Novo evento '{clone_name}' clonado com sucesso com isolamento total!")
                        st.rerun()
                    else:
                        st.error("Informe o nome para o novo evento.")

    return st.session_state.get("active_event_id", "")

