from datetime import datetime
import pandas as pd
import streamlit as st
from services.auth_service import delete_user, get_all_users, save_user
from services.event_service import list_events
from services.storage_service import get_audit_logs
from ui.auth_view import is_master


def render_admin(event_id: str):
    st.title("⚙️ Administração, Usuários e Permissões de Eventos")
    st.caption("Controle exclusivo Master: Defina quais eventos cada usuário ou colaborador pode acessar e associe visualizadores a eventos únicos.")

    if not is_master():
        st.error("⛔ Acesso Restrito: Apenas usuários com perfil Master podem gerenciar contas e configurações avançadas.")
        return

    tab1, tab2, tab3 = st.tabs([
        "👥 Gestão de Usuários e Permissões",
        "📜 Log de Auditoria do Evento",
        "💾 Backup e Migração de Dados"
    ])

    all_events = list_events()
    ev_dict = {e["id"]: f"{e['name']} ({e.get('date', '')})" for e in all_events}

    # ========================================================
    # ABA 1: GESTÃO DE USUÁRIOS
    # ========================================================
    with tab1:
        st.subheader("Usuários Cadastrados e Eventos Autorizados")
        st.caption("Visualize logins, senhas e a lista de eventos permitidos para cada conta.")
        users = get_all_users()

        user_rows = []
        for u in users.values():
            role = u.get("role", "visualizador")
            allowed = u.get("allowed_events", [])
            
            if role == "master":
                eventos_txt = "🌟 Todos os Eventos (Acesso Livre)"
            elif role == "visualizador":
                ev_name = ev_dict.get(allowed[0], allowed[0]) if allowed else "Nenhum"
                eventos_txt = f"🔒 {ev_name} (Apenas 1)"
            else:
                ev_names = [ev_dict.get(eid, eid) for eid in allowed] if allowed else ["Nenhum"]
                eventos_txt = ", ".join(ev_names)

            user_rows.append({
                "Usuário (Login)": u["username"],
                "Nome Completo": u["name"],
                "Perfil de Acesso": "👑 Master" if role == "master" else ("🛠️ Colaborador" if role == "colaborador" else "👀 Visualizador"),
                "Senha Atual": u.get("plain_password", "admin123" if u["username"] == "admin" else ("1234" if u["username"] == "convidado" else f"{u['username']}123")),
                "Eventos Permitidos": eventos_txt,
                "E-mail": u.get("email", "-"),
                "Status": "Ativo" if u.get("active", True) else "Inativo"
            })

        df_users = pd.DataFrame(user_rows)
        st.dataframe(df_users, use_container_width=True, hide_index=True)

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ➕ Criar ou Atualizar Usuário e Permissões")
            with st.form("form_save_user", clear_on_submit=True):
                u_login = st.text_input("Login (Username) *", placeholder="ex: joao, maria, professor").strip().lower()
                u_name = st.text_input("Nome Completo *")
                u_role = st.selectbox("Perfil de Permissão", ["colaborador", "master", "visualizador"], format_func=lambda x: "👑 Master (Acesso Total)" if x == "master" else ("🛠️ Colaborador (Edita Valores/Tarefas)" if x == "colaborador" else "👀 Visualizador (Somente Leitura - 1 Evento)"))
                u_email = st.text_input("E-mail")
                u_pass = st.text_input("Senha *", placeholder="Digite a senha desejada")

                # Seleção de Eventos conforme a regra de perfil
                st.write("**Definição de Acesso a Eventos:**")
                if u_role == "master":
                    st.info("👑 Usuários Master têm acesso a todos os eventos automaticamente.")
                    selected_evs = ["*"]
                elif u_role == "visualizador":
                    st.caption("Regra: Cada login de visualizador pode ver apenas **um único evento associado**.")
                    ev_opt = st.selectbox(
                        "Evento Associado (Apenas 1) *",
                        options=[e["id"] for e in all_events],
                        format_func=lambda x: ev_dict.get(x, x),
                        key="ev_sel_single"
                    )
                    selected_evs = [ev_opt] if ev_opt else []
                else:
                    st.caption("Colaboradores: Selecione quais eventos este usuário terá permissão para visualizar e atuar.")
                    multi_evs = st.multiselect(
                        "Eventos Permitidos *",
                        options=[e["id"] for e in all_events],
                        format_func=lambda x: ev_dict.get(x, x),
                        default=[e["id"] for e in all_events],
                        key="ev_sel_multi"
                    )
                    selected_evs = multi_evs

                if st.form_submit_button("Salvar Usuário e Permissões", type="primary", use_container_width=True):
                    if u_login and u_name:
                        save_user(
                            username=u_login,
                            name=u_name,
                            role=u_role,
                            password=u_pass if u_pass else "123456",
                            email=u_email,
                            allowed_events=selected_evs
                        )
                        st.success(f"Usuário '{u_login}' salvo com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe o login e o nome completo.")

        with c2:
            st.markdown("#### 🔑 Alterar Eventos ou Senha de Usuário Existente")
            st.caption("Atualize rapidamente os eventos autorizados ou a senha de qualquer usuário.")
            with st.form("form_reset_password"):
                target_user = st.selectbox("Selecione o usuário:", options=list(users.keys()), format_func=lambda x: f"{users[x]['name']} ({x})")
                u_data = users[target_user]
                new_quick_pass = st.text_input("Nova Senha (deixe vazio para manter):", placeholder="Digite para trocar a senha")

                # Seleção de eventos para atualização
                target_role = u_data.get("role", "visualizador")
                if target_role == "master":
                    st.info("Usuário Master possui acesso livre a todos os eventos.")
                    up_events = ["*"]
                elif target_role == "visualizador":
                    curr_allowed = u_data.get("allowed_events", [])
                    default_idx = [e["id"] for e in all_events].index(curr_allowed[0]) if curr_allowed and curr_allowed[0] in [e["id"] for e in all_events] else 0
                    up_ev = st.selectbox(
                        "Evento Associado (Apenas 1):",
                        options=[e["id"] for e in all_events],
                        format_func=lambda x: ev_dict.get(x, x),
                        index=default_idx
                    )
                    up_events = [up_ev]
                else:
                    curr_allowed = u_data.get("allowed_events", [e["id"] for e in all_events])
                    valid_defaults = [eid for eid in curr_allowed if eid in [e["id"] for e in all_events]]
                    up_events = st.multiselect(
                        "Eventos Permitidos:",
                        options=[e["id"] for e in all_events],
                        format_func=lambda x: ev_dict.get(x, x),
                        default=valid_defaults
                    )

                if st.form_submit_button("Atualizar Cadastro do Usuário", type="primary", use_container_width=True):
                    save_user(
                        username=target_user,
                        name=u_data["name"],
                        role=u_data["role"],
                        password=new_quick_pass.strip() if new_quick_pass.strip() else None,
                        email=u_data.get("email", ""),
                        allowed_events=up_events
                    )
                    st.success(f"Cadastro do usuário '{target_user}' atualizado com sucesso!")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### 🗑️ Excluir Usuário")
            st.caption("Regra de segurança: O sistema não permite excluir o último usuário Master.")
            del_login = st.selectbox("Selecione o usuário para remover:", options=[u for u in users.keys() if u != "admin"])
            if st.button("Confirmar Exclusão de Usuário", type="secondary"):
                if delete_user(del_login):
                    st.warning(f"Usuário '{del_login}' excluído.")
                    st.rerun()
                else:
                    st.error("Não foi possível excluir o usuário. Deve haver no mínimo um Master ativo.")

    # ========================================================
    # ABA 2: LOG DE AUDITORIA
    # ========================================================
    with tab2:
        st.subheader("📜 Histórico de Alterações Auditadas do Evento")
        st.caption("Rastreamento de quem alterou valores, adicionou ou excluiu itens, tarefas, despesas ou participantes.")

        logs = get_audit_logs(event_id)
        if not logs:
            st.info("Nenhum registro de auditoria neste evento ainda.")
        else:
            df_logs = pd.DataFrame([
                {
                    "Data e Hora": l.get("timestamp"),
                    "Usuário Responsável": l.get("user"),
                    "Ação": l.get("action"),
                    "Detalhes da Alteração": l.get("details")
                }
                for l in logs
            ])
            st.dataframe(df_logs, use_container_width=True, hide_index=True)

    # ========================================================
    # ABA 3: BACKUP E MIGRAÇÃO DE DADOS
    # ========================================================
    with tab3:
        st.subheader("💾 Exportação e Backup Completo da Base de Dados")
        st.caption("Exporte todos os dados cadastrados em formato de texto padronizado (JSON) para arquivamento ou migração para outra plataforma.")

        from services.backup_service import (
            export_full_database_json_bytes,
            export_event_database_json_bytes,
            export_full_database_zip,
            import_database_from_json
        )

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            st.markdown(
                """
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 10px;">
                    <h4 style="margin-top: 0; color: #1E293B;">📄 Base Completa do Sistema (JSON)</h4>
                    <p style="font-size: 0.9rem; color: #475569;">
                        Arquivo único de texto contendo <b>todos os eventos</b> (participantes, compras, carnes, bebidas, receitas, financeiro) e <b>todos os usuários e permissões</b>.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            full_json_bytes = export_full_database_json_bytes()
            st.download_button(
                label="📥 Baixar Base Completa (.json)",
                data=full_json_bytes,
                file_name=f"backup_completo_churrasco_{ts_str}.json",
                mime="application/json",
                type="primary",
                use_container_width=True
            )
            st.caption(f"Tamanho: {len(full_json_bytes)/1024:.1f} KB | Formato: JSON (UTF-8 legível)")

        with col_b2:
            st.markdown(
                """
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 10px;">
                    <h4 style="margin-top: 0; color: #1E293B;">📦 Pacote Completo com Fotos (.ZIP)</h4>
                    <p style="font-size: 0.9rem; color: #475569;">
                        Gera um arquivo compacto contendo o JSON consolidado, arquivos individuais por evento e <b>todas as fotos de notas fiscais e comprovantes</b>.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            zip_bytes = export_full_database_zip()
            st.download_button(
                label="📦 Baixar Backup Completo c/ Fotos (.zip)",
                data=zip_bytes,
                file_name=f"backup_completo_churrasco_{ts_str}.zip",
                mime="application/zip",
                use_container_width=True
            )
            st.caption(f"Tamanho: {len(zip_bytes)/1024:.1f} KB | Inclui JSONs e Imagens de Recibos")

        st.markdown("---")

        # Seção de Exportação de Evento Individual
        st.markdown("#### 🎯 Exportar um Evento Específico em JSON")
        st.caption("Selecione um evento para baixar apenas os dados pertinentes a ele em arquivo de texto JSON:")

        col_ev_sel, col_ev_btn = st.columns([2, 1])
        with col_ev_sel:
            selected_export_eid = st.selectbox(
                "Selecione o evento para exportação:",
                options=[e["id"] for e in all_events],
                format_func=lambda x: ev_dict.get(x, x),
                key="sel_export_ev"
            )
        with col_ev_btn:
            st.write("")
            st.write("")
            if selected_export_eid:
                ev_json_bytes = export_event_database_json_bytes(selected_export_eid)
                st.download_button(
                    label="📥 Baixar Evento (.json)",
                    data=ev_json_bytes,
                    file_name=f"evento_{selected_export_eid}_{ts_str}.json",
                    mime="application/json",
                    use_container_width=True
                )

        st.markdown("---")

        # Seção de Importação / Migração
        st.markdown("#### 🔄 Restaurar / Migrar Base de Dados (Importação de JSON)")
        st.caption("Deseja migrar seus dados para outra máquina ou restaurar um backup prévio? Selecione o arquivo JSON exportado:")

        uploaded_backup = st.file_uploader(
            "Enviar arquivo JSON de backup:",
            type=["json"],
            key="upload_backup_file"
        )
        if uploaded_backup is not None:
            if st.button("🚀 Confirmar Restauração / Migração dos Dados", type="secondary"):
                current_user = st.session_state.get("user", {}).get("name", "Admin Master")
                file_content = uploaded_backup.read()
                success, msg, stats = import_database_from_json(file_content, current_user=current_user)
                if success:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

