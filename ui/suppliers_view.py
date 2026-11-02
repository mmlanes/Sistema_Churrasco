import uuid
from datetime import datetime
from pathlib import Path
import pandas as pd
from PIL import Image
import streamlit as st
from services.event_service import get_event_data, save_event_data
from services.storage_service import get_event_uploads_dir
from ui.auth_view import can_edit


def render_suppliers(event_id: str):
    st.title("🏬 Fornecedores e Cotações com Fotos")
    st.caption("Cadastro de estabelecimentos (açougues, atacadistas, distribuidoras), associação com itens e fotos de encartes/etiquetas.")

    suppliers = get_event_data(event_id, "suppliers")
    consumables = get_event_data(event_id, "consumables")
    suppliers_dir = get_event_uploads_dir(event_id, "suppliers")

    tab1, tab2, tab3 = st.tabs(["📋 Lista de Fornecedores", "➕ Novo Fornecedor", "📸 Fotos de Preços & Cotações"])

    # ========================================================
    # ABA 1: LISTA DE FORNECEDORES E ITENS ASSOCIADOS
    # ========================================================
    with tab1:
        if not suppliers:
            st.info("Nenhum fornecedor cadastrado.")
        else:
            for s in suppliers:
                with st.expander(f"🏪 {s['name']} - ({s.get('category', 'Geral')})", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Contato:** {s.get('contact', '-')}")
                    c2.write(f"**Telefone / WhatsApp:** {s.get('phone', '-')}")
                    c3.write(f"**Endereço:** {s.get('address', '-')}")
                    
                    if s.get("notes"):
                        st.caption(f"📝 *Observações:* {s.get('notes')}")

                    # Itens cotados/associados a este fornecedor
                    items_sup = [c for c in consumables if c.get("supplier_id") == s["id"]]
                    if items_sup:
                        st.write("**Itens associados neste evento:**")
                        df_items = pd.DataFrame([
                            {
                                "Item": it["name"],
                                "Categoria": it.get("category", "-"),
                                "Preço Unitário": f"R$ {float(it.get('unit_price', 0)):.2f} / {it.get('unit')}",
                                "Embalagem Padrão": it.get("package_unit_name", "-")
                            }
                            for it in items_sup
                        ])
                        st.dataframe(df_items, use_container_width=True, hide_index=True)
                    else:
                        st.write("*(Nenhum item associado diretamente ainda)*")

                    # Fotos do fornecedor
                    sup_photos = s.get("photos", [])
                    if sup_photos:
                        st.write("**Fotos de Cotações / Preços:**")
                        pcols = st.columns(min(len(sup_photos), 4))
                        for idx, p_name in enumerate(sup_photos):
                            p_path = suppliers_dir / p_name
                            if p_path.exists():
                                with pcols[idx % 4]:
                                    img = Image.open(p_path)
                                    st.image(img, caption=p_name, use_container_width=True)

                    if can_edit():
                        col_ed1, col_ed2 = st.columns([1, 1])
                        with col_ed1:
                            # Anexar foto para este fornecedor
                            with st.popover(f"📷 Anexar Foto para {s['name']}"):
                                photo_file = st.file_uploader(f"Foto de etiqueta/preço ({s['name']})", type=["png", "jpg", "jpeg"], key=f"up_sup_{s['id']}")
                                if st.button("Salvar Foto", key=f"btn_p_{s['id']}"):
                                    if photo_file:
                                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                        ext = Path(photo_file.name).suffix
                                        fname = f"sup_{s['id']}_{int(datetime.now().timestamp())}{ext}"
                                        with open(suppliers_dir / fname, "wb") as f:
                                            f.write(photo_file.getbuffer())
                                        s.setdefault("photos", []).append(fname)
                                        save_event_data(event_id, "suppliers", suppliers, user_name, f"Anexou foto de cotação para fornecedor '{s['name']}'")
                                        st.success("Foto salva com sucesso!")
                                        st.rerun()

                        with col_ed2:
                            if st.button("🗑️ Excluir Fornecedor", key=f"del_sup_{s['id']}"):
                                user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                suppliers = [item for item in suppliers if item["id"] != s["id"]]
                                save_event_data(event_id, "suppliers", suppliers, user_name, f"Excluiu fornecedor '{s['name']}'")
                                st.warning("Fornecedor removido.")
                                st.rerun()

    # ========================================================
    # ABA 2: NOVO FORNECEDOR
    # ========================================================
    with tab2:
        if can_edit():
            st.subheader("Cadastrar Novo Fornecedor")
            with st.form("form_add_supplier", clear_on_submit=True):
                c1, c2 = st.columns(2)
                s_name = c1.text_input("Nome do Fornecedor / Estabelecimento *")
                s_cat = c2.selectbox("Categoria Principal", ["Carnes Nobres / Açougue", "Bebidas e Mercearia", "Hortifruti & Temperos", "Sobremesas / Gelo", "Descartáveis", "Outros"])

                c3, c4 = st.columns(2)
                s_contact = c3.text_input("Pessoa de Contato")
                s_phone = c4.text_input("Telefone / WhatsApp")

                s_address = st.text_input("Endereço Completo")
                s_notes = st.text_area("Condições de Pagamento / Vantagens / Horários de Entrega")

                sup_photo = st.file_uploader("Anexar Foto de Tabela de Preços / Fachada / Cartão de Visitas", type=["png", "jpg", "jpeg"])

                if st.form_submit_button("Cadastrar Fornecedor", type="primary"):
                    if s_name.strip():
                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                        sup_id = f"sup_{str(uuid.uuid4())[:8]}"
                        photos = []
                        if sup_photo is not None:
                            ext = Path(sup_photo.name).suffix
                            fname = f"sup_{sup_id}_{int(datetime.now().timestamp())}{ext}"
                            with open(suppliers_dir / fname, "wb") as f:
                                f.write(sup_photo.getbuffer())
                            photos.append(fname)

                        new_s = {
                            "id": sup_id,
                            "name": s_name.strip(),
                            "category": s_cat,
                            "contact": s_contact.strip(),
                            "phone": s_phone.strip(),
                            "address": s_address.strip(),
                            "notes": s_notes.strip(),
                            "photos": photos
                        }
                        suppliers.append(new_s)
                        save_event_data(event_id, "suppliers", suppliers, user_name, f"Cadastrou fornecedor '{s_name}'")
                        st.success(f"Fornecedor '{s_name}' adicionado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Informe o nome do fornecedor.")
        else:
            st.warning("Apenas usuários autenticados podem cadastrar novos fornecedores.")

    # ========================================================
    # ABA 3: FOTOS E COTAÇÕES
    # ========================================================
    with tab3:
        st.subheader("📸 Galeria de Fotos de Preços e Cotações")
        all_photos = []
        for s in suppliers:
            for p in s.get("photos", []):
                all_photos.append((s["name"], p))

        if not all_photos:
            st.info("Nenhuma foto de cotação ou tabela de preços anexada ainda.")
        else:
            pcols = st.columns(3)
            for idx, (s_name, p_name) in enumerate(all_photos):
                p_path = suppliers_dir / p_name
                if p_path.exists():
                    with pcols[idx % 3]:
                        st.markdown(f"**Fornecedor:** `{s_name}`")
                        img = Image.open(p_path)
                        st.image(img, use_container_width=True)
                        with open(p_path, "rb") as f:
                            st.download_button("⬇️ Baixar Imagem", f.read(), file_name=p_name, key=f"dl_sup_p_{idx}")
                        st.markdown("---")

