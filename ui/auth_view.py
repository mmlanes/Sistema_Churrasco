import streamlit as st
from services.auth_service import authenticate, get_all_users


def init_session_state():
    if "user" not in st.session_state:
        # Padrão: convidado / visualizador
        st.session_state["user"] = {
            "username": "convidado",
            "name": "Convidado (Modo Leitura)",
            "role": "visualizador"
        }
    if "active_event_id" not in st.session_state:
        st.session_state["active_event_id"] = None


def render_user_header():
    """Renderiza a barra superior de identificação do usuário e botão de login/logout."""
    user = st.session_state.get("user", {})
    role = user.get("role", "visualizador")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if role == "master":
            badge_html = "<span style='color: #60A5FA; font-weight: bold;'>👑 ORGANIZADOR MASTER</span>"
            border_color = "#3B82F6"
        elif role == "colaborador":
            badge_html = "<span style='color: #34D399; font-weight: bold;'>🛠️ COLABORADOR</span>"
            border_color = "#10B981"
        else:
            badge_html = "<span style='color: #9CA3AF; font-weight: bold;'>👀 VISUALIZADOR (Somente Leitura)</span>"
            border_color = "#6B7280"

        st.markdown(
            f"<div style='background: rgba(127, 127, 127, 0.12); color: inherit; padding: 10px 16px; border-radius: 8px; border-left: 5px solid {border_color}; border-top: 1px solid rgba(127,127,127,0.2); border-right: 1px solid rgba(127,127,127,0.2); border-bottom: 1px solid rgba(127,127,127,0.2); font-size: 0.95rem; line-height: 1.5;'>"
            f"Conectado como: <strong>{user.get('name', 'Convidado')}</strong> &nbsp;|&nbsp; Permissão: {badge_html}</div>",
            unsafe_allow_html=True
        )

    with col2:
        if role == "visualizador":
            with st.popover("🔑 Fazer Login"):
                login_form()
        else:
            if st.button("🚪 Sair / Trocar Usuário", use_container_width=True):
                st.session_state["user"] = {
                    "username": "convidado",
                    "name": "Convidado (Modo Leitura)",
                    "role": "visualizador"
                }
                st.rerun()


def login_form():
    st.subheader("Acesso ao Sistema")
    st.caption("Faça login para editar valores, gerenciar tarefas ou administrar o evento.")
    username = st.text_input("Usuário", key="login_user").strip().lower()
    password = st.text_input("Senha", type="password", key="login_pass")
    
    if st.button("Entrar", type="primary", use_container_width=True):
        u = authenticate(username, password)
        if u:
            st.session_state["user"] = u
            st.success(f"Bem-vindo(a), {u['name']}!")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")

    st.markdown("---")
    with st.expander("📋 Ver Contas e Senhas Cadastradas"):
        all_u = get_all_users()
        for uname, udata in all_u.items():
            urole = "👑 Master" if udata["role"] == "master" else ("🛠️ Colab" if udata["role"] == "colaborador" else "👀 Leitura")
            upass = udata.get("plain_password", "admin123" if uname == "admin" else ("1234" if uname == "convidado" else f"{uname}123"))
            st.markdown(f"- **`{uname}`** | Senha: **`{upass}`** *({urole})*")


def can_edit() -> bool:
    """Verifica se o usuário atual tem permissão de escrita (master ou colaborador)."""
    role = st.session_state.get("user", {}).get("role", "visualizador")
    return role in ["master", "colaborador"]


def is_master() -> bool:
    """Verifica se o usuário atual é Master/Administrador."""
    role = st.session_state.get("user", {}).get("role", "visualizador")
    return role == "master"

