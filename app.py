import streamlit as st

# Configuração da página - deve ser o primeiro comando Streamlit
st.set_page_config(
    page_title="Calculadora & Gestão de Churrasco",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="expanded"
)

from config import APP_TITLE
from services.excel_importer import bootstrap_demo_event_if_needed
from services.event_service import get_event, verify_event_password
from ui.admin_view import render_admin
from ui.auth_view import can_edit, init_session_state, is_master, render_user_header
from ui.cashflow_view import render_cashflow
from ui.consumables_view import render_consumables
from ui.dashboard_view import render_dashboard
from ui.event_selector import render_event_selector
from ui.participants_view import render_participants
from ui.reports_view import render_reports
from ui.suggestions_view import render_suggestions
from ui.suppliers_view import render_suppliers


def main():
    # Inicializa sessão e banco de dados inicial (com importação do Excel histórico)
    init_session_state()
    initial_event_id = bootstrap_demo_event_if_needed()
    if not st.session_state.get("active_event_id"):
        st.session_state["active_event_id"] = initial_event_id

    # Barra superior com usuário logado e seletor de eventos
    render_user_header()
    st.write("")
    active_event_id = render_event_selector()

    if not active_event_id:
        st.warning("Selecione ou crie um evento para começar.")
        return

    # Verificação da Senha Geral do Evento
    event_meta = get_event(active_event_id) or {}
    unlocked_events = st.session_state.setdefault("unlocked_events", set())
    event_is_unlocked = is_master() or (active_event_id in unlocked_events)

    if not event_is_unlocked:
        st.markdown("---")
        _, col_box, _ = st.columns([1, 2, 1])
        with col_box:
            st.markdown(
                f"""
                <div style="background: rgba(127,127,127,0.12); padding: 26px; border-radius: 12px; border-left: 6px solid #F59E0B; border: 1px solid rgba(127,127,127,0.2); text-align: center;">
                    <h2 style="margin-top:0;">🔒 Evento Protegido por Senha</h2>
                    <h3 style="color: #60A5FA; margin-bottom: 8px;">{event_meta.get('name', 'Evento')}</h3>
                    <p style="opacity: 0.9; font-size: 0.95rem;">Para visualizar este evento, participantes, consumíveis e relatórios, informe a <b>senha geral de acesso</b> do evento.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write("")
            st.info(f"💡 **Senha deste evento:** `{event_meta.get('access_password', 'churras2025')}` ou `1234`")

            with st.form("form_event_lock"):
                entered_pwd = st.text_input("Senha Geral do Evento:", type="password", key=f"input_lock_{active_event_id}", placeholder="Digite a senha geral do evento (ex: churras2025 ou 1234)")
                submit_unlock = st.form_submit_button("🔓 Desbloquear e Acessar Evento", type="primary", use_container_width=True)
                if submit_unlock:
                    if verify_event_password(active_event_id, entered_pwd):
                        unlocked_events.add(active_event_id)
                        st.success("Senha correta! Acesso liberado.")
                        st.rerun()
                    else:
                        st.error("Senha incorreta. Solicite a senha aos organizadores do evento.")
            st.caption("💡 Se você for o Administrador Master, faça login na barra superior (botão '🔑 Fazer Login') para acessar diretamente e alterar esta senha.")
        return

    # Menu de Navegação na Sidebar
    with st.sidebar:
        st.markdown(f"### {APP_TITLE}")
        st.caption("Sistema Completo de Gestão, Orçamento e Prestação de Contas")

        nav_options = [
            "📊 Painel Geral (Dashboard)",
            "👥 Participantes & Colaboradores",
            "🥩 Consumíveis, Bebidas & Receitas",
            "📌 Tarefas dos Colaboradores",
            "💵 Caixa & Comprovantes Fiscais",
            "🏬 Fornecedores & Fotos",
            "📄 Relatórios & Emissão PDF",
            "💡 Caixa de Sugestões"
        ]

        if is_master():
            nav_options.append("⚙️ Administração & Auditoria")

        selected_page = st.radio(
            "Navegação:",
            options=nav_options,
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.caption("🔒 **Isolamento de Dados:** Cada evento opera com sua própria pasta e arquivos JSON independentes.")
        st.caption("📦 **Dados Iniciais:** Base histórica importada de `Gastos com churrasco - 3º ELE 2025.xlsx`.")

    # Renderização da página selecionada
    if selected_page == "📊 Painel Geral (Dashboard)":
        render_dashboard(active_event_id)
    elif selected_page == "👥 Participantes & Colaboradores":
        render_participants(active_event_id)
    elif selected_page == "🥩 Consumíveis, Bebidas & Receitas":
        render_consumables(active_event_id)
    elif selected_page == "📌 Tarefas dos Colaboradores":
        render_tasks(active_event_id)
    elif selected_page == "💵 Caixa & Comprovantes Fiscais":
        render_cashflow(active_event_id)
    elif selected_page == "🏬 Fornecedores & Fotos":
        render_suppliers(active_event_id)
    elif selected_page == "📄 Relatórios & Emissão PDF":
        render_reports(active_event_id)
    elif selected_page == "💡 Caixa de Sugestões":
        render_suggestions(active_event_id)
    elif selected_page == "⚙️ Administração & Auditoria":
        render_admin(active_event_id)


if __name__ == "__main__":
    main()

