import uuid
import pandas as pd
import streamlit as st
from services.calculation_service import calculate_consumables_totals, calculate_recipes_totals
from services.event_service import get_event_data, save_event_data
from ui.auth_view import can_edit


def render_consumables(event_id: str):
    st.title("🥩 Consumíveis, Bebidas e Receitas Fabricadas")
    st.caption("Cálculo automático de porções por pessoa, arredondamento para embalagens comerciais e receitas personalizadas.")

    participants = get_event_data(event_id, "participants")
    confirmed_count = len([p for p in participants if p.get("confirmed", True)])
    if confirmed_count == 0:
        confirmed_count = len(participants) or 35

    col_info1, col_info2 = st.columns([2, 1])
    with col_info1:
        st.info(f"💡 Base de cálculo atual: **{confirmed_count} participantes confirmados**. Todas as quantidades ajustadas e custos são recalculados automaticamente.")
    with col_info2:
        calc_override = st.number_input("Simular outro número de pessoas:", min_value=1, max_value=1000, value=confirmed_count, step=1)
        if calc_override != confirmed_count:
            confirmed_count = calc_override

    tab1, tab2, tab3 = st.tabs([
        "🥤 Bebidas, Carnes e Itens Diretos",
        "🥗 Receitas Fabricadas (Farofa, Vinagrete, etc.)",
        "🛒 Lista de Compras Consolidada"
    ])

    suppliers = get_event_data(event_id, "suppliers")
    suppliers_dict = {s["id"]: s["name"] for s in suppliers}
    collaborators = get_event_data(event_id, "collaborators")
    collab_names = [c["name"] for c in collaborators]

    # ========================================================
    # ABA 1: CONSUMÍVEIS DIRETOS (BEBIDAS, CARNES, DESCARTÁVEIS)
    # ========================================================
    with tab1:
        consumables = get_event_data(event_id, "consumables")
        calc_items, summary = calculate_consumables_totals(consumables, confirmed_count)

        # Métricas no topo com destaque para Carnes e Bebidas por Pessoa
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        meat_g = summary.get("meat_grams_per_person", 0.0)
        meat_kg_p = summary.get("meat_kg_per_person", 0.0)
        meat_tot = summary.get("total_meat_kg", 0.0)
        meat_adj = summary.get("total_meat_kg_adjusted", 0.0)
        meat_count = summary.get("meat_items_count", 0)

        drink_l = summary.get("drinks_liters_per_person", 0.0)
        drink_ml = summary.get("drinks_ml_per_person", 0.0)
        drink_tot = summary.get("total_drinks_liters", 0.0)
        drink_adj = summary.get("total_drinks_liters_adjusted", 0.0)
        drink_count = summary.get("drink_items_count", 0)

        col_m1.metric(
            label="🥩 Carnes por Pessoa",
            value=f"{meat_g:.0f} g" if meat_g < 1000 else f"{meat_kg_p:.2f} kg",
            delta=f"Total: {meat_tot:.1f} kg ({meat_count} tipos)",
            delta_color="normal"
        )

        col_m2.metric(
            label="🥤 Bebidas por Pessoa",
            value=f"{drink_l:.2f} L" if drink_l >= 1 else f"{drink_ml:.0f} ml",
            delta=f"Total: {drink_tot:.1f} L ({drink_count} bebidas)",
            delta_color="normal"
        )

        col_m3.metric(
            label="💰 Custo Médio / Pessoa",
            value=f"R$ {summary['cost_per_person']:,.2f}",
            delta=f"Base: {confirmed_count} confirmados",
            delta_color="off"
        )

        col_m4.metric(
            label="💵 Subtotal Consumíveis",
            value=f"R$ {summary['grand_total']:,.2f}",
            delta=f"{len(consumables)} itens totais",
            delta_color="off"
        )

        # Painel Informativo de Consumo Per Capita
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%); border: 1px solid #BFDBFE; border-radius: 10px; padding: 14px 18px; margin: 12px 0 16px 0;">
                <div style="font-size: 1rem; font-weight: 700; color: #1E3A8A; margin-bottom: 8px;">
                    🎯 Médias de Consumo do Churrasco (Planejado para {confirmed_count} participantes):
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; font-size: 0.92rem; color: #1E293B;">
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px;">
                        <span style="font-size: 1.1rem;">🥩</span> <b>Carnes:</b> <b style="color: #DC2626; font-size: 1.05rem;">{meat_g:.0f} g / pessoa</b> (ou <b>{meat_kg_p:.3f} kg</b>)
                        <div style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">
                            &bull; Necessário líquido: <b>{meat_tot:.2f} kg</b><br>
                            &bull; Com embalagens comerciais: <b>{meat_adj:.2f} kg</b> ({summary.get('meat_adjusted_grams_per_person', 0.0):.0f} g / pessoa)
                        </div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px;">
                        <span style="font-size: 1.1rem;">🥤</span> <b>Bebidas:</b> <b style="color: #2563EB; font-size: 1.05rem;">{drink_l:.2f} L / pessoa</b> (ou <b>{drink_ml:.0f} ml</b>)
                        <div style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">
                            &bull; Necessário líquido: <b>{drink_tot:.2f} Litros</b><br>
                            &bull; Com embalagens comerciais: <b>{drink_adj:.2f} Litros</b> ({summary.get('drinks_adjusted_liters_per_person', 0.0):.2f} L / pessoa)
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Detalhamento expansível da composição das carnes e bebidas
        meat_breakdown = summary.get("meat_breakdown", [])
        drinks_breakdown = summary.get("drinks_breakdown", [])

        if meat_breakdown or drinks_breakdown:
            with st.expander("🔍 Ver Composição Detalhada (Carnes e Bebidas por Participante)"):
                col_det1, col_det2 = st.columns(2)
                
                with col_det1:
                    st.markdown("##### 🥩 Composição de Carnes")
                    if meat_breakdown:
                        df_meat = pd.DataFrame([
                            {
                                "Corte / Carne": m["name"],
                                "Qtd / Pessoa": f"{m['per_person_g']:.0f} g ({m['per_person_kg']:.3f} kg)",
                                "% do Total": f"{(m['total_needed_kg'] / (meat_tot or 1)) * 100:.1f}%",
                                "Total Evento": f"{m['total_needed_kg']:.2f} kg"
                            }
                            for m in meat_breakdown
                        ])
                        st.dataframe(df_meat, use_container_width=True, hide_index=True)
                    else:
                        st.caption("Nenhuma carne cadastrada ainda.")

                with col_det2:
                    st.markdown("##### 🥤 Composição de Bebidas")
                    if drinks_breakdown:
                        df_drinks = pd.DataFrame([
                            {
                                "Bebida": d["name"],
                                "Qtd / Pessoa": f"{d['per_person_l']:.2f} L ({d['per_person_ml']:.0f} ml)",
                                "% do Total": f"{(d['total_needed_l'] / (drink_tot or 1)) * 100:.1f}%",
                                "Total Evento": f"{d['total_needed_l']:.2f} L"
                            }
                            for d in drinks_breakdown
                        ])
                        st.dataframe(df_drinks, use_container_width=True, hide_index=True)
                    else:
                        st.caption("Nenhuma bebida cadastrada ainda.")

        st.markdown("---")

        # Formulário para Adicionar Consumível
        if can_edit():
            with st.expander("➕ Adicionar Novo Consumível", expanded=(len(consumables) == 0)):
                with st.form("form_add_consumable", clear_on_submit=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c_name = c1.text_input("Nome do Item (ex: Coca-cola 2L, Alcatra, Cerveja Lata, Pão de Alho)")
                    c_cat = c2.selectbox("Categoria", ["Bebidas", "Carnes", "Gelo / Carvão", "Acompanhamentos", "Descartáveis", "Sobremesas", "Outros"])
                    c_unit = c3.selectbox("Unidade Base", ["L", "kg", "un", "pct", "rolo"])

                    c4, c5, c6 = st.columns(3)
                    c_per_person = c4.number_input("Qtd por Pessoa (0 se for fixo)", value=0.1, step=0.05, format="%.3f")
                    c_fixed = c5.number_input("Qtd Fixa (se não for por pessoa)", value=0.0, step=1.0)
                    c_pack = c6.number_input("Tamanho da Embalagem Comercial (ex: 2.0 p/ garrafa 2L, 40 p/ pacote 40un)", value=2.0, step=0.5)

                    c7, c8, c9 = st.columns(3)
                    c_pack_name = c7.text_input("Nome da Embalagem (ex: Garrafa de 2L, Fardo com 12 latas)")
                    c_price = c8.number_input("Preço Unitário (R$)", value=5.0, step=0.50, format="%.2f")
                    c_supplier = c9.selectbox(
                        "Fornecedor",
                        options=[""] + list(suppliers_dict.keys()),
                        format_func=lambda x: suppliers_dict.get(x, "Nenhum selecionado")
                    )

                    c10, c11 = st.columns([1, 2])
                    c_collab = c10.selectbox("Responsável pela Compra", [""] + collab_names)
                    c_notes = c11.text_input("Observações")

                    if st.form_submit_button("Cadastrar Item", type="primary"):
                        if c_name.strip():
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            new_item = {
                                "id": f"c_{str(uuid.uuid4())[:8]}",
                                "name": c_name.strip(),
                                "category": c_cat,
                                "unit": c_unit,
                                "per_person": float(c_per_person),
                                "fixed_quantity": float(c_fixed),
                                "package_size": float(c_pack),
                                "package_unit_name": c_pack_name.strip() or f"Embalagem {c_pack} {c_unit}",
                                "unit_price": float(c_price),
                                "price_is_per_package": False,
                                "supplier_id": c_supplier,
                                "assigned_collaborator": c_collab,
                                "notes": c_notes
                            }
                            consumables.append(new_item)
                            save_event_data(event_id, "consumables", consumables, user_name, f"Adicionou consumível '{c_name}'")
                            st.success(f"Item '{c_name}' cadastrado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Informe o nome do item.")

        # Tabela com Arredondamento e Custos
        if calc_items:
            table_data = []
            for item in calc_items:
                pack_desc = item.get("package_unit_name") or f"{item.get('package_size')} {item.get('unit')}"
                sup_name = suppliers_dict.get(item.get("supplier_id"), "-")
                table_data.append({
                    "ID": item["id"],
                    "Item": item["name"],
                    "Categoria": item.get("category", "-"),
                    "Qtd / Pessoa": f"{item.get('per_person', 0)} {item.get('unit')}" if item.get('per_person', 0) > 0 else f"{item.get('fixed_quantity')} (Fixo)",
                    "Qtd Necessária": f"{item.get('base_needed'):.2f} {item.get('unit')}",
                    "Embalagem / Arredondamento": f"{item.get('packages_needed')}x ({pack_desc})" if item.get('package_size', 0) > 0 else "-",
                    "Total a Comprar": f"{item.get('adjusted_quantity'):.2f} {item.get('unit')}",
                    "Preço Unit.": f"R$ {float(item.get('unit_price', 0)):.2f}",
                    "Custo Total": f"R$ {float(item.get('total_cost', 0)):.2f}",
                    "Responsável": item.get("assigned_collaborator", "-"),
                    "Fornecedor": sup_name
                })

            df_items = pd.DataFrame(table_data)
            st.dataframe(df_items, use_container_width=True, hide_index=True)

            # Edição e Exclusão rápida
            if can_edit():
                with st.expander("✏️ Editar ou Ajustar Preço / Quantidade de um Item"):
                    sel_item_id = st.selectbox(
                        "Selecione o item para editar:",
                        options=[c["id"] for c in consumables],
                        format_func=lambda x: next((f"{c['name']} ({c.get('category')}) - R$ {c.get('unit_price')}" for c in consumables if c["id"] == x), x)
                    )
                    curr_item = next(c for c in consumables if c["id"] == sel_item_id)

                    with st.form("form_edit_consumable"):
                        e1, e2, e3 = st.columns([2, 1, 1])
                        new_name = e1.text_input("Nome", value=curr_item["name"])
                        new_cat = e2.selectbox("Categoria", ["Bebidas", "Carnes", "Gelo / Carvão", "Acompanhamentos", "Descartáveis", "Sobremesas", "Outros"], index=["Bebidas", "Carnes", "Gelo / Carvão", "Acompanhamentos", "Descartáveis", "Sobremesas", "Outros"].index(curr_item.get("category", "Bebidas")) if curr_item.get("category") in ["Bebidas", "Carnes", "Gelo / Carvão", "Acompanhamentos", "Descartáveis", "Sobremesas", "Outros"] else 0)
                        new_unit = e3.selectbox("Unidade", ["L", "kg", "un", "pct", "rolo"], index=["L", "kg", "un", "pct", "rolo"].index(curr_item.get("unit", "L")) if curr_item.get("unit") in ["L", "kg", "un", "pct", "rolo"] else 0)

                        e4, e5, e6 = st.columns(3)
                        new_per_p = e4.number_input("Qtd por Pessoa", value=float(curr_item.get("per_person", 0)), step=0.05, format="%.3f")
                        new_fixed = e5.number_input("Qtd Fixa", value=float(curr_item.get("fixed_quantity", 0)), step=1.0)
                        new_pack = e6.number_input("Embalagem Comercial", value=float(curr_item.get("package_size", 1.0)), step=0.5)

                        e7, e8, e9 = st.columns(3)
                        new_pack_name = e7.text_input("Nome da Embalagem", value=curr_item.get("package_unit_name", ""))
                        new_price = e8.number_input("Preço Unitário (R$)", value=float(curr_item.get("unit_price", 0)), step=0.50, format="%.2f")
                        curr_sup = curr_item.get("supplier_id") or ""
                        sup_opts = [""] + list(suppliers_dict.keys())
                        sup_idx = sup_opts.index(curr_sup) if curr_sup in sup_opts else 0
                        new_sup = e9.selectbox("Fornecedor", options=sup_opts, format_func=lambda x: suppliers_dict.get(x, "Nenhum"), index=sup_idx)

                        e10, e11 = st.columns([1, 2])
                        collab_opts = [""] + collab_names
                        collab_idx = collab_opts.index(curr_item.get("assigned_collaborator", "")) if curr_item.get("assigned_collaborator") in collab_opts else 0
                        new_collab = e10.selectbox("Responsável", options=collab_opts, index=collab_idx)
                        new_notes = e11.text_input("Observações", value=curr_item.get("notes", ""))

                        b1, b2 = st.columns(2)
                        with b1:
                            salvar_btn = st.form_submit_button("Salvar Alterações", type="primary", use_container_width=True)
                        with b2:
                            excluir_btn = st.form_submit_button("🗑️ Excluir Item", use_container_width=True)

                        if salvar_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            curr_item["name"] = new_name.strip()
                            curr_item["category"] = new_cat
                            curr_item["unit"] = new_unit
                            curr_item["per_person"] = float(new_per_p)
                            curr_item["fixed_quantity"] = float(new_fixed)
                            curr_item["package_size"] = float(new_pack)
                            curr_item["package_unit_name"] = new_pack_name.strip()
                            curr_item["unit_price"] = float(new_price)
                            curr_item["supplier_id"] = new_sup
                            curr_item["assigned_collaborator"] = new_collab
                            curr_item["notes"] = new_notes

                            save_event_data(event_id, "consumables", consumables, user_name, f"Atualizou consumível '{new_name}' (Preço: R$ {new_price}, Qtd/p: {new_per_p})")
                            st.success(f"Item '{new_name}' atualizado com sucesso!")
                            st.rerun()

                        if excluir_btn:
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            consumables = [c for c in consumables if c["id"] != sel_item_id]
                            save_event_data(event_id, "consumables", consumables, user_name, f"Excluiu consumível '{curr_item['name']}'")
                            st.warning(f"Item '{curr_item['name']}' removido.")
                            st.rerun()

    # ========================================================
    # ABA 2: RECEITAS FABRICADAS POR COLABORADORES
    # ========================================================
    with tab2:
        recipes = get_event_data(event_id, "recipes")
        calc_recipes, rec_summary = calculate_recipes_totals(recipes, confirmed_count)

        st.subheader("🥗 Consumíveis Fabricados por Colaboradores")
        st.caption("Receitas que utilizam múltiplos ingredientes (ex: Farofa com bacon/calabresa, Vinagrete temperado, Tortas doces). O sistema calcula a quantidade total de cada ingrediente e o custo por fornecedor.")

        st.metric("Custo Total Estimado das Receitas", f"R$ {rec_summary['recipes_grand_total']:,.2f}")

        # Mensagem explicativa caso o usuário esteja em modo somente leitura
        if not can_edit():
            st.info("ℹ️ **Modo Visualização (Somente Leitura):** Você está acessando em modo de leitura. Para criar, editar ou excluir receitas e ingredientes, faça login na barra superior (botão **🔑 Fazer Login**) como **Organizador Master** ou **Colaborador**.")

        # Adicionar Nova Receita
        if can_edit():
            with st.expander("➕ Criar Nova Receita Fabricada"):
                with st.form("form_add_recipe", clear_on_submit=True):
                    r1, r2 = st.columns(2)
                    rec_name = r1.text_input("Nome da Receita (ex: Arroz Carreteiro, Vinagrete Especial)")
                    rec_collab = r2.selectbox("Colaborador Responsável pelo Preparo", [""] + collab_names)

                    r3, r4, r5 = st.columns(3)
                    rec_yield = r3.number_input("Rendimento Padrão", value=3.0, step=0.5)
                    rec_unit = r4.selectbox("Unidade do Rendimento", ["kg", "L", "porções", "un"])
                    rec_portion_p = r5.number_input("Porção estimada por pessoa", value=0.085, step=0.01, format="%.3f")

                    rec_inst = st.text_area("Instruções / Modo de Preparo")

                    if st.form_submit_button("Criar Receita Base", type="primary"):
                        if rec_name.strip():
                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                            new_r = {
                                "id": f"rec_{str(uuid.uuid4())[:8]}",
                                "name": rec_name.strip(),
                                "category": "Acompanhamentos",
                                "assigned_to": rec_collab or "Colaborador",
                                "standard_yield": float(rec_yield),
                                "yield_unit": rec_unit,
                                "portion_per_person": float(rec_portion_p),
                                "batch_multiplier": 1.0,
                                "instructions": rec_inst,
                                "ingredients": []
                            }
                            recipes.append(new_r)
                            save_event_data(event_id, "recipes", recipes, user_name, f"Criou receita '{rec_name}'")
                            st.success(f"Receita '{rec_name}' criada! Agora adicione os ingredientes abaixo.")
                            st.rerun()

        # Listagem e Gestão de cada receita existente
        for r_idx, r in enumerate(calc_recipes):
            with st.container():
                col_r_title, col_r_actions = st.columns([3, 1.8])
                with col_r_title:
                    st.markdown(f"### 🍲 {r.get('name')}")
                    st.write(f"**Chef / Responsável:** `{r.get('assigned_to', 'Não atribuído')}` | **Rendimento Calculado:** `{r.get('total_yield_needed')} {r.get('yield_unit', 'kg')}` | **Custo Total da Receita:** `R$ {r.get('total_cost'):,.2f}`")
                    if r.get("instructions"):
                        st.caption(f"📝 *Modo de preparo:* {r.get('instructions')}")

                if can_edit():
                    with col_r_actions:
                        st.write("")
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            with st.popover("✏️ Editar Receita"):
                                st.subheader(f"Editar '{r.get('name')}'")
                                with st.form(f"form_edit_recipe_{r['id']}"):
                                    e_rec_name = st.text_input("Nome da Receita", value=r.get("name", ""))
                                    collab_opts = [""] + collab_names
                                    c_idx = collab_opts.index(r.get("assigned_to", "")) if r.get("assigned_to") in collab_opts else 0
                                    e_rec_collab = st.selectbox("Colaborador Responsável", collab_opts, index=c_idx)
                                    
                                    er1, er2 = st.columns(2)
                                    e_rec_yield = er1.number_input("Rendimento Padrão", value=float(r.get("standard_yield", 3.0)), step=0.5)
                                    unit_opts = ["kg", "L", "porções", "un"]
                                    u_idx = unit_opts.index(r.get("yield_unit", "kg")) if r.get("yield_unit") in unit_opts else 0
                                    e_rec_unit = er2.selectbox("Unidade do Rendimento", unit_opts, index=u_idx)
                                    
                                    e_rec_portion = st.number_input("Porção estimada por pessoa", value=float(r.get("portion_per_person", 0.085)), step=0.01, format="%.3f")
                                    e_rec_inst = st.text_area("Instruções / Modo de Preparo", value=r.get("instructions", ""))
                                    
                                    if st.form_submit_button("💾 Salvar Receita", type="primary", use_container_width=True):
                                        if e_rec_name.strip():
                                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                            orig_r = next((item for item in recipes if item["id"] == r["id"]), None)
                                            if orig_r:
                                                orig_r["name"] = e_rec_name.strip()
                                                orig_r["assigned_to"] = e_rec_collab or "Colaborador"
                                                orig_r["standard_yield"] = float(e_rec_yield)
                                                orig_r["yield_unit"] = e_rec_unit
                                                orig_r["portion_per_person"] = float(e_rec_portion)
                                                orig_r["instructions"] = e_rec_inst
                                                save_event_data(event_id, "recipes", recipes, user_name, f"Editou receita '{e_rec_name.strip()}'")
                                                st.success(f"Receita '{e_rec_name.strip()}' atualizada!")
                                                st.rerun()
                                        else:
                                            st.error("O nome da receita não pode ficar vazio.")

                        with b_col2:
                            with st.popover("🗑️ Excluir"):
                                st.subheader("Excluir Receita")
                                st.warning(f"Excluir '{r.get('name')}' e todos os ingredientes?")
                                if st.button("Confirmar Exclusão", key=f"btn_confirm_del_rec_{r['id']}", type="primary", use_container_width=True):
                                    user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                    recipes = [item for item in recipes if item["id"] != r["id"]]
                                    save_event_data(event_id, "recipes", recipes, user_name, f"Excluiu receita '{r.get('name')}'")
                                    st.warning(f"Receita '{r.get('name')}' excluída.")
                                    st.rerun()

                ings = r.get("ingredients", [])
                if ings:
                    df_ing = pd.DataFrame([
                        {
                            "Ingrediente": ing.get("name"),
                            "Qtd Base": f"{ing.get('quantity')} {ing.get('unit')}",
                            "Qtd Calculada p/ Evento": f"{ing.get('adjusted_qty')} {ing.get('unit')}",
                            "Preço Unitário": f"R$ {float(ing.get('unit_price', 0)):.2f}",
                            "Custo Ingrediente": f"R$ {float(ing.get('cost', 0)):.2f}",
                            "Fornecedor": suppliers_dict.get(ing.get("supplier_id"), "-")
                        }
                        for ing in ings
                    ])
                    st.dataframe(df_ing, use_container_width=True, hide_index=True)
                else:
                    st.warning("Esta receita ainda não possui ingredientes cadastrados.")

                # Ações de ingredientes (Adicionar ou Editar/Remover)
                if can_edit():
                    col_ing_add, col_ing_edit = st.columns(2)
                    with col_ing_add:
                        with st.expander(f"➕ Adicionar Ingrediente em '{r.get('name')}'"):
                            with st.form(f"form_add_ing_{r['id']}", clear_on_submit=True):
                                i1, i2, i3 = st.columns([2, 1, 1])
                                ing_name = i1.text_input("Nome do Ingrediente (ex: Bacon, Tomate, Ovos)")
                                ing_qty = i2.number_input("Qtd para o rendimento padrão", value=1.0, step=0.1)
                                ing_unit = i3.selectbox("Unidade", ["kg", "g", "L", "ml", "un", "maço", "pct"])

                                i4, i5, i6 = st.columns(3)
                                ing_price = i4.number_input("Preço Unitário (R$)", value=10.0, step=1.0)
                                ing_pack = i5.number_input("Embalagem Comercial (0 se granel)", value=1.0, step=0.1)
                                ing_sup = i6.selectbox("Fornecedor", [""] + list(suppliers_dict.keys()), format_func=lambda x: suppliers_dict.get(x, "Nenhum"), key=f"sup_ing_{r['id']}")

                                if st.form_submit_button("Incluir Ingrediente", type="primary", use_container_width=True):
                                    if ing_name.strip():
                                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                        orig_r = next(item for item in recipes if item["id"] == r["id"])
                                        orig_r.setdefault("ingredients", []).append({
                                            "name": ing_name.strip(),
                                            "quantity": float(ing_qty),
                                            "unit": ing_unit,
                                            "unit_price": float(ing_price),
                                            "package_size": float(ing_pack),
                                            "supplier_id": ing_sup
                                        })
                                        save_event_data(event_id, "recipes", recipes, user_name, f"Adicionou ingrediente '{ing_name}' à receita '{r.get('name')}'")
                                        st.success(f"Ingrediente '{ing_name}' adicionado!")
                                        st.rerun()

                    with col_ing_edit:
                        if ings:
                            with st.expander(f"✏️ Editar ou Remover Ingrediente"):
                                ing_options = {idx: f"{ing.get('name')} (Qtd: {ing.get('quantity')} {ing.get('unit')} | R$ {float(ing.get('unit_price', 0)):.2f})" for idx, ing in enumerate(ings)}
                                sel_idx = st.selectbox(
                                    "Escolha o ingrediente:",
                                    options=list(ing_options.keys()),
                                    format_func=lambda x: ing_options[x],
                                    key=f"select_ing_edit_{r['id']}"
                                )
                                curr_ing = ings[sel_idx]
                                with st.form(f"form_edit_ing_{r['id']}_{sel_idx}"):
                                    ei1, ei2, ei3 = st.columns([2, 1, 1])
                                    e_ing_name = ei1.text_input("Nome", value=curr_ing.get("name", ""))
                                    e_ing_qty = ei2.number_input("Qtd Base", value=float(curr_ing.get("quantity", 1.0)), step=0.1)
                                    unit_opts_ing = ["kg", "g", "L", "ml", "un", "maço", "pct"]
                                    u_ing_idx = unit_opts_ing.index(curr_ing.get("unit", "kg")) if curr_ing.get("unit") in unit_opts_ing else 0
                                    e_ing_unit = ei3.selectbox("Unidade", unit_opts_ing, index=u_ing_idx)

                                    ei4, ei5, ei6 = st.columns(3)
                                    e_ing_price = ei4.number_input("Preço Unit. (R$)", value=float(curr_ing.get("unit_price", 0.0)), step=0.5, format="%.2f")
                                    e_ing_pack = ei5.number_input("Embalagem Comercial", value=float(curr_ing.get("package_size", 1.0)), step=0.1)
                                    cur_sup = curr_ing.get("supplier_id") or ""
                                    sup_keys = [""] + list(suppliers_dict.keys())
                                    s_idx = sup_keys.index(cur_sup) if cur_sup in sup_keys else 0
                                    e_ing_sup = ei6.selectbox("Fornecedor", options=sup_keys, format_func=lambda x: suppliers_dict.get(x, "Nenhum"), index=s_idx)

                                    b_save_col, b_del_col = st.columns(2)
                                    with b_save_col:
                                        submit_save_ing = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                                    with b_del_col:
                                        submit_del_ing = st.form_submit_button("🗑️ Remover Ingrediente", use_container_width=True)

                                    if submit_save_ing:
                                        if e_ing_name.strip():
                                            user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                            orig_r = next(item for item in recipes if item["id"] == r["id"])
                                            if "ingredients" in orig_r and sel_idx < len(orig_r["ingredients"]):
                                                orig_r["ingredients"][sel_idx] = {
                                                    "name": e_ing_name.strip(),
                                                    "quantity": float(e_ing_qty),
                                                    "unit": e_ing_unit,
                                                    "unit_price": float(e_ing_price),
                                                    "package_size": float(e_ing_pack),
                                                    "supplier_id": e_ing_sup
                                                }
                                                save_event_data(event_id, "recipes", recipes, user_name, f"Atualizou ingrediente '{e_ing_name}' na receita '{r.get('name')}'")
                                                st.success(f"Ingrediente '{e_ing_name}' atualizado!")
                                                st.rerun()

                                    if submit_del_ing:
                                        user_name = st.session_state.get("user", {}).get("name", "Usuário")
                                        orig_r = next(item for item in recipes if item["id"] == r["id"])
                                        if "ingredients" in orig_r and sel_idx < len(orig_r["ingredients"]):
                                            removed_name = orig_r["ingredients"][sel_idx].get("name", "Ingrediente")
                                            orig_r["ingredients"].pop(sel_idx)
                                            save_event_data(event_id, "recipes", recipes, user_name, f"Removeu ingrediente '{removed_name}' da receita '{r.get('name')}'")
                                            st.warning(f"Ingrediente '{removed_name}' removido!")
                                            st.rerun()

                st.markdown("---")

    # ========================================================
    # ABA 3: LISTA CONSOLIDADA DE COMPRAS
    # ========================================================
    with tab3:
        st.subheader("🛒 Lista de Compras Completa e Unificada")
        st.caption("Todos os itens diretos e todos os ingredientes das receitas agrupados por fornecedor e categoria.")

        all_shopping_items = []
        for item in calc_items:
            all_shopping_items.append({
                "Origem": "Item Direto",
                "Item": item["name"],
                "Categoria": item.get("category", "Geral"),
                "Quantidade a Comprar": f"{item.get('adjusted_quantity')} {item.get('unit')}",
                "Embalagens Comerciais": f"{item.get('packages_needed')} un ({item.get('package_unit_name', '')})" if item.get('package_size', 0) > 0 else "-",
                "Preço Unit.": f"R$ {float(item.get('unit_price', 0)):.2f}",
                "Custo Estimado": float(item.get("total_cost", 0)),
                "Fornecedor": suppliers_dict.get(item.get("supplier_id"), "Não definido"),
                "Comprador / Responsável": item.get("assigned_collaborator", "-")
            })

        for ing in rec_summary.get("all_recipe_ingredients", []):
            all_shopping_items.append({
                "Origem": f"Receita: {ing.get('source_recipe')}",
                "Item": ing["name"],
                "Categoria": ing.get("category", "Ingredientes"),
                "Quantidade a Comprar": f"{ing.get('adjusted_quantity')} {ing.get('unit')}",
                "Embalagens Comerciais": "-",
                "Preço Unit.": f"R$ {float(ing.get('unit_price', 0)):.2f}",
                "Custo Estimado": float(ing.get("total_cost", 0)),
                "Fornecedor": suppliers_dict.get(ing.get("supplier_id"), "Não definido"),
                "Comprador / Responsável": ing.get("assigned_to", "-")
            })

        if all_shopping_items:
            df_shop = pd.DataFrame(all_shopping_items)
            total_lista = df_shop["Custo Estimado"].sum()

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                filtro_sup = st.selectbox("Filtrar por Fornecedor:", ["Todos"] + list(set(df_shop["Fornecedor"].tolist())))
            with c_f2:
                filtro_resp = st.selectbox("Filtrar por Responsável:", ["Todos"] + list(set(df_shop["Comprador / Responsável"].tolist())))

            df_filtrado = df_shop.copy()
            if filtro_sup != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Fornecedor"] == filtro_sup]
            if filtro_resp != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Comprador / Responsável"] == filtro_resp]

            df_display = df_filtrado.copy()
            df_display["Custo Estimado"] = df_display["Custo Estimado"].apply(lambda v: f"R$ {v:,.2f}")

            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.metric("Total da Lista (Filtrada)", f"R$ {df_filtrado['Custo Estimado'].sum():,.2f}")
        else:
            st.info("Nenhum item na lista de compras.")

