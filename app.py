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

