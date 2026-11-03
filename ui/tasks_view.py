import uuid
import pandas as pd
import streamlit as st
from services.event_service import get_event_data, save_event_data
from ui.auth_view import can_edit


def render_tasks(event_id: str):
    st.title("📌 Gestão e Atribuição de Tarefas")
    st.caption("Acompanhamento das responsabilidades de cada colaborador (quem faz o vinagrete, quem compra a carne, quem fecha o caixa etc.).")

    # Sincroniza automaticamente tarefas de receitas pendentes com seus custos calculados
    from services.event_service import sync_all_recipes_tasks
    sync_all_recipes_tasks(event_id, user_name="Sistema")

    tasks = get_event_data(event_id, "tasks")
    collaborators = get_event_data(event_id, "collaborators")
    collab_names = [c["name"] for c in collaborators]

    tab1, tab2 = st.tabs(["👤 Minhas Tarefas (Portal do Colaborador)", "📋 Todas as Tarefas do Evento"])

    # ========================================================
    # ABA 1: MINHAS TAREFAS
    # ========================================================
    with tab1:
        current_user = st.session_state.get("user", {})
        default_collab = current_user.get("name", "")

        c_top1, c_top2 = st.columns([2, 1])
        with c_top1:
            st.subheader("Minhas Responsabilidades")
        with c_top2:
            sel_options = ["Todos"] + collab_names
            default_idx = sel_options.index(default_collab) if default_collab in sel_options else 0
            filter_collab = st.selectbox("Visualizar tarefas de:", options=sel_options, index=default_idx)

        my_tasks = tasks
        if filter_collab != "Todos":
            my_tasks = [t for t in tasks if t.get("assigned_to", "").lower() == filter_collab.lower()]

        if not my_tasks:
            st.info(f"Nenhuma tarefa atribuída para '{filter_collab}'.")
        else:
            for t in my_tasks:
                status = t.get("status", "Pendente")
                if status == "Realizada":
                    color_border = "#10B981"
                    badge = "✅ REALIZADA"
                elif status in ["Em Andamento", "Parcial"]:
                    color_border = "#3B82F6"
                    badge = "⏳ EM ANDAMENTO / PARCIAL"
                elif status == "Cancelada":
                    color_border = "#6B7280"
                    badge = "❌ CANCELADA"
                else:
                    color_border = "#F59E0B"
                    badge = "⚠️ PENDENTE"

                with st.container():
                    st.markdown(
                        f"""
                        <div style="border-left: 6px solid {color_border}; background: rgba(127, 127, 127, 0.12); color: inherit; padding: 14px 18px; border-radius: 8px; margin-bottom: 12px; border-top: 1px solid rgba(127,127,127,0.15); border-right: 1px solid rgba(127,127,127,0.15); border-bottom: 1px solid rgba(127,127,127,0.15);">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h4 style="margin:0; color:inherit;">{t.get('title')}</h4>
                                <span style="font-size:0.85rem; font-weight:bold; color:{color_border};">{badge}</span>
                            </div>
                            <p style="margin: 6px 0; color:inherit; opacity: 0.9;">{t.get('description', '')}</p>
                            <div style="font-size:0.9rem; color:inherit; opacity: 0.85;">
                                <b>Responsável:</b> {t.get('assigned_to', 'Não atribuído')} &nbsp;|&nbsp;
                                <b>Prazo:</b> {t.get('deadline', 'Sem data')} &nbsp;|&nbsp;
                                <b>Orçado:</b> R$ {float(t.get('budget', 0)):.2f} &nbsp;|&nbsp;
                                <b>Gasto Real:</b> R$ {float(t.get('actual_spent', 0)):.2f}
                            </div>
                            {f"<div style='margin-top:6px; font-size:0.85rem; color:inherit; opacity:0.75;'><i>Observações:</i> {t.get('notes')}</div>" if t.get('notes') else ""}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Botões de Ação e Edição Detalhada para o Colaborador
                    if can_edit():
                        col_b1, col_b2, col_b3, col_b4 = st.columns([1.4, 1.3, 1.3, 1.3])
                        with col_b1:
                            new_st = st.selectbox(
                                "Status:",
                                ["Pendente", "Em Andamento", "Parcial", "Realizada", "Cancelada"],
                                index=["Pendente", "Em Andamento", "Parcial", "Realizada", "Cancelada"].index(status) if status in ["Pendente", "Em Andamento", "Parcial", "Realizada", "Cancelada"] else 0,
                                key=f"st_sel_{t['id']}"
                            )
                        with col_b2:
                            new_spent = st.number_input(
                                "Gasto Real (R$):",
                                value=float(t.get("actual_spent", 0.0)),
                                step=5.0,
                                key=f"sp_inp_{t['id']}"
                            )
                        with col_b3:
                            st.write("")
                            if st.button("💾 Atualizar", key=f"btn_up_{t['id']}", use_container_width=True):
                                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                orig_t = next(item for item in tasks if item["id"] == t["id"])
                                orig_t["status"] = new_st
                                orig_t["actual_spent"] = float(new_spent)
                                save_event_data(event_id, "tasks", tasks, user_name, f"Atualizou tarefa '{t.get('title')}' para '{new_st}' (Gasto: R$ {new_spent})")
                                st.success(f"Tarefa '{t.get('title')}' atualizada!")
                                st.rerun()
                        with col_b4:
                            st.write("")
                            with st.popover("✏️ Detalhar"):
                                st.subheader(f"Editar Tarefa: {t.get('title')}")
                                with st.form(f"form_card_edit_task_{t['id']}"):
                                    c_title = st.text_input("Título", value=t.get("title", ""))
                                    c_opts = [""] + collab_names
                                    c_cur = t.get("assigned_to", "")
                                    c_idx = c_opts.index(c_cur) if c_cur in c_opts else 0
                                    c_collab = st.selectbox("Responsável", options=c_opts, index=c_idx)
                                    c_dead = st.text_input("Prazo", value=t.get("deadline", ""))
                                    c_desc = st.text_area("Descrição Detalhada e Instruções", value=t.get("description", ""), height=100)
                                    c_budget = st.number_input("Orçamento Estimado (R$)", value=float(t.get("budget", 0.0)), step=10.0)
                                    c_notes = st.text_input("Observações", value=t.get("notes", ""))
                                    if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                                        if c_title.strip():
                                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                            orig_t = next(item for item in tasks if item["id"] == t["id"])
                                            orig_t["title"] = c_title.strip()
                                            orig_t["assigned_to"] = c_collab or "Não Atribuído"
                                            orig_t["deadline"] = c_dead.strip()
                                            orig_t["description"] = c_desc.strip()
                                            orig_t["budget"] = float(c_budget)
                                            orig_t["notes"] = c_notes.strip()
                                            save_event_data(event_id, "tasks", tasks, user_name, f"Editou e detalhou a tarefa '{c_title.strip()}'")
                                            st.success("Tarefa atualizada com sucesso!")
                                            st.rerun()

    # ========================================================
    # ABA 2: TODAS AS TAREFAS
    # ========================================================
    with tab2:
        col_t_title, col_t_sync = st.columns([2.5, 1.5])
        with col_t_title:
            st.subheader("Quadro Completo de Tarefas")
        with col_t_sync:
            if can_edit():
                from services.event_service import sync_all_recipes_tasks
                if st.button("🔄 Sincronizar Tarefas de Receitas", key="btn_sync_recipes_tasks_tab_all", use_container_width=True, help="Gera tarefas pendentes para todas as receitas que possuem colaboradores associados"):
                    user_name = st.session_state.get("user", {}).get("name", "Usuário")
                    c_sync = sync_all_recipes_tasks(event_id, user_name)
                    if c_sync > 0:
                        st.success(f"🎉 {c_sync} tarefa(s) de receita sincronizada(s)!")
                    else:
                        st.info("Todas as receitas associadas já possuem tarefas correspondentes.")
                    st.rerun()
        
        # Adicionar Nova Tarefa
        if can_edit():
            with st.expander("➕ Atribuir Nova Tarefa", expanded=(len(tasks) == 0)):
                with st.form("form_add_task", clear_on_submit=True):
                    t1, t2 = st.columns([2, 1])
                    task_title = t1.text_input("Título da Tarefa (ex: Fazer Farofa, Comprar Pão de Alho, Comprar Gelo) *")
                    task_collab = t2.selectbox("Colaborador Responsável *", [""] + collab_names)

                    t3, t4, t5 = st.columns(3)
                    task_deadline = t3.date_input("Data Limite / Prazo")
                    task_budget = t4.number_input("Orçamento Estimado (R$)", value=50.0, step=10.0)
                    task_status = t5.selectbox("Status Inicial", ["Pendente", "Em Andamento", "Parcial", "Realizada"])

                    task_desc = st.text_area("Descrição Detalhada e Instruções")
                    task_notes = st.text_input("Observações Adicionais")

                    if st.form_submit_button("Criar e Atribuir Tarefa", type="primary"):
                        if task_title.strip():
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            new_task = {
                                "id": f"tsk_{str(uuid.uuid4())[:8]}",
                                "title": task_title.strip(),
                                "description": task_desc.strip(),
                                "assigned_to": task_collab or "Não Atribuído",
                                "deadline": str(task_deadline),
                                "status": task_status,
                                "budget": float(task_budget),
                                "actual_spent": 0.0,
                                "notes": task_notes.strip()
                            }
                            tasks.append(new_task)
                            save_event_data(event_id, "tasks", tasks, user_name, f"Atribuiu tarefa '{task_title}' para '{task_collab}'")
                            st.success(f"Tarefa '{task_title}' atribuída com sucesso!")
                            st.rerun()
                        else:
                            st.error("Informe o título da tarefa.")

        # Tabela Geral de Tarefas
        if tasks:
            df_tasks = pd.DataFrame([
                {
                    "ID": t["id"],
                    "Tarefa": t["title"],
                    "Responsável": t.get("assigned_to", "-"),
                    "Prazo": t.get("deadline", "-"),
                    "Status": t.get("status", "Pendente"),
                    "Orçamento": f"R$ {float(t.get('budget', 0)):.2f}",
                    "Gasto Real": f"R$ {float(t.get('actual_spent', 0)):.2f}",
                    "Descrição": t.get("description", "")
                }
                for t in tasks
            ])
            st.dataframe(df_tasks, use_container_width=True, hide_index=True)

            if can_edit():
                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    with st.expander("✏️ Editar e Descrever Tarefa", expanded=False):
                        st.caption("Selecione uma tarefa para editar o título, responsável, prazo, orçamento e detalhar suas instruções.")
                        sel_edit_id = st.selectbox(
                            "Escolha a tarefa:",
                            options=[t["id"] for t in tasks],
                            format_func=lambda x: next((f"{t['title']} ({t.get('assigned_to', 'Pendente')})" for t in tasks if t["id"] == x), x),
                            key="sel_task_to_edit"
                        )
                        task_to_edit = next(t for t in tasks if t["id"] == sel_edit_id)
                        with st.form(f"form_full_edit_task_{sel_edit_id}"):
                            te1, te2 = st.columns([2, 1])
                            e_title = te1.text_input("Título da Tarefa *", value=task_to_edit.get("title", ""))
                            c_opts = [""] + collab_names
                            cur_collab = task_to_edit.get("assigned_to", "")
                            c_idx = c_opts.index(cur_collab) if cur_collab in c_opts else 0
                            e_collab = te2.selectbox("Colaborador Responsável *", options=c_opts, index=c_idx)

                            te3, te4, te5 = st.columns(3)
                            e_deadline = te3.text_input("Prazo / Data Limite", value=task_to_edit.get("deadline", ""))
                            e_budget = te4.number_input("Orçamento Estimado (R$)", value=float(task_to_edit.get("budget", 0.0)), step=10.0)
                            e_spent = te5.number_input("Gasto Real (R$)", value=float(task_to_edit.get("actual_spent", 0.0)), step=5.0)

                            st_opts = ["Pendente", "Em Andamento", "Parcial", "Realizada", "Cancelada"]
                            cur_st = task_to_edit.get("status", "Pendente")
                            st_idx = st_opts.index(cur_st) if cur_st in st_opts else 0
                            e_status = st.selectbox("Status da Tarefa", options=st_opts, index=st_idx)

                            e_desc = st.text_area("Descrição Detalhada e Instruções de Execução", value=task_to_edit.get("description", ""), height=110)
                            e_notes = st.text_input("Observações Adicionais", value=task_to_edit.get("notes", ""))

                            if st.form_submit_button("💾 Salvar Alterações da Tarefa", type="primary", use_container_width=True):
                                if e_title.strip():
                                    user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                    task_to_edit["title"] = e_title.strip()
                                    task_to_edit["assigned_to"] = e_collab or "Não Atribuído"
                                    task_to_edit["deadline"] = e_deadline.strip()
                                    task_to_edit["budget"] = float(e_budget)
                                    task_to_edit["actual_spent"] = float(e_spent)
                                    task_to_edit["status"] = e_status
                                    task_to_edit["description"] = e_desc.strip()
                                    task_to_edit["notes"] = e_notes.strip()
                                    save_event_data(event_id, "tasks", tasks, user_name, f"Editou e detalhou a tarefa '{e_title.strip()}'")
                                    st.success(f"Tarefa '{e_title.strip()}' atualizada com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("O título da tarefa não pode ficar vazio.")

                with col_act2:
                    with st.expander("🗑️ Excluir Tarefa"):
                        sel_del_id = st.selectbox(
                            "Selecione a tarefa para remover:",
                            options=[t["id"] for t in tasks],
                            format_func=lambda x: next((f"{t['title']} ({t.get('assigned_to')})" for t in tasks if t["id"] == x), x),
                            key="sel_task_to_delete"
                        )
                        if st.button("Confirmar Exclusão da Tarefa", type="primary", use_container_width=True):
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            tasks = [t for t in tasks if t["id"] != sel_del_id]
                            save_event_data(event_id, "tasks", tasks, user_name, f"Excluiu tarefa ID '{sel_del_id}'")
                            st.warning("Tarefa removida com sucesso.")
                            st.rerun()
        else:
            st.info("Nenhuma tarefa cadastrada.")

