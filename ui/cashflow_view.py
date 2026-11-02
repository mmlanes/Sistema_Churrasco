import os
import uuid
from datetime import datetime
from pathlib import Path
import pandas as pd
from PIL import Image
import io
import streamlit as st
from services.event_service import get_event_data, save_event_data
from services.storage_service import get_event_uploads_dir
from services.supabase_service import save_upload_to_db, get_upload_from_db
from ui.auth_view import can_edit


def render_cashflow(event_id: str):
    st.title("💵 Controle de Caixa e Comprovantes Fiscais")
    st.caption("Registro de entradas (cotas de alunos e servidores), saídas, reembolsos via PIX e upload de cupons fiscais e notas.")

    cashflow = get_event_data(event_id, "cashflow")
    receipts_dir = get_event_uploads_dir(event_id, "receipts")

    entradas = [c for c in cashflow if c.get("type") == "ENTRADA"]
    saidas = [c for c in cashflow if c.get("type") == "SAIDA"]

    total_in = sum(float(c.get("amount", 0)) for c in entradas)
    total_out = sum(float(c.get("amount", 0)) for c in saidas)
    saldo = total_in - total_out

    # Resumo em métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Entradas (Caixa)", f"R$ {total_in:,.2f}")
    m2.metric("Total Gastos Efetuados", f"R$ {total_out:,.2f}")
    delta_color = "normal" if saldo >= 0 else "inverse"
    m3.metric("Saldo Atual / Sobra em Caixa", f"R$ {saldo:,.2f}", delta_color=delta_color)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📝 Lançamentos do Caixa", "➕ Novo Lançamento / Comprovante", "📷 Galeria de Notas e Cupons"])

    # ========================================================
    # ABA 1: TABELA DE LANÇAMENTOS
    # ========================================================
    with tab1:
        st.subheader("Extrato de Movimentações")
        if cashflow:
            df_cash = pd.DataFrame([
                {
                    "ID": c["id"],
                    "Tipo": "🟢 ENTRADA" if c.get("type") == "ENTRADA" else "🔴 SAÍDA",
                    "Data": c.get("date", "-"),
                    "Descrição": c.get("description", ""),
                    "Origem / Destino": c.get("payer_or_receiver", "-"),
                    "Forma": c.get("payment_method", "-"),
                    "Valor (R$)": f"R$ {float(c.get('amount', 0)):.2f}",
                    "Comprovante": "📎 Anexado" if c.get("attachment_name") else "Sem anexo",
                    "Observações": c.get("notes", "")
                }
                for c in cashflow
            ])
            st.dataframe(df_cash, use_container_width=True, hide_index=True)

            if can_edit():
                with st.expander("🗑️ Excluir Lançamento"):
                    sel_del_csh = st.selectbox(
                        "Selecione o lançamento a remover:",
                        options=[c["id"] for c in cashflow],
                        format_func=lambda x: next((f"[{c.get('type')}] {c.get('description')} - R$ {c.get('amount')}" for c in cashflow if c["id"] == x), x)
                    )
                    if st.button("Confirmar Exclusão de Lançamento", type="secondary"):
                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                        cashflow = [c for c in cashflow if c["id"] != sel_del_csh]
                        save_event_data(event_id, "cashflow", cashflow, user_name, f"Excluiu lançamento de caixa ID '{sel_del_csh}'")
                        st.warning("Lançamento removido.")
                        st.rerun()
        else:
            st.info("Nenhuma movimentação de caixa registrada.")

    # ========================================================
    # ABA 2: NOVO LANÇAMENTO & UPLOAD DE COMPROVANTE
    # ========================================================
    with tab2:
        if can_edit():
            st.subheader("Registrar Movimentação Financeira")
            st.caption("Envie comprovantes de PIX, cupom fiscal de compras de supermercado ou açougue tirados pelo celular.")

            with st.form("form_add_cashflow", clear_on_submit=True):
                c1, c2, c3 = st.columns([1.2, 2, 1.2])
                cf_type = c1.selectbox("Tipo de Movimentação", ["SAIDA", "ENTRADA"], format_func=lambda x: "🔴 Saída / Gasto / Reembolso" if x == "SAIDA" else "🟢 Entrada / Arrecadação")
                cf_desc = c2.text_input("Descrição (ex: Compra de Carne no Açougue, PIX Reembolso Marcelle, Cota Alunos) *")
                cf_amount = c3.number_input("Valor (R$)", value=50.0, step=10.0, format="%.2f")

                c4, c5, c6 = st.columns(3)
                cf_date = c4.date_input("Data do Pagamento")
                cf_person = c5.text_input("Origem / Destino (Pessoa ou Estabelecimento)")
                cf_method = c6.selectbox("Forma de Pagamento", ["PIX", "Cartão de Débito", "Cartão de Crédito", "Dinheiro", "Transferência", "Outro"])

                uploaded_file = st.file_uploader("📎 Anexar Cupom Fiscal / Nota Fiscal / Comprovante PIX (Foto de celular JPG, PNG ou PDF)", type=["png", "jpg", "jpeg", "pdf"])
                cf_notes = st.text_input("Observações Adicionais")

                if st.form_submit_button("Salvar no Caixa", type="primary"):
                    if cf_desc.strip():
                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                        filename = ""
                        if uploaded_file is not None:
                            ext = Path(uploaded_file.name).suffix
                            filename = f"rec_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}{ext}"
                            file_bytes = uploaded_file.getvalue()
                            save_path = receipts_dir / filename
                            try:
                                with open(save_path, "wb") as f:
                                    f.write(file_bytes)
                            except Exception:
                                pass
                            # Salva permanentemente no Supabase
                            try:
                                save_upload_to_db(event_id, "receipts", filename, file_bytes, uploaded_file.type)
                            except Exception as e:
                                print(f"Erro ao salvar upload no Supabase: {e}")

                        new_entry = {
                            "id": f"csh_{str(uuid.uuid4())[:8]}",
                            "type": cf_type,
                            "category": "Geral",
                            "description": cf_desc.strip(),
                            "amount": float(cf_amount),
                            "payer_or_receiver": cf_person.strip(),
                            "date": str(cf_date),
                            "payment_method": cf_method,
                            "attachment_name": filename,
                            "notes": cf_notes.strip()
                        }
                        cashflow.append(new_entry)
                        save_event_data(event_id, "cashflow", cashflow, user_name, f"Registrou {cf_type} de R$ {cf_amount:.2f}: '{cf_desc}'")
                        st.success("Lançamento e comprovante registrados com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe a descrição do lançamento.")
        else:
            st.warning("Você está em modo de leitura. Faça login para registrar lançamentos ou anexar comprovantes.")

    # ========================================================
    # ABA 3: GALERIA DE COMPROVANTES
    # ========================================================
    with tab3:
        st.subheader("📷 Galeria de Comprovantes e Notas Fiscais")
        receipts_files = [c for c in cashflow if c.get("attachment_name")]
        
        if not receipts_files:
            st.info("Nenhum comprovante fiscal com anexo foi registrado até o momento.")
        else:
            cols = st.columns(3)
            for idx, c in enumerate(receipts_files):
                fname = c.get("attachment_name")
                file_path = receipts_dir / fname
                col_target = cols[idx % 3]

                with col_target:
                    with st.container():
                        st.markdown(f"**{c.get('description')}**")
                        st.caption(f"Valor: R$ {c.get('amount', 0):.2f} | Data: {c.get('date')}")
                        # Tenta carregar do disco local; se não existir, recupera do Supabase
                        file_bytes = None
                        if file_path.exists():
                            try:
                                with open(file_path, "rb") as f:
                                    file_bytes = f.read()
                            except Exception:
                                pass
                        if file_bytes is None:
                            file_bytes = get_upload_from_db(event_id, "receipts", fname)
                            if file_bytes:
                                try:
                                    with open(file_path, "wb") as f:
                                        f.write(file_bytes)
                                except Exception:
                                    pass

                        if file_bytes:
                            if Path(fname).suffix.lower() in [".png", ".jpg", ".jpeg"]:
                                try:
                                    img = Image.open(io.BytesIO(file_bytes))
                                    st.image(img, use_container_width=True)
                                except Exception:
                                    st.write("Erro ao processar imagem.")
                            else:
                                st.write(f"📄 Arquivo: `{fname}`")

                            st.download_button(
                                label="⬇️ Baixar Arquivo",
                                data=file_bytes,
                                file_name=fname,
                                key=f"dl_{idx}_{fname}"
                            )
                        else:
                            st.write("*(Arquivo físico não localizado)*")
                        st.markdown("---")

