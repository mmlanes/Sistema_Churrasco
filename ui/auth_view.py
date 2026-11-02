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
            badge = "👑 **ORGANIZADOR MASTER**"
            color = "#1E3A8A"
        elif role == "colaborador":
            badge = "🛠️ **COLABORADOR**"
            color = "#047857"
        else:
            badge = "👀 **VISUALIZADOR (Somente Leitura)**"
            color = "#6B7280"

        st.markdown(
            f"<div style='background-color:#F3F4F6; padding:8px 14px; border-radius:8px; border-left: 5px solid {color};'>"
            f"Conectado como: <b>{user.get('name', 'Convidado')}</b> &nbsp;|&nbsp; Permissão: {badge}</div>",
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
    st.caption("💡 **Usuários iniciais do sistema:**")
    st.caption("- **Master:** `admin` (senha `admin123`) ou `matusalem` (senha `matu123`)")
    st.caption("- **Colaboradores:** `manuela` (senha `manu123`), `marcelle` (senha `marcelle123`), `julia` (senha `julia123`)")
    st.caption("- **Visualizador:** `convidado` (senha `1234`)")


def can_edit() -> bool:
    """Verifica se o usuário atual tem permissão de escrita (master ou colaborador)."""
    role = st.session_state.get("user", {}).get("role", "visualizador")
    return role in ["master", "colaborador"]


def is_master() -> bool:
    """Verifica se o usuário atual é Master/Administrador."""
    role = st.session_state.get("user", {}).get("role", "visualizador")
    return role == "master"

