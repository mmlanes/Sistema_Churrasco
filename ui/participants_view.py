import uuid
import pandas as pd
import streamlit as st
from services.event_service import get_event_data, save_event_data
from ui.auth_view import can_edit


def render_participants(event_id: str):
    st.title("👥 Participantes e Colaboradores")
    st.caption("Gerenciamento de convidados, alunos, servidores e colaboradores responsáveis por tarefas.")

    tab1, tab2 = st.tabs(["📋 Lista de Participantes (Consumidores)", "🛠️ Colaboradores do Evento"])

    # ==========================
    # ABA 1: PARTICIPANTES
    # ==========================
    with tab1:
        participants = get_event_data(event_id, "participants")
        
        # Métricas
        total = len(participants)
        confirmados = len([p for p in participants if p.get("confirmed", True)])
        pagos = len([p for p in participants if p.get("paid", False)])
        total_arrecadado = sum(float(p.get("paid_amount", 0)) for p in participants if p.get("paid"))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Cadastrados", f"{total} pessoas")
        m2.metric("Confirmados", f"{confirmados} pessoas")
        m3.metric("Pagantes Quitados", f"{pagos} pessoas")
        m4.metric("Valor Arrecadado", f"R$ {total_arrecadado:,.2f}")

        st.markdown("---")

        # Botão para adicionar participante (se permitido)
        if can_edit():
            with st.expander("➕ Adicionar Novo Participante"):
                with st.form("form_add_participant", clear_on_submit=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    p_name = c1.text_input("Nome do Participante *")
                    p_cat = c2.selectbox("Categoria", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"])
                    p_fee = c3.number_input("Valor da Cota (R$)", value=25.0, step=5.0)

                    c4, c5, c6 = st.columns([1, 1, 2])
                    p_conf = c4.checkbox("Presença Confirmada?", value=True)
                    p_paid = c5.checkbox("Já efetuou o pagamento?", value=False)
                    p_method = c6.selectbox("Forma de Pagamento", ["PIX", "Dinheiro", "Cartão", "Abatimento em Compras", "Pendente"])

                    p_notes = st.text_input("Observações (ex: Turma, Alergia alimentar, Contato)")

                    submitted = st.form_submit_button("Cadastrar Participante", type="primary")
                    if submitted:
                        if p_name.strip():
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            new_p = {
                                "id": f"p_{str(uuid.uuid4())[:8]}",
                                "name": p_name.strip(),
                                "category": p_cat,
                                "confirmed": p_conf,
                                "fee": float(p_fee),
                                "paid": p_paid,
                                "payment_method": p_method if p_paid else "Pendente",
                                "paid_amount": float(p_fee) if p_paid else 0.0,
                                "notes": p_notes
                            }
                            participants.append(new_p)
                            save_event_data(event_id, "participants", participants, user_name, f"Adicionou participante '{p_name}'")
                            st.success(f"Participante '{p_name}' adicionado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Informe o nome do participante.")

        # Tabela e Edição
        if participants:
            df_parts = pd.DataFrame([
                {
                    "ID": p["id"],
                    "Nome": p["name"],
                    "Categoria": p.get("category", "Geral"),
                    "Confirmado": "✅ Sim" if p.get("confirmed") else "❌ Não",
                    "Cota (R$)": f"R$ {float(p.get('fee', 0)):.2f}",
                    "Status Pagamento": "🟢 Pago" if p.get("paid") else "🔴 Pendente",
                    "Forma": p.get("payment_method", "-"),
                    "Valor Pago": f"R$ {float(p.get('paid_amount', 0)):.2f}",
                    "Observações": p.get("notes", "")
                }
                for p in participants
            ])
            st.dataframe(df_parts, use_container_width=True, hide_index=True)

            if can_edit():
                with st.expander("✏️ Editar ou Dar Baixa em Pagamento"):
                    selected_p_id = st.selectbox(
                        "Selecione o participante:",
                        options=[p["id"] for p in participants],
                        format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - {'Pago' if p.get('paid') else 'Pendente'}" for p in participants if p["id"] == x), x)
                    )
                    curr_p = next(p for p in participants if p["id"] == selected_p_id)

                    with st.form("form_edit_participant"):
                        e1, e2, e3 = st.columns([2, 1, 1])
                        new_name = e1.text_input("Nome", value=curr_p["name"])
                        new_cat = e2.selectbox("Categoria", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"], index=["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"].index(curr_p.get("category", "Aluno")) if curr_p.get("category") in ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"] else 0)
                        new_fee = e3.number_input("Valor da Cota (R$)", value=float(curr_p.get("fee", 25.0)), step=5.0)

                        e4, e5, e6 = st.columns([1, 1, 2])
                        new_conf = e4.checkbox("Confirmado", value=bool(curr_p.get("confirmed", True)))
                        new_paid = e5.checkbox("Pago", value=bool(curr_p.get("paid", False)))
                        new_method = e6.selectbox("Forma Pagamento", ["PIX", "Dinheiro", "Cartão", "Abatimento em Compras", "Pendente"], index=0)
                        new_notes = st.text_input("Observações", value=curr_p.get("notes", ""))

                        ecol_a, ecol_b = st.columns(2)
                        with ecol_a:
                            save_btn = st.form_submit_button("Salvar Alterações", type="primary", use_container_width=True)
                        with ecol_b:
                            del_btn = st.form_submit_button("🗑️ Excluir Participante", use_container_width=True)

                        if save_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            curr_p["name"] = new_name.strip()
                            curr_p["category"] = new_cat
                            curr_p["fee"] = float(new_fee)
                            curr_p["confirmed"] = new_conf
                            curr_p["paid"] = new_paid
                            curr_p["payment_method"] = new_method if new_paid else "Pendente"
                            curr_p["paid_amount"] = float(new_fee) if new_paid else 0.0
                            curr_p["notes"] = new_notes

                            save_event_data(event_id, "participants", participants, user_name, f"Atualizou participante '{new_name}'")
                            st.success(f"Participante '{new_name}' atualizado!")
                            st.rerun()

                        if del_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            participants = [p for p in participants if p["id"] != selected_p_id]
                            save_event_data(event_id, "participants", participants, user_name, f"Excluiu participante '{curr_p['name']}'")
                            st.warning(f"Participante '{curr_p['name']}' excluído.")
                            st.rerun()
        else:
            st.info("Nenhum participante registrado neste evento.")

    # ==========================
    # ABA 2: COLABORADORES
    # ==========================
    with tab2:
        collaborators = get_event_data(event_id, "collaborators")

        st.subheader("🛠️ Equipe de Colaboradores e Organizadores")
        st.caption("Pessoas responsáveis por compras, churrasqueira, preparo de acompanhamentos, limpeza e caixa.")

        if can_edit():
            with st.expander("➕ Cadastrar Novo Colaborador"):
                with st.form("form_add_collab", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    collab_name = c1.text_input("Nome do Colaborador *")
                    collab_role = c2.text_input("Função / Papel (ex: Mestre Churrasqueiro, Chef da Farofa, Compras)")
                    
                    c3, c4 = st.columns(2)
                    collab_phone = c3.text_input("WhatsApp / Telefone")
                    collab_email = c4.text_input("E-mail")

                    if st.form_submit_button("Cadastrar Colaborador", type="primary"):
                        if collab_name.strip():
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            new_c = {
                                "id": f"c_{str(uuid.uuid4())[:8]}",
                                "name": collab_name.strip(),
                                "role": collab_role.strip() or "Apoio Geral",
                                "phone": collab_phone.strip(),
                                "email": collab_email.strip()
                            }
                            collaborators.append(new_c)
                            save_event_data(event_id, "collaborators", collaborators, user_name, f"Cadastrou colaborador '{collab_name}'")
                            st.success(f"Colaborador '{collab_name}' adicionado!")
                            st.rerun()
                        else:
                            st.error("Informe o nome do colaborador.")

        if collaborators:
            df_collabs = pd.DataFrame([
                {
                    "Nome": c["name"],
                    "Função / Responsabilidade": c.get("role", "Apoio"),
                    "Telefone / Contato": c.get("phone", "-"),
                    "E-mail": c.get("email", "-")
                }
                for c in collaborators
            ])
            st.dataframe(df_collabs, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum colaborador registrado ainda.")

