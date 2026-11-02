import pandas as pd
import streamlit as st
from services.auth_service import delete_user, get_all_users, save_user
from services.storage_service import get_audit_logs
from ui.auth_view import is_master


def render_admin(event_id: str):
    st.title("⚙️ Administração, Usuários e Auditoria")
    st.caption("Controle de acessos, administradores Masters, contas de colaboradores e histórico completo de alterações auditadas.")

    if not is_master():
        st.error("⛔ Acesso Restrito: Apenas usuários com perfil Master podem gerenciar contas e configurações avançadas.")
        return

    tab1, tab2 = st.tabs(["👥 Gestão de Usuários e Permissões", "📜 Log de Auditoria do Evento"])

    # ========================================================
    # ABA 1: GESTÃO DE USUÁRIOS
    # ========================================================
    with tab1:
        st.subheader("Usuários Cadastrados no Sistema")
        users = get_all_users()

        df_users = pd.DataFrame([
            {
                "Usuário (Login)": u["username"],
                "Nome Completo": u["name"],
                "Perfil de Acesso": "👑 Master" if u["role"] == "master" else ("🛠️ Colaborador" if u["role"] == "colaborador" else "👀 Visualizador"),
                "E-mail": u.get("email", "-"),
                "Status": "Ativo" if u.get("active", True) else "Inativo"
            }
            for u in users.values()
        ])
        st.dataframe(df_users, use_container_width=True, hide_index=True)

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ➕ Criar ou Atualizar Usuário")
            with st.form("form_save_user", clear_on_submit=True):
                u_login = st.text_input("Login (Username) *").strip().lower()
                u_name = st.text_input("Nome Completo *")
                u_role = st.selectbox("Perfil de Permissão", ["colaborador", "master", "visualizador"], format_func=lambda x: "👑 Master (Acesso Total)" if x == "master" else ("🛠️ Colaborador (Edita Valores/Tarefas)" if x == "colaborador" else "👀 Visualizador (Somente Leitura)"))
                u_email = st.text_input("E-mail")
                u_pass = st.text_input("Senha (deixe em branco para manter se for edição)", type="password")

                if st.form_submit_button("Salvar Usuário", type="primary"):
                    if u_login and u_name:
                        save_user(u_login, u_name, u_role, u_pass if u_pass else None, u_email)
                        st.success(f"Usuário '{u_login}' salvo com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe o login e o nome completo.")

        with c2:
            st.markdown("#### 🗑️ Excluir Usuário")
            st.caption("Regra de segurança: O sistema não permite excluir o último usuário Master.")
            del_login = st.selectbox("Selecione o usuário:", options=[u for u in users.keys() if u != "admin"])
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

