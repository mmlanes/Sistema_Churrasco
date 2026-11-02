import uuid
from datetime import datetime
import pandas as pd
import streamlit as st
from services.event_service import get_event_data, save_event_data
from ui.auth_view import can_edit, is_master


def render_suggestions(event_id: str):
    st.title("💡 Caixa de Sugestões e Ideias da Turma")
    st.caption("Espaço aberto para todos os convidados, alunos e colaboradores enviarem ideias, pedidos e sugestões de melhoria.")

    suggestions = get_event_data(event_id, "suggestions")
    current_user = st.session_state.get("user", {})

    tab1, tab2 = st.tabs(["💬 Mural de Sugestões", "✍️ Enviar Nova Sugestão"])

    with tab1:
        if not suggestions:
            st.info("Nenhuma sugestão enviada ainda. Seja o primeiro a contribuir!")
        else:
            for s in reversed(suggestions):
                status = s.get("status", "Pendente")
                if status == "Aceita":
                    border_color = "#10B981"
                    badge = "✅ ACEITA PELA ORGANIZAÇÃO"
                elif status == "Analisada":
                    border_color = "#3B82F6"
                    badge = "⏳ EM ANÁLISE"
                elif status == "Rejeitada":
                    border_color = "#EF4444"
                    badge = "❌ NÃO APLICÁVEL"
                else:
                    border_color = "#F59E0B"
                    badge = "📬 PENDENTE"

                with st.container():
                    st.markdown(
                        f"""
                        <div style="border-left: 5px solid {border_color}; background: rgba(127, 127, 127, 0.12); color: inherit; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; border-top: 1px solid rgba(127,127,127,0.15); border-right: 1px solid rgba(127,127,127,0.15); border-bottom: 1px solid rgba(127,127,127,0.15);">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:bold; color:inherit;">👤 {s.get('author', 'Anônimo')} <span style="font-size:0.8rem; opacity:0.75;">({s.get('created_at', '')})</span></span>
                                <span style="font-size:0.8rem; font-weight:bold; color:{border_color};">{badge}</span>
                            </div>
                            <p style="margin: 8px 0; color:inherit; font-size: 0.95rem;">{s.get('text')}</p>
                            {f"<div style='background: rgba(59, 130, 246, 0.15); border-left:3px solid #3B82F6; padding:6px 10px; margin-top:6px; border-radius:4px; font-size:0.85rem; color:inherit;'><b>Resposta da Organização:</b> {s.get('admin_response')}</div>" if s.get('admin_response') else ""}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Se for Master ou Colaborador, pode responder ou mudar o status da sugestão
                    if can_edit():
                        with st.popover(f"⚙️ Moderar Sugestão de {s.get('author')}"):
                            new_st = st.selectbox(
                                "Status:",
                                ["Pendente", "Analisada", "Aceita", "Rejeitada"],
                                index=["Pendente", "Analisada", "Aceita", "Rejeitada"].index(status) if status in ["Pendente", "Analisada", "Aceita", "Rejeitada"] else 0,
                                key=f"sug_st_{s['id']}"
                            )
                            new_resp = st.text_input("Resposta da Organização:", value=s.get("admin_response", ""), key=f"sug_resp_{s['id']}")
                            if st.button("Salvar Moderação", key=f"btn_mod_{s['id']}"):
                                orig_s = next(item for item in suggestions if item["id"] == s["id"])
                                orig_s["status"] = new_st
                                orig_s["admin_response"] = new_resp.strip()
                                save_event_data(event_id, "suggestions", suggestions, current_user.get("name", "Organizador"), f"Moderou sugestão ID '{s['id']}' para '{new_st}'")
                                st.success("Sugestão atualizada!")
                                st.rerun()

    with tab2:
        st.subheader("Envie sua Ideia para o Churrasco")
        with st.form("form_send_suggestion", clear_on_submit=True):
            author_name = st.text_input("Seu Nome", value=current_user.get("name", "") if current_user.get("username") != "convidado" else "")
            sug_text = st.text_area("Descreva sua sugestão ou pedido (ex: incluir bebidas zero, música, sugestão de corte de carne, etc.) *")
            
            if st.form_submit_button("Enviar Sugestão", type="primary"):
                if sug_text.strip():
                    new_s = {
                        "id": f"sug_{str(uuid.uuid4())[:8]}",
                        "author": author_name.strip() or "Convidado Anônimo",
                        "user_role": current_user.get("role", "visualizador"),
                        "text": sug_text.strip(),
                        "status": "Pendente",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "admin_response": ""
                    }
                    suggestions.append(new_s)
                    save_event_data(event_id, "suggestions", suggestions, author_name or "Convidado", "Enviou uma nova sugestão no mural")
                    st.success("Sua sugestão foi enviada com sucesso e já está visível para a turma!")
                    st.rerun()
                else:
                    st.error("Por favor, digite o texto da sua sugestão.")

