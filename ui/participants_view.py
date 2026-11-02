import uuid
import pandas as pd
import streamlit as st
from services.event_service import get_event, get_event_data, save_event_data
from ui.auth_view import can_edit


def render_participants(event_id: str):
    st.title("👥 Participantes e Colaboradores")
    st.caption("Gerenciamento de convidados, alunos, servidores e definição de colaboradores sem retrabalho.")

    tab1, tab2 = st.tabs(["📋 Lista de Participantes (Consumidores)", "🛠️ Colaboradores do Evento"])

    participants = get_event_data(event_id, "participants")
    collaborators = get_event_data(event_id, "collaborators")
    event_meta = get_event(event_id) or {}
    default_fee = float(event_meta.get("default_fee_aluno", 25.0))

    # Conjuntos de busca rápida para verificar colaboradores existentes
    collab_names_set = {c["name"].strip().lower() for c in collaborators}
    collab_pids_set = {c.get("participant_id") for c in collaborators if c.get("participant_id")}

    # ==========================
    # ABA 1: PARTICIPANTES
    # ==========================
    with tab1:
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
            # Notificação se o evento estiver vazio
            if total == 0:
                st.info("👋 **Este evento ainda não possui participantes cadastrados.** Use o formulário **➕ Adicionar Novo Participante** logo abaixo ou importe vários nomes de uma só vez no **🚀 Cadastro em Massa**.")

            # ========================================================
            # 1. FORMULÁRIO: ADICIONAR NOVO PARTICIPANTE (INDIVIDUAL)
            # ========================================================
            with st.expander("➕ Adicionar Novo Participante", expanded=(total == 0)):
                st.subheader("Cadastrar Participante")
                st.caption("Preencha os dados e clique em 'Cadastrar Participante'.")

                with st.form("form_add_single_participant", clear_on_submit=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    p_name = c1.text_input("Nome Completo *", placeholder="Ex: Carlos Silva")
                    p_cat = c2.selectbox("Categoria", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"], index=0)
                    p_fee = c3.number_input("Valor da Cota (R$)", value=default_fee, step=5.0, min_value=0.0)

                    c4, c5, c6 = st.columns([1, 1, 2])
                    p_conf = c4.checkbox("Presença Confirmada?", value=True)
                    p_paid = c5.checkbox("Já efetuou o pagamento?", value=False)
                    p_method = c6.selectbox("Forma de Pagamento", ["PIX", "Dinheiro", "Cartão", "Abatimento em Compras", "Pendente"])

                    p_notes = st.text_input("Observações (Turma, restrição alimentar, telefone, etc.)", placeholder="Opcional")

                    # Opção de já incluir na equipe de colaboradores se for categoria Colaborador
                    c_collab_role = ""
                    if p_cat == "Colaborador":
                        c_collab_role = st.text_input("Função como Colaborador (opcional)", value="Apoio Geral")

                    if st.form_submit_button("➕ Cadastrar Participante", type="primary", use_container_width=True):
                        if p_name.strip():
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            p_uuid = f"p_{str(uuid.uuid4())[:8]}"
                            new_participant = {
                                "id": p_uuid,
                                "name": p_name.strip(),
                                "category": p_cat,
                                "confirmed": p_conf,
                                "fee": float(p_fee),
                                "paid": p_paid,
                                "payment_method": p_method if p_paid else "Pendente",
                                "paid_amount": float(p_fee) if p_paid else 0.0,
                                "notes": p_notes.strip()
                            }
                            participants.append(new_participant)
                            save_event_data(event_id, "participants", participants, user_name, f"Cadastrou participante '{p_name.strip()}'")

                            # Se cadastrado como Colaborador, já vincula na equipe automaticamente
                            if p_cat == "Colaborador" and p_name.strip().lower() not in collab_names_set:
                                collaborators.append({
                                    "id": f"c_{str(uuid.uuid4())[:8]}",
                                    "participant_id": p_uuid,
                                    "name": p_name.strip(),
                                    "role": c_collab_role.strip() or "Apoio Geral",
                                    "phone": "",
                                    "email": ""
                                })
                                save_event_data(event_id, "collaborators", collaborators, user_name, f"Vinculou participante '{p_name.strip()}' à equipe de colaboradores")

                            st.success(f"Participante '{p_name.strip()}' cadastrado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Informe o nome completo do participante.")

            # ========================================================
            # 2. CADASTRO EM MASSA (COLAR LISTA)
            # ========================================================
            with st.expander("🚀 Cadastro em Massa (Colar Lista de Nomes)", expanded=False):
                st.subheader("Importar Nomes Rapidamente")
                st.caption("Cole uma lista com múltiplos nomes (um por linha). O sistema cadastra todos com 1 clique.")
                names_text = st.text_area(
                    "Cole a lista de nomes:",
                    placeholder="Carlos Silva\nMariana Souza\nFelipe Santos\nBruna Oliveira\nLucas Pereira",
                    height=130
                )
                c_m1, c_m2, c_m3 = st.columns(3)
                bulk_cat = c_m1.selectbox("Categoria para todos:", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"], key="bulk_cat")
                bulk_fee = c_m2.number_input("Cota Inicial (R$):", value=default_fee, step=5.0, min_value=0.0, key="bulk_fee")
                bulk_conf = c_m3.checkbox("Presença Confirmada?", value=True, key="bulk_conf")

                if st.button("🚀 Cadastrar Todos os Nomes da Lista", type="primary"):
                    raw_lines = [line.strip() for line in names_text.splitlines() if line.strip()]
                    if raw_lines:
                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                        for name in raw_lines:
                            p_uuid = f"p_{str(uuid.uuid4())[:8]}"
                            participants.append({
                                "id": p_uuid,
                                "name": name,
                                "category": bulk_cat,
                                "confirmed": bulk_conf,
                                "fee": float(bulk_fee),
                                "paid": False,
                                "payment_method": "Pendente",
                                "paid_amount": 0.0,
                                "notes": "Cadastrado via importação em massa"
                            })
                            if bulk_cat == "Colaborador" and name.lower() not in collab_names_set:
                                collaborators.append({
                                    "id": f"c_{str(uuid.uuid4())[:8]}",
                                    "participant_id": p_uuid,
                                    "name": name,
                                    "role": "Apoio Geral / Colaborador",
                                    "phone": "",
                                    "email": ""
                                })
                                collab_names_set.add(name.lower())

                        save_event_data(event_id, "participants", participants, user_name, f"Cadastrou em massa {len(raw_lines)} participantes na categoria '{bulk_cat}'")
                        if bulk_cat == "Colaborador":
                            save_event_data(event_id, "collaborators", collaborators, user_name, f"Vinculou {len(raw_lines)} participantes como colaboradores")
                        st.success(f"{len(raw_lines)} participante(s) cadastrados com sucesso!")
                        st.rerun()
                    else:
                        st.error("Cole ao menos um nome na caixa acima para cadastrar.")

            # ========================================================
            # 3. PAINEL DE AÇÕES RÁPIDAS EM LOTE
            # ========================================================
            if total > 0:
                with st.expander("⚡ Ações Rápidas em Lote (Alterar Cota, Exclusão, Quitação e Promover Colaborador)", expanded=False):
                    st.caption("Execute operações em massa para múltiplos participantes cadastrados simultaneamente.")

                    b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs([
                        "💰 Alterar Cota em Lote",
                        "🗑️ Excluir em Lote",
                        "🟢 Dar Baixa / Quitar em Lote",
                        "🛠️ Definir como Colaboradores em Lote"
                    ])

                    # 3.1 ALTERAR COTA EM LOTE
                    with b_tab1:
                        st.write("**Atualizar o valor da cota para um grupo de participantes:**")
                        c_cota1, c_cota2 = st.columns([1, 2])
                        new_batch_fee = c_cota1.number_input("Novo Valor da Cota (R$):", value=default_fee, step=5.0, min_value=0.0, key="batch_new_fee")
                        batch_target = c_cota2.selectbox(
                            "Aplicar para quem?",
                            [
                                "Todos os Participantes",
                                "Apenas Alunos",
                                "Apenas Servidores/Professores",
                                "Apenas Convidados",
                                "Apenas Pendentes de Pagamento",
                                "Seleção Específica de Participantes"
                            ],
                            key="batch_target_sel"
                        )

                        selected_fee_pids = []
                        if batch_target == "Seleção Específica de Participantes":
                            selected_fee_pids = st.multiselect(
                                "Escolha os participantes:",
                                options=[p["id"] for p in participants],
                                format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - Cota: R$ {p.get('fee')}" for p in participants if p["id"] == x), x)
                            )

                        sync_paid_amount = st.checkbox("Ajustar também o valor pago de quem já havia quitado?", value=False, key="chk_sync_paid")

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

                    # 3.2 EXCLUIR EM LOTE
                    with b_tab2:
                        st.write("**Excluir múltiplos participantes de uma só vez:**")
                        filter_del_mode = st.radio(
                            "Forma de Seleção para Exclusão:",
                            ["Selecionar Manualmente", "Todos os Não Confirmados (Ausentes)", "Todos de uma Categoria"],
                            horizontal=True,
                            key="batch_del_mode"
                        )

                        del_candidates = []
                        if filter_del_mode == "Selecionar Manualmente":
                            del_candidates = st.multiselect(
                                "Selecione os participantes a serem excluídos:",
                                options=[p["id"] for p in participants],
                                format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - {'Pago' if p.get('paid') else 'Pendente'}" for p in participants if p["id"] == x), x),
                                key="batch_del_select"
                            )
                        elif filter_del_mode == "Todos os Não Confirmados (Ausentes)":
                            del_candidates = [p["id"] for p in participants if not p.get("confirmed")]
                            st.write(f"Participantes não confirmados encontrados: **{len(del_candidates)} pessoas**.")
                        else:
                            cat_to_del = st.selectbox("Escolha a categoria a excluir:", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"], key="batch_del_cat")
                            del_candidates = [p["id"] for p in participants if p.get("category") == cat_to_del]
                            st.write(f"Participantes na categoria '{cat_to_del}': **{len(del_candidates)} pessoas**.")

                        if del_candidates:
                            confirm_batch_del = st.checkbox(f"⚠️ Confirmar a exclusão definitiva de {len(del_candidates)} participante(s)?", value=False, key="chk_confirm_del")
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

                    # 3.3 QUITAÇÃO EM LOTE
                    with b_tab3:
                        st.write("**Dar baixa de pagamento para vários participantes de uma só vez:**")
                        c_q1, c_q2 = st.columns([2, 1])
                        unpaid_participants = [p for p in participants if not p.get("paid")]
                        selected_quit = c_q1.multiselect(
                            "Selecione quem efetuou o pagamento:",
                            options=[p["id"] for p in unpaid_participants],
                            format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - Cota R$ {p.get('fee')}" for p in unpaid_participants if p["id"] == x), x),
                            key="batch_quit_select"
                        )
                        forma_quit = c_q2.selectbox("Forma de Pagamento:", ["PIX", "Dinheiro", "Cartão", "Transferência", "Abatimento em Compras"], key="batch_quit_forma")

                        if st.button("🟢 Confirmar Quitação em Lote", type="primary"):
                            if selected_quit:
                                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                for p in participants:
                                    if p["id"] in selected_quit:
                                        p["paid"] = True
                                        p["payment_method"] = forma_quit
                                        p["paid_amount"] = float(p.get("fee", default_fee))
                                save_event_data(event_id, "participants", participants, user_name, f"Deu baixa de pagamento em lote para {len(selected_quit)} participantes via {forma_quit}")
                                st.success(f"Pagamento de {len(selected_quit)} participante(s) confirmado com sucesso!")
                                st.rerun()
                            else:
                                st.error("Selecione ao menos um participante para dar baixa.")

                    # 3.4 DEFINIR COMO COLABORADORES EM LOTE
                    with b_tab4:
                        st.write("**Definir múltiplos participantes como colaboradores da equipe:**")
                        st.caption("Eles serão incluídos na equipe de colaboradores sem precisar recadastrar nomes.")

                        b_collab_pids = st.multiselect(
                            "Selecione os participantes:",
                            options=[p["id"] for p in participants],
                            format_func=lambda x: next(
                                (f"{p['name']} ({p.get('category')})" + (" [Já é colaborador]" if p['name'].strip().lower() in collab_names_set else "")
                                 for p in participants if p["id"] == x), x
                            ),
                            key="batch_promote_collab_sel"
                        )

                        b_preset_role = st.selectbox(
                            "Função / Papel na Equipe para todos:",
                            [
                                "Equipe de Apoio Geral",
                                "Mestre Churrasqueiro & Churrasqueira",
                                "Chef de Acompanhamentos (Farofa / Vinagrete)",
                                "Compras de Carnes & Bebidas",
                                "Compras de Gelo & Descartáveis",
                                "Pão de Alho & Sobremesas",
                                "Recepção & Caixa",
                                "Limpeza & Organização",
                                "Outra Função Personalizada"
                            ],
                            key="batch_promote_role_sel"
                        )
                        if b_preset_role == "Outra Função Personalizada":
                            b_final_role = st.text_input("Digite a função personalizada:", value="Apoio Geral", key="batch_custom_role_txt")
                        else:
                            b_final_role = b_preset_role

                        b_chk_cat = st.checkbox("Atualizar categoria deles para 'Colaborador' na lista de participantes?", value=True, key="chk_batch_cat_promo")

                        if st.button("🛠️ Definir Selecionados como Colaboradores", type="primary"):
                            if b_collab_pids:
                                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                added_now = 0
                                for pid in b_collab_pids:
                                    part = next(p for p in participants if p["id"] == pid)
                                    if part["name"].strip().lower() not in collab_names_set and part["id"] not in collab_pids_set:
                                        collaborators.append({
                                            "id": f"c_{str(uuid.uuid4())[:8]}",
                                            "participant_id": part["id"],
                                            "name": part["name"].strip(),
                                            "role": b_final_role.strip() or "Apoio Geral",
                                            "phone": "",
                                            "email": ""
                                        })
                                        collab_names_set.add(part["name"].strip().lower())
                                        collab_pids_set.add(part["id"])
                                        added_now += 1
                                    if b_chk_cat:
                                        part["category"] = "Colaborador"

                                save_event_data(event_id, "collaborators", collaborators, user_name, f"Definiu em lote {len(b_collab_pids)} participantes como colaboradores ('{b_final_role}')")
                                if b_chk_cat:
                                    save_event_data(event_id, "participants", participants, user_name, f"Atualizou categoria de {len(b_collab_pids)} participantes para 'Colaborador'")
                                st.success(f"{len(b_collab_pids)} participante(s) definidos como colaboradores com sucesso!")
                                st.rerun()
                            else:
                                st.error("Selecione ao menos um participante.")

            # ========================================================
            # 4. EDIÇÃO DIRETA NA TABELA (st.data_editor)
            # ========================================================
            st.subheader("📋 Tabela de Participantes")
            st.info("💡 **Edição Direta:** Você pode alterar qualquer valor clicando diretamente nas células da tabela. **Dica:** Se você alterar a Categoria de uma pessoa para **Colaborador**, o sistema a adicionará automaticamente à equipe de colaboradores ao salvar!")

            col_s1, col_s2 = st.columns([1.5, 3])
            save_table_btn = col_s1.button("💾 Salvar Alterações da Tabela", type="primary", use_container_width=True)

            # Prepara DataFrame editável
            df_editable = pd.DataFrame([
                {
                    "id": p.get("id") or f"p_{str(uuid.uuid4())[:8]}",
                    "name": p.get("name", ""),
                    "category": p.get("category", "Aluno"),
                    "confirmed": bool(p.get("confirmed", True)),
                    "fee": float(p.get("fee", default_fee)),
                    "paid": bool(p.get("paid", False)),
                    "payment_method": p.get("payment_method", "Pendente"),
                    "paid_amount": float(p.get("paid_amount", 0.0)),
                    "notes": str(p.get("notes", "") or "")
                }
                for p in participants
            ])

            if df_editable.empty:
                df_editable = pd.DataFrame([{
                    "id": f"p_{str(uuid.uuid4())[:8]}",
                    "name": "",
                    "category": "Aluno",
                    "confirmed": True,
                    "fee": default_fee,
                    "paid": False,
                    "payment_method": "Pendente",
                    "paid_amount": 0.0,
                    "notes": ""
                }])

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
                collabs_added = 0

                for _, row in edited_df.iterrows():
                    name_val = str(row.get("name", "")).strip()
                    if not name_val:
                        continue  # ignora linhas em branco
                    row_id = str(row.get("id", "")).strip() or f"p_{str(uuid.uuid4())[:8]}"
                    cat_val = str(row.get("category", "Aluno"))
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
                        "category": cat_val,
                        "confirmed": bool(row.get("confirmed", True)),
                        "fee": row_fee,
                        "paid": is_paid,
                        "payment_method": str(row.get("payment_method", "Pendente")) if is_paid else "Pendente",
                        "paid_amount": row_paid_amt,
                        "notes": str(row.get("notes", "") or "")
                    })

                    # Sincronização inteligente: Se a categoria for Colaborador, adiciona automaticamente à equipe!
                    if cat_val == "Colaborador":
                        if row_id not in collab_pids_set and name_val.lower() not in collab_names_set:
                            collaborators.append({
                                "id": f"c_{str(uuid.uuid4())[:8]}",
                                "participant_id": row_id,
                                "name": name_val,
                                "role": "Apoio Geral / Colaborador",
                                "phone": "",
                                "email": ""
                            })
                            collab_names_set.add(name_val.lower())
                            collab_pids_set.add(row_id)
                            collabs_added += 1

                save_event_data(event_id, "participants", new_records, user_name, f"Atualizou tabela de participantes diretamente no editor ({len(new_records)} registros)")
                if collabs_added > 0:
                    save_event_data(event_id, "collaborators", collaborators, user_name, f"Adicionou automaticamente {collabs_added} participante(s) à equipe de colaboradores")
                
                msg = "Tabela salva com sucesso!"
                if collabs_added > 0:
                    msg += f" ({collabs_added} pessoa(s) adicionadas à equipe de colaboradores)"
                st.success(msg)
                st.rerun()

            # ========================================================
            # 5. EDIÇÃO INDIVIDUAL DETALHADA (SE JÁ HOUVER PARTICIPANTES)
            # ========================================================
            if total > 0:
                with st.expander("✏️ Editar ou Excluir Participante Específico (Formulário)"):
                    selected_p_id = st.selectbox(
                        "Selecione o participante:",
                        options=[p["id"] for p in participants],
                        format_func=lambda x: next((f"{p['name']} ({p.get('category')}) - {'Pago' if p.get('paid') else 'Pendente'}" for p in participants if p["id"] == x), x),
                        key="sel_p_indiv"
                    )
                    curr_p = next(p for p in participants if p["id"] == selected_p_id)
                    is_already_collab = curr_p["name"].strip().lower() in collab_names_set or curr_p["id"] in collab_pids_set

                    with st.form("form_edit_participant"):
                        e1, e2, e3 = st.columns([2, 1, 1])
                        new_name = e1.text_input("Nome", value=curr_p["name"])
                        new_cat = e2.selectbox("Categoria", ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"], index=["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"].index(curr_p.get("category", "Aluno")) if curr_p.get("category") in ["Aluno", "Servidor/Professor", "Convidado", "Colaborador", "Criança"] else 0)
                        new_fee = e3.number_input("Valor da Cota (R$)", value=float(curr_p.get("fee", default_fee)), step=5.0)

                        e4, e5, e6 = st.columns([1, 1, 2])
                        new_conf = e4.checkbox("Confirmado", value=bool(curr_p.get("confirmed", True)))
                        new_paid = e5.checkbox("Pago", value=bool(curr_p.get("paid", False)))
                        new_method = e6.selectbox("Forma Pagamento", ["PIX", "Dinheiro", "Cartão", "Abatimento em Compras", "Pendente"], index=0)
                        new_notes = st.text_input("Observações", value=curr_p.get("notes", ""))

                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            save_btn = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                        with col_btn2:
                            promote_btn = st.form_submit_button(
                                "🛠️ " + ("Já é Colaborador" if is_already_collab else "Tornar Colaborador"),
                                disabled=is_already_collab,
                                use_container_width=True
                            )
                        with col_btn3:
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

                            # Se mudou categoria para Colaborador e não estava na lista, adiciona
                            if new_cat == "Colaborador" and not is_already_collab:
                                collaborators.append({
                                    "id": f"c_{str(uuid.uuid4())[:8]}",
                                    "participant_id": curr_p["id"],
                                    "name": new_name.strip(),
                                    "role": "Apoio Geral / Colaborador",
                                    "phone": "",
                                    "email": ""
                                })
                                save_event_data(event_id, "collaborators", collaborators, user_name, f"Adicionou '{new_name}' à equipe de colaboradores")

                            st.success(f"Participante '{new_name}' atualizado!")
                            st.rerun()

                        if promote_btn and not is_already_collab:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            curr_p["category"] = "Colaborador"
                            collaborators.append({
                                "id": f"c_{str(uuid.uuid4())[:8]}",
                                "participant_id": curr_p["id"],
                                "name": curr_p["name"].strip(),
                                "role": "Apoio Geral / Colaborador",
                                "phone": "",
                                "email": ""
                            })
                            save_event_data(event_id, "participants", participants, user_name, f"Definiu '{curr_p['name']}' como colaborador")
                            save_event_data(event_id, "collaborators", collaborators, user_name, f"Vinculou '{curr_p['name']}' à equipe de colaboradores")
                            st.success(f"'{curr_p['name']}' agora faz parte da equipe de colaboradores!")
                            st.rerun()

                        if del_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            participants = [p for p in participants if p["id"] != selected_p_id]
                            save_event_data(event_id, "participants", participants, user_name, f"Excluiu participante '{curr_p['name']}'")
                            st.warning(f"Participante '{curr_p['name']}' excluído.")
                            st.rerun()
        else:
            # Modo Somente Leitura
            st.warning("👀 **Você está conectado em Modo Visualizador (Somente Leitura).** Para adicionar ou editar participantes, faça login como **Organizador Master** ou **Colaborador** usando o botão **🔑 Fazer Login** no canto superior direito.")
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
                st.info("Nenhum participante registrado neste evento ainda.")

    # ==========================
    # ABA 2: COLABORADORES
    # ==========================
    with tab2:
        st.subheader("🛠️ Equipe de Colaboradores e Organizadores")
        st.caption("Pessoas responsáveis por compras, churrasqueira, preparo de acompanhamentos, limpeza e caixa.")

        # Participantes que ainda não foram vinculados como colaboradores
        available_participants = [
            p for p in participants
            if p["id"] not in collab_pids_set and p["name"].strip().lower() not in collab_names_set
        ]

        if can_edit():
            # ========================================================
            # 1. VINCULAR PARTICIPANTE EXISTENTE (SEM RECADASTRO)
            # ========================================================
            with st.expander("⚡ Definir Participante como Colaborador (Sem Recadastrar)", expanded=True):
                if not participants:
                    st.info("ℹ️ Não há participantes cadastrados no evento ainda. Cadastre participantes na primeira aba ou cadastre um colaborador externo abaixo.")
                elif not available_participants:
                    st.success("🎉 Todos os participantes cadastrados neste evento já fazem parte da equipe de colaboradores!")
                else:
                    st.write("**Selecione um participante já cadastrado para torná-lo colaborador:**")

                    link_mode = st.radio(
                        "Forma de Vinculação:",
                        ["Individual (com função detalhada)", "Em Lote (múltiplos participantes)"],
                        horizontal=True,
                        key="tab2_link_mode"
                    )

                    if link_mode == "Individual (com função detalhada)":
                        with st.form("form_link_individual_collab"):
                            c_part_id = st.selectbox(
                                "Escolha o Participante *",
                                options=[p["id"] for p in available_participants],
                                format_func=lambda x: next(f"👤 {p['name']} ({p.get('category')})" for p in available_participants if p["id"] == x),
                                key="sel_part_to_collab_tab2"
                            )
                            chosen_part = next(p for p in available_participants if p["id"] == c_part_id)

                            c_r1, c_r2 = st.columns([1, 1])
                            preset_role = c_r1.selectbox(
                                "Função / Responsabilidade no Churrasco *",
                                [
                                    "Mestre Churrasqueiro & Churrasqueira",
                                    "Chef de Acompanhamentos (Farofa / Vinagrete)",
                                    "Compras de Carnes & Insumos",
                                    "Compras de Bebidas & Gelo",
                                    "Pão de Alho & Sobremesas",
                                    "Recepção & Fechamento de Caixa",
                                    "Apoio Geral e Logística",
                                    "Limpeza e Organização",
                                    "Outra Função Personalizada"
                                ],
                                key="tab2_preset_role"
                            )
                            if preset_role == "Outra Função Personalizada":
                                final_role_ind = c_r2.text_input("Especifique a função:", placeholder="Ex: Fotógrafo, Som, Decoração", key="tab2_custom_role")
                            else:
                                final_role_ind = preset_role

                            c_c1, c_c2 = st.columns(2)
                            c_phone = c_c1.text_input("WhatsApp / Telefone de Contato (opcional)", key="tab2_c_phone")
                            c_email = c_c2.text_input("E-mail de Contato (opcional)", key="tab2_c_email")

                            c_update_cat = st.checkbox("Atualizar categoria deste participante para 'Colaborador'?", value=True, key="tab2_c_update_cat")

                            if st.form_submit_button("🚀 Confirmar e Definir como Colaborador", type="primary", use_container_width=True):
                                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                new_collab = {
                                    "id": f"c_{str(uuid.uuid4())[:8]}",
                                    "participant_id": chosen_part["id"],
                                    "name": chosen_part["name"].strip(),
                                    "role": final_role_ind.strip() or "Apoio Geral",
                                    "phone": c_phone.strip(),
                                    "email": c_email.strip()
                                }
                                collaborators.append(new_collab)
                                save_event_data(event_id, "collaborators", collaborators, user_name, f"Definiu participante '{chosen_part['name']}' como colaborador ('{new_collab['role']}')")

                                if c_update_cat and chosen_part.get("category") != "Colaborador":
                                    for p in participants:
                                        if p["id"] == chosen_part["id"]:
                                            p["category"] = "Colaborador"
                                    save_event_data(event_id, "participants", participants, user_name, f"Atualizou categoria de '{chosen_part['name']}' para 'Colaborador'")

                                st.success(f"'{chosen_part['name']}' agora é colaborador com a função '{new_collab['role']}'!")
                                st.rerun()

                    else:
                        # Modo Em Lote na Aba 2
                        with st.form("form_link_batch_tab2"):
                            selected_batch_pids = st.multiselect(
                                "Selecione os participantes para tornar colaboradores *",
                                options=[p["id"] for p in available_participants],
                                format_func=lambda x: next(f"👤 {p['name']} ({p.get('category')})" for p in available_participants if p["id"] == x),
                                key="tab2_batch_pids"
                            )
                            batch_role = st.text_input("Função / Papel da Equipe *", value="Equipe de Apoio e Logística", key="tab2_batch_role")
                            batch_update_cat = st.checkbox("Atualizar categoria de todos para 'Colaborador'?", value=True, key="tab2_batch_chk_cat")

                            if st.form_submit_button("🚀 Definir Selecionados como Colaboradores", type="primary", use_container_width=True):
                                if selected_batch_pids:
                                    user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                    for pid in selected_batch_pids:
                                        p_obj = next(p for p in available_participants if p["id"] == pid)
                                        collaborators.append({
                                            "id": f"c_{str(uuid.uuid4())[:8]}",
                                            "participant_id": p_obj["id"],
                                            "name": p_obj["name"].strip(),
                                            "role": batch_role.strip() or "Apoio Geral",
                                            "phone": "",
                                            "email": ""
                                        })
                                        if batch_update_cat:
                                            for p in participants:
                                                if p["id"] == pid:
                                                    p["category"] = "Colaborador"

                                    save_event_data(event_id, "collaborators", collaborators, user_name, f"Definiu em lote {len(selected_batch_pids)} participantes como colaboradores ('{batch_role}')")
                                    if batch_update_cat:
                                        save_event_data(event_id, "participants", participants, user_name, f"Atualizou categoria de {len(selected_batch_pids)} participantes para 'Colaborador'")

                                    st.success(f"{len(selected_batch_pids)} participante(s) definidos como colaboradores com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Selecione ao menos um participante.")

            # ========================================================
            # 2. CADASTRAR COLABORADOR EXTERNO (NÃO PARTICIPANTE)
            # ========================================================
            with st.expander("➕ Cadastrar Colaborador Externo (Não Participante)", expanded=False):
                st.caption("Utilize para terceirizados ou voluntários que não estão na lista de consumidores (ex: churrasqueiro profissional contratado, garçom, DJ, etc.).")
                with st.form("form_add_ext_collab", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    collab_name = c1.text_input("Nome do Colaborador *")
                    collab_role = c2.text_input("Função / Papel (ex: Churrasqueiro Profissional, DJ, Segurança)")
                    
                    c3, c4 = st.columns(2)
                    collab_phone = c3.text_input("WhatsApp / Telefone")
                    collab_email = c4.text_input("E-mail")

                    if st.form_submit_button("Cadastrar Colaborador Externo", type="primary"):
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
                            save_event_data(event_id, "collaborators", collaborators, user_name, f"Cadastrou colaborador externo '{collab_name}'")
                            st.success(f"Colaborador externo '{collab_name}' cadastrado!")
                            st.rerun()
                        else:
                            st.error("Informe o nome do colaborador.")

            # ========================================================
            # 3. EDITAR / DESVINCULAR COLABORADOR
            # ========================================================
            if collaborators:
                with st.expander("✏️ Editar Função ou Desvincular Colaborador", expanded=False):
                    sel_collab_id = st.selectbox(
                        "Selecione o colaborador:",
                        options=[c["id"] for c in collaborators],
                        format_func=lambda x: next(f"{c['name']} - {c.get('role', 'Apoio')}" for c in collaborators if c["id"] == x),
                        key="sel_edit_collab_tab2"
                    )
                    curr_c = next(c for c in collaborators if c["id"] == sel_collab_id)

                    with st.form("form_edit_collab_details"):
                        ed1, ed2 = st.columns(2)
                        new_c_name = ed1.text_input("Nome", value=curr_c["name"])
                        new_c_role = ed2.text_input("Função / Papel", value=curr_c.get("role", ""))

                        ed3, ed4 = st.columns(2)
                        new_c_phone = ed3.text_input("Telefone", value=curr_c.get("phone", ""))
                        new_c_email = ed4.text_input("E-mail", value=curr_c.get("email", ""))

                        ced_a, ced_b = st.columns(2)
                        with ced_a:
                            save_collab_btn = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                        with ced_b:
                            remove_collab_btn = st.form_submit_button("🗑️ Desvincular da Equipe", use_container_width=True)

                        if save_collab_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            curr_c["name"] = new_c_name.strip()
                            curr_c["role"] = new_c_role.strip()
                            curr_c["phone"] = new_c_phone.strip()
                            curr_c["email"] = new_c_email.strip()
                            save_event_data(event_id, "collaborators", collaborators, user_name, f"Atualizou dados do colaborador '{curr_c['name']}'")
                            st.success("Colaborador atualizado com sucesso!")
                            st.rerun()

                        if remove_collab_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            collaborators = [c for c in collaborators if c["id"] != sel_collab_id]
                            save_event_data(event_id, "collaborators", collaborators, user_name, f"Desvinculou colaborador '{curr_c['name']}' da equipe")
                            st.warning(f"'{curr_c['name']}' foi desvinculado da equipe de colaboradores (o participante continua ativo no evento).")
                            st.rerun()

        # ========================================================
        # TABELA DE COLABORADORES
        # ========================================================
        if collaborators:
            part_dict_by_name = {p["name"].strip().lower(): p for p in participants}
            part_dict_by_id = {p["id"]: p for p in participants}

            df_collabs = pd.DataFrame([
                {
                    "Nome": c["name"],
                    "Função / Responsabilidade": c.get("role", "Apoio"),
                    "Origem": "👤 Participante Vinculado" if (c.get("participant_id") in part_dict_by_id or c["name"].strip().lower() in part_dict_by_name) else "🏢 Externo (Contratado/Apoio)",
                    "Telefone / Contato": c.get("phone") or (part_dict_by_id.get(c.get("participant_id"), {}).get("notes", "-") if c.get("participant_id") else "-"),
                    "E-mail": c.get("email", "-")
                }
                for c in collaborators
            ])
            st.dataframe(df_collabs, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum colaborador registrado ainda neste evento.")
