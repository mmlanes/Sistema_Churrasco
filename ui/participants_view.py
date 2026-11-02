import uuid
import pandas as pd
import streamlit as st
from services.event_service import get_event_data, save_event_data
from ui.auth_view import can_edit


def render_participants(event_id: str):
    st.title("👥 Participantes e Colaboradores")
    st.caption("Gerenciamento de convidados, alunos, servidores e colaboradores com edição direta na tabela e ações em lote.")

    tab1, tab2 = st.tabs(["📋 Lista de Participantes (Consumidores)", "🛠️ Colaboradores do Evento"])

    # ==========================
    # ABA 1: PARTICIPANTES
    # ==========================
    with tab1:
        participants = get_event_data(event_id, "participants")
        
        # Métricas gerais no topo
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

        if can_edit():
            # ========================================================
            # PAINEL DE AÇÕES EM LOTE
            # ========================================================
            with st.expander("⚡ Ações Rápidas em Lote (Alterar Cota, Exclusão, Baixa e Importação)", expanded=False):
                st.caption("Execute operações em massa para múltiplos participantes simultaneamente.")

                b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs([
                    "💰 Alterar Cota em Lote",
                    "🗑️ Excluir em Lote",
                    "🟢 Dar Baixa / Quitar em Lote",
                    "🚀 Cadastro em Massa (Colar Lista)"
                ])

                # 1. ALTERAR COTA EM LOTE
                with b_tab1:
                    st.write("**Atualizar o valor da cota para um grupo de participantes:**")
                    c_cota1, c_cota2 = st.columns([1, 2])
                    new_batch_fee = c_cota1.number_input("Novo Valor da Cota (R$):", value=25.0, step=5.0, min_value=0.0)
                    batch_target = c_cota2.selectbox(
                        "Aplicar para quem?",
                        [
                            "Todos os Participantes",
                            "Apenas Alunos",
                            "Apenas Servidores/Professores",
                            "Apenas Convidados",
                            "Apenas Pendentes de Pagamento",
                            "Seleção Específica de Participantes"
                        ]
                    )

                    selected_fee_pids = []
                    if batch_target == "Seleção Específica de Participantes":
                        selected_fee_pids = st.multiselect(
                            "Escolha os participantes:",
                            options=[p["id"] for p in participants],
                            format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - Cota: R$ {p.get('fee')}" for p in participants if p["id"] == x), x)
                        )

                    sync_paid_amount = st.checkbox("Ajustar também o valor pago de quem já havia quitado?", value=False)

                    if st.button("💰 Aplicar Nova Cota em Lote", type="primary"):
                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                        updated_count = 0
                        for p in participants:
                            should_update = False
                            if batch_target == "Todos os Participantes":
                                should_update = True
                            elif batch_target == "Apenas Alunos" and p.get("category") == "Aluno":
                                should_update = True
                            elif batch_target == "Apenas Servidores/Professores" and p.get("category") == "Servidor/Professor":
                                should_update = True
                            elif batch_target == "Apenas Convidados" and p.get("category") == "Convidado":
                                should_update = True
                            elif batch_target == "Apenas Pendentes de Pagamento" and not p.get("paid"):
                                should_update = True
                            elif batch_target == "Seleção Específica de Participantes" and p["id"] in selected_fee_pids:
                                should_update = True

                            if should_update:
                                p["fee"] = float(new_batch_fee)
                                if sync_paid_amount and p.get("paid"):
                                    p["paid_amount"] = float(new_batch_fee)
                                updated_count += 1

                        save_event_data(event_id, "participants", participants, user_name, f"Atualizou em lote a cota de {updated_count} participantes para R$ {new_batch_fee:.2f}")
                        st.success(f"Cota de {updated_count} participante(s) atualizada com sucesso para R$ {new_batch_fee:,.2f}!")
                        st.rerun()

                # 2. EXCLUIR EM LOTE
                with b_tab2:
                    st.write("**Excluir múltiplos participantes de uma só vez:**")
                    filter_del_mode = st.radio(
                        "Forma de Seleção para Exclusão:",
                        ["Selecionar Manualmente", "Todos os Não Confirmados (Ausentes)", "Todos de uma Categoria"],
                        horizontal=True
                    )

                    del_candidates = []
                    if filter_del_mode == "Selecionar Manualmente":
                        del_candidates = st.multiselect(
                            "Selecione os participantes a serem excluídos:",
                            options=[p["id"] for p in participants],
                            format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - {'Pago' if p.get('paid') else 'Pendente'}" for p in participants if p["id"] == x), x)
                        )
                    elif filter_del_mode == "Todos os Não Confirmados (Ausentes)":
                        del_candidates = [p["id"] for p in participants if not p.get("confirmed")]
                        st.write(f"Participantes não confirmados encontrados: **{len(del_candidates)} pessoas**.")
                    else:
                        cat_to_del = st.selectbox("Escolha a categoria a excluir:", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"])
                        del_candidates = [p["id"] for p in participants if p.get("category") == cat_to_del]
                        st.write(f"Participantes na categoria '{cat_to_del}': **{len(del_candidates)} pessoas**.")

                    if del_candidates:
                        confirm_batch_del = st.checkbox(f"⚠️ Confirmar a exclusão definitiva de {len(del_candidates)} participante(s)?", value=False)
                        if st.button("🗑️ Excluir Participantes Selecionados", type="secondary"):
                            if confirm_batch_del:
                                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                count_before = len(participants)
                                participants = [p for p in participants if p["id"] not in del_candidates]
                                removed_count = count_before - len(participants)
                                save_event_data(event_id, "participants", participants, user_name, f"Excluiu {removed_count} participantes em lote")
                                st.warning(f"{removed_count} participante(s) removido(s) com sucesso!")
                                st.rerun()
                            else:
                                st.error("Marque a caixa de confirmação acima para prosseguir.")
                    else:
                        st.info("Nenhum participante selecionado para exclusão.")

                # 3. QUITAÇÃO / PAGAMENTOS EM LOTE
                with b_tab3:
                    st.write("**Dar baixa de pagamento para vários participantes de uma só vez:**")
                    c_q1, c_q2 = st.columns([2, 1])
                    unpaid_participants = [p for p in participants if not p.get("paid")]
                    selected_quit = c_q1.multiselect(
                        "Selecione quem efetuou o pagamento:",
                        options=[p["id"] for p in unpaid_participants],
                        format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - Cota R$ {p.get('fee')}" for p in unpaid_participants if p["id"] == x), x)
                    )
                    forma_quit = c_q2.selectbox("Forma de Pagamento:", ["PIX", "Dinheiro", "Cartão", "Transferência", "Abatimento em Compras"])

                    if st.button("🟢 Confirmar Quitação em Lote", type="primary"):
                        if selected_quit:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            for p in participants:
                                if p["id"] in selected_quit:
                                    p["paid"] = True
                                    p["payment_method"] = forma_quit
                                    p["paid_amount"] = float(p.get("fee", 25.0))
                            save_event_data(event_id, "participants", participants, user_name, f"Deu baixa de pagamento em lote para {len(selected_quit)} participantes via {forma_quit}")
                            st.success(f"Pagamento de {len(selected_quit)} participante(s) confirmado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Selecione ao menos um participante para dar baixa.")

                # 4. CADASTRO EM MASSA (COLAR LISTA)
                with b_tab4:
                    st.write("**Importar rapidamente uma lista de nomes:**")
                    st.caption("Cole os nomes abaixo (um por linha). O sistema cadastra todos com 1 clique.")
                    names_text = st.text_area("Lista de Nomes:", placeholder="Carlos Silva\nMariana Souza\nFelipe Santos\nBruna Oliveira")
                    c_m1, c_m2, c_m3 = st.columns(3)
                    bulk_cat = c_m1.selectbox("Categoria:", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"], key="bulk_cat")
                    bulk_fee = c_m2.number_input("Cota Inicial (R$):", value=25.0, step=5.0, key="bulk_fee")
                    bulk_conf = c_m3.checkbox("Presença Confirmada?", value=True, key="bulk_conf")

                    if st.button("🚀 Cadastrar Lista em Massa", type="primary"):
                        raw_lines = [line.strip() for line in names_text.splitlines() if line.strip()]
                        if raw_lines:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            for name in raw_lines:
                                participants.append({
                                    "id": f"p_{str(uuid.uuid4())[:8]}",
                                    "name": name,
                                    "category": bulk_cat,
                                    "confirmed": bulk_conf,
                                    "fee": float(bulk_fee),
                                    "paid": False,
                                    "payment_method": "Pendente",
                                    "paid_amount": 0.0,
                                    "notes": "Cadastrado via importação em massa"
                                })
                            save_event_data(event_id, "participants", participants, user_name, f"Cadastrou em massa {len(raw_lines)} participantes na categoria '{bulk_cat}'")
                            st.success(f"{len(raw_lines)} participante(s) cadastrados com sucesso!")
                            st.rerun()
                        else:
                            st.error("Cole ao menos um nome para importar.")

        # ========================================================
        # EDIÇÃO DIRETA NA TABELA (st.data_editor)
        # ========================================================
        st.subheader("📋 Tabela de Participantes")
        
        if can_edit():
            st.info("💡 **Edição Direta:** Você pode alterar qualquer dado clicando diretamente nas células da tabela (nome, categoria, presença, cota, pago, forma e observações). Para adicionar participantes, vá até a última linha. Para excluir linhas, selecione-as e pressione `Delete`. Ao terminar, clique em **Salvar Alterações da Tabela**.")

            col_s1, col_s2 = st.columns([1.5, 3])
            save_table_btn = col_s1.button("💾 Salvar Alterações da Tabela", type="primary", use_container_width=True)

            # Prepara DataFrame editável
            df_editable = pd.DataFrame([
                {
                    "id": p.get("id") or f"p_{str(uuid.uuid4())[:8]}",
                    "name": p.get("name", ""),
                    "category": p.get("category", "Aluno"),
                    "confirmed": bool(p.get("confirmed", True)),
                    "fee": float(p.get("fee", 25.0)),
                    "paid": bool(p.get("paid", False)),
                    "payment_method": p.get("payment_method", "Pendente"),
                    "paid_amount": float(p.get("paid_amount", 0.0)),
                    "notes": str(p.get("notes", "") or "")
                }
                for p in participants
            ])

            edited_df = st.data_editor(
                df_editable,
                column_config={
                    "id": None,  # Oculta ID técnico
                    "name": st.column_config.TextColumn("Nome *", required=True, width="medium"),
                    "category": st.column_config.SelectboxColumn(
                        "Categoria *",
                        options=["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"],
                        required=True,
                        width="medium"
                    ),
                    "confirmed": st.column_config.CheckboxColumn("Confirmado?", default=True, width="small"),
                    "fee": st.column_config.NumberColumn("Cota (R$)", min_value=0.0, step=1.0, format="R$ %.2f", width="small"),
                    "paid": st.column_config.CheckboxColumn("Pago?", default=False, width="small"),
                    "payment_method": st.column_config.SelectboxColumn(
                        "Forma Pagamento",
                        options=["PIX", "Dinheiro", "Cartão", "Abatimento em Compras", "Pendente"],
                        width="small"
                    ),
                    "paid_amount": st.column_config.NumberColumn("Valor Pago (R$)", min_value=0.0, step=1.0, format="R$ %.2f", width="small"),
                    "notes": st.column_config.TextColumn("Observações", width="large")
                },
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key=f"editor_participants_{event_id}"
            )

            if save_table_btn:
                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                new_records = []
                for _, row in edited_df.iterrows():
                    name_val = str(row.get("name", "")).strip()
                    if not name_val:
                        continue  # ignora linhas em branco
                    row_id = str(row.get("id", "")).strip() or f"p_{str(uuid.uuid4())[:8]}"
                    is_paid = bool(row.get("paid", False))
                    row_fee = float(row.get("fee", 0.0))
                    row_paid_amt = float(row.get("paid_amount", 0.0))
                    if is_paid and row_paid_amt == 0.0:
                        row_paid_amt = row_fee
                    elif not is_paid:
                        row_paid_amt = 0.0

                    new_records.append({
                        "id": row_id,
                        "name": name_val,
                        "category": str(row.get("category", "Aluno")),
                        "confirmed": bool(row.get("confirmed", True)),
                        "fee": row_fee,
                        "paid": is_paid,
                        "payment_method": str(row.get("payment_method", "Pendente")) if is_paid else "Pendente",
                        "paid_amount": row_paid_amt,
                        "notes": str(row.get("notes", "") or "")
                    })

                save_event_data(event_id, "participants", new_records, user_name, f"Atualizou tabela de participantes diretamente no editor ({len(new_records)} registros)")
                st.success("Tabela salva com sucesso!")
                st.rerun()

            # Opção de Edição Individual Detalhada (mantida conforme solicitado)
            with st.expander("✏️ Edição Individual Detalhada (Formulário)"):
                if participants:
                    selected_p_id = st.selectbox(
                        "Selecione o participante:",
                        options=[p["id"] for p in participants],
                        format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - {'Pago' if p.get('paid') else 'Pendente'}" for p in participants if p["id"] == x), x),
                        key="sel_p_indiv"
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
            # Modo Somente Leitura
            if participants:
                df_parts = pd.DataFrame([
                    {
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
