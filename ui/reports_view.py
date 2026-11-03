from config import get_now
from datetime import datetime

import pandas as pd

import streamlit as st

from services.calculation_service import calculate_consumables_totals, calculate_recipes_totals

from services.event_service import get_event, get_event_data

from services.pdf_service import (

    generate_cashflow_pdf,

    generate_general_event_pdf,

    generate_shopping_list_pdf,

    is_pdf_available,

)





def render_reports(event_id: str):

    meta = get_event(event_id)

    if not meta:

        st.error("Evento não localizado.")

        return



    st.title("📄 Relatórios do Evento e Emissão em PDF")

    st.caption("Consulte os relatórios analíticos interativos diretamente na tela ou emita cópias em formato PDF para distribuição.")



    participants = get_event_data(event_id, "participants")

    consumables = get_event_data(event_id, "consumables")

    recipes = get_event_data(event_id, "recipes")

    tasks = get_event_data(event_id, "tasks")

    cashflow = get_event_data(event_id, "cashflow")

    suppliers = get_event_data(event_id, "suppliers")

    suppliers_dict = {s["id"]: s["name"] for s in suppliers}



    confirmed_count = len([p for p in participants if p.get("confirmed", True)]) or len(participants) or 35

    calc_consumables, cons_summary = calculate_consumables_totals(consumables, confirmed_count)

    calc_recipes, rec_summary = calculate_recipes_totals(recipes, confirmed_count)



    tab1, tab2, tab3, tab4 = st.tabs([

        "📊 1. Relatório Geral do Evento",

        "💵 2. Prestação de Contas (Caixa)",

        "🛒 3. Lista de Compras c/ Arredondamento",

        "📌 4. Relatório de Tarefas & Colaboradores"

    ])



    # ========================================================

    # ABA 1: RELATÓRIO GERAL DO EVENTO

    # ========================================================

    with tab1:

        st.subheader(f"Relatório Geral: {meta.get('name')}")

        st.write(f"**Data Prevista:** {meta.get('date')} | **Descrição:** {meta.get('description', '-')}")



        c1, c2, c3 = st.columns(3)

        from services.event_service import get_event_financial_summary

        fin = get_event_financial_summary(event_id, confirmed_count)



        # Status do Balanço: Sobra ou Falta

        if fin["falta_arrecadar"] > 0:

            st.warning(

                f"⚠️ **Balanço da Arrecadação:** O total arrecadado (**R$ {fin['total_arrecadado']:,.2f}**) cobre **{fin['pct_meta']:.1f}%** das despesas previstas (**R$ {fin['previsto_total']:,.2f}**). "

                f"**FALTA ARRECADAR: R$ {fin['falta_arrecadar']:,.2f}** (em média **R$ {fin['falta_por_pessoa']:,.2f}** por participante confirmado)."

            )

        else:

            st.success(

                f"🎉 **Balanço da Arrecadação:** 100% das despesas previstas estão cobertas! "

                f"**SOBRA PREVISTA: R$ {fin['sobra_prevista']:,.2f}** (em média **R$ {fin['sobra_por_pessoa']:,.2f}** por participante)."

            )



        with c1:

            st.markdown("#### 👥 Participação")

            st.write(f"- Total de Inscritos: **{len(participants)} pessoas**")

            st.write(f"- Confirmados no cálculo: **{confirmed_count} pessoas**")

            st.write(f"- Pagantes Quitados: **{fin['qtd_cotas_pagas']} pessoas**")

            st.write(f"- **Total Arrecadado:** **R$ {fin['total_arrecadado']:,.2f}**")

            st.caption(f"Cotas: R$ {fin['total_cotas_pagas']:,.2f} | Fundo: R$ {fin['fundo_formatura_total']:,.2f}")



        with c2:

            st.markdown("#### 💰 Orçamento Estimado")

            st.write(f"- Consumíveis Diretos: **R$ {fin['custo_consumiveis_diretos']:,.2f}**")

            st.write(f"- Receitas Fabricadas: **R$ {fin['custo_receitas_fabricadas']:,.2f}**")

            if fin['custo_estrutura'] > 0:

                st.write(f"- Estrutura & Atrações: **R$ {fin['custo_estrutura']:,.2f}**")

            st.write(f"- **Total Orçado:** **R$ {fin['previsto_total']:,.2f}** (R$ {fin['custo_por_pessoa']:,.2f} / pessoa)")

            st.write(f"- **Saldo Líquido em Caixa:** **R$ {fin['saldo_caixa']:,.2f}**")



        with c3:

            st.markdown("#### 🥩🥤 Consumo por Pessoa")

            meat_g = cons_summary.get("meat_grams_per_person", 0.0)

            meat_tot = cons_summary.get("total_meat_kg", 0.0)

            drink_l = cons_summary.get("drinks_liters_per_person", 0.0)

            drink_ml = cons_summary.get("drinks_ml_per_person", 0.0)

            drink_tot = cons_summary.get("total_drinks_liters", 0.0)



            st.write(f"- 🥩 Carnes: **{meat_g:.0f} g / pessoa** (Total: **{meat_tot:.1f} kg**)")

            st.write(f"- 🥤 Bebidas: **{drink_l:.2f} L / pessoa** ({drink_ml:.0f} ml) (Total: **{drink_tot:.1f} L**)")

            st.write(f"- Variedade: **{cons_summary.get('meat_items_count', 0)}** carnes e **{cons_summary.get('drink_items_count', 0)}** bebidas")



        # Quadro Geral Lado a Lado (Entradas vs Despesas)

        st.markdown("##### 📋 Quadro Geral Financeiro do Evento")

        col_in_rep, col_out_rep = st.columns(2)

        with col_in_rep:

            with st.container(border=True):

                st.markdown(f"**💰 ENTRADAS DE VALORES & RECEITAS:** `R$ {fin['total_arrecadado']:,.2f}`")

                st.markdown(

                    f"""

                    - 🎓 **Fundo / Comissão de Formatura:** R$ {fin['fundo_formatura_total']:,.2f}

                    - 👥 **Cotas dos Alunos / Participantes:** R$ {fin['total_cotas_pagas']:,.2f} *({fin['qtd_cotas_pagas']} pagantes)*

                    - 💵 **Outras Receitas Financeiras / Aportes:** R$ {fin['outras_receitas_total']:,.2f}

                    """

                )

        with col_out_rep:

            with st.container(border=True):

                st.markdown(f"**🥩 DESPESAS TOTAIS PREVISTAS:** `R$ {fin['previsto_total']:,.2f}`")

                st.markdown(

                    f"""

                    - 🛒 **Consumíveis e Itens Diretos:** R$ {fin['custo_consumiveis_diretos']:,.2f}

                    - 🍲 **Receitas Fabricadas por Colaboradores:** R$ {fin['custo_receitas_fabricadas']:,.2f}

                    - 🎪 **Estrutura, Atrações & Locações:** R$ {fin['custo_estrutura']:,.2f}

                    """

                )



        st.markdown("---")



        # Botões de Emissão em PDF e Exportação em JSON

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:

            if is_pdf_available():

                pdf_bytes = generate_general_event_pdf(

                    meta, participants, calc_consumables, calc_recipes, tasks, cashflow, cons_summary, rec_summary

                )

                st.download_button(

                    label="📄 Baixar Relatório Geral em PDF",

                    data=pdf_bytes,

                    file_name=f"Relatorio_Geral_{event_id}.pdf",

                    mime="application/pdf",

                    type="primary",

                    use_container_width=True

                )

            else:

                st.warning("⚠️ Biblioteca 'fpdf2' não encontrada no ambiente atual. Para gerar PDFs, instale com: `pip install fpdf2`")



        with col_dl2:

            from services.backup_service import export_event_database_json_bytes

            ev_json_bytes = export_event_database_json_bytes(event_id)

            st.download_button(

                label="💾 Exportar Dados Deste Evento (.json)",

                data=ev_json_bytes,

                file_name=f"dados_evento_{event_id}_{get_now().strftime('%Y%m%d')}.json",

                mime="application/json",

                use_container_width=True

            )



        st.markdown("---")

        st.write("##### Itens Principais do Orçamento:")

        df_gen = pd.DataFrame([

            {

                "Item": c["name"],

                "Categoria": c.get("category", "-"),

                "Qtd Ajustada": f"{c.get('adjusted_quantity')} {c.get('unit')}",

                "Embalagens": f"{c.get('packages_needed')} un" if c.get("package_size", 0) > 0 else "-",

                "Preço Unit.": f"R$ {float(c.get('unit_price', 0)):.2f}",

                "Custo Total": f"R$ {float(c.get('total_cost', 0)):.2f}"

            }

            for c in calc_consumables

        ])

        st.dataframe(df_gen, use_container_width=True, hide_index=True)



        with st.expander("👥 Relação Geral de Participantes e Status de Pagamento", expanded=False):

            if participants:

                df_rep_parts = pd.DataFrame([

                    {

                        "Nome": p.get("name", "-"),

                        "Categoria": p.get("category", "Geral"),

                        "Presença": "✅ Confirmado" if p.get("confirmed", True) else "⏳ Ausente / Pend.",

                        "Status Cota": "🟢 Quitado" if p.get("paid", False) else "🔴 Pendente",

                        "Forma": p.get("payment_method", "-") if p.get("paid") else "-",

                        "Valor Cota": f"R$ {float(p.get('paid_amount', p.get('fee', 0.0)) or 0.0):.2f}" if p.get("paid") else f"R$ {float(p.get('fee', 0.0) or 0.0):.2f}"

                    }

                    for p in sorted(participants, key=lambda x: str(x.get("name", "")).lower())

                ])

                st.dataframe(df_rep_parts, use_container_width=True, hide_index=True)

            else:

                st.info("Nenhum participante registrado neste evento.")



    # ========================================================

    # ABA 2: PRESTAÇÃO DE CONTAS E FLUXO DE CAIXA

    # ========================================================

    with tab2:

        st.subheader("Relatório Financeiro e Prestação de Contas")

        entradas = [c for c in cashflow if c.get("type") == "ENTRADA"]

        saidas = [c for c in cashflow if c.get("type") == "SAIDA"]



        tot_in = sum(float(c.get("amount", 0)) for c in entradas)

        tot_out = sum(float(c.get("amount", 0)) for c in saidas)

        saldo = tot_in - tot_out



        r1, r2, r3 = st.columns(3)

        r1.metric("Entradas Totais", f"R$ {tot_in:,.2f}")

        r2.metric("Saídas / Reembolsos", f"R$ {tot_out:,.2f}")

        r3.metric("Saldo / Sobra Final", f"R$ {saldo:,.2f}")



        if is_pdf_available():

            pdf_cash_bytes = generate_cashflow_pdf(meta, cashflow, participants)

            st.download_button(

                label="📥 Baixar Prestação de Contas em PDF",

                data=pdf_cash_bytes,

                file_name=f"Prestacao_Contas_{event_id}.pdf",

                mime="application/pdf",

                type="primary"

            )

        else:

            st.warning("⚠️ Instale 'fpdf2' (`pip install fpdf2`) para habilitar o download em PDF.")



        st.markdown("---")

        st.write("##### Detalhamento de Entradas:")

        if entradas:

            df_in = pd.DataFrame([

                {"Data": e.get("date"), "Descrição": e.get("description"), "Origem": e.get("payer_or_receiver"), "Forma": e.get("payment_method"), "Valor": f"R$ {float(e.get('amount', 0)):.2f}"}

                for e in entradas

            ])

            st.dataframe(df_in, use_container_width=True, hide_index=True)



        st.write("##### Detalhamento de Saídas e Reembolsos:")

        if saidas:

            df_out = pd.DataFrame([

                {"Data": s.get("date"), "Descrição": s.get("description"), "Favorecido": s.get("payer_or_receiver"), "Forma": s.get("payment_method"), "Valor": f"R$ {float(s.get('amount', 0)):.2f}", "Observação": s.get("notes")}

                for s in saidas

            ])

            st.dataframe(df_out, use_container_width=True, hide_index=True)



    # ========================================================

    # ABA 3: LISTA DE COMPRAS COM ARREDONDAMENTO & RECEITAS

    # ========================================================

    with tab3:

        st.subheader("🛒 Relatório de Compras & Insumos para o Churrasco")

        st.caption("Detalhamento completo de todos os itens e receitas a serem comprados para o churrasco, com quantidades ajustadas para embalagens comerciais, preços unitários, custos totais, fornecedores e colaboradores responsáveis.")



        tot_dir = cons_summary.get("grand_total", 0.0)

        tot_rec = rec_summary.get("recipes_grand_total", 0.0)

        tot_geral = tot_dir + tot_rec

        custo_p = tot_geral / (confirmed_count or 1)



        # Métricas no topo

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Total Geral de Compras", f"R$ {tot_geral:,.2f}")

        m2.metric("Consumíveis Diretos", f"R$ {tot_dir:,.2f}", f"{len(calc_consumables)} itens")

        m3.metric("Receitas Fabricadas", f"R$ {tot_rec:,.2f}", f"{len(calc_recipes)} receitas")

        m4.metric("Custo / Participante", f"R$ {custo_p:,.2f}", f"Base: {confirmed_count} confirmados")



        st.markdown("---")



        # Botões de Download: PDF Completo e Planilha CSV

        col_dl_pdf, col_dl_csv = st.columns(2)

        with col_dl_pdf:

            if is_pdf_available():

                pdf_shop_bytes = generate_shopping_list_pdf(

                    meta, calc_consumables, calc_recipes, suppliers_dict, confirmed_count

                )

                st.download_button(

                    label="📄 Baixar Relatório de Compras em PDF (Completo)",

                    data=pdf_shop_bytes,

                    file_name=f"Relatorio_Compras_Churrasco_{event_id}.pdf",

                    mime="application/pdf",

                    type="primary",

                    use_container_width=True

                )

            else:

                st.warning("⚠️ Instale 'fpdf2' (`pip install fpdf2`) para habilitar o download em PDF.")



        with col_dl_csv:

            # Montagem de tabela consolidada para exportação em CSV (compatível com Excel)

            export_rows = []

            for c in calc_consumables:

                pack_info = c.get("package_unit_name") or (f"{c.get('package_size')} {c.get('unit')}" if c.get("package_size", 0) > 0 else "-")

                export_rows.append({

                    "Origem": "Consumível Direto",

                    "Receita": "-",

                    "Item / Ingrediente": c.get("name"),

                    "Categoria": c.get("category", "-"),

                    "Qtd Necessária": c.get("base_needed"),

                    "Qtd a Comprar (Ajustada)": c.get("adjusted_quantity"),

                    "Unidade": c.get("unit"),

                    "Embalagem Comercial": pack_info,

                    "Preço Unitário (R$)": c.get("unit_price"),

                    "Custo Total (R$)": c.get("total_cost"),

                    "Fornecedor": suppliers_dict.get(c.get("supplier_id"), "-"),

                    "Responsável": c.get("assigned_collaborator", "-")

                })

            for r in calc_recipes:

                for ing in r.get("ingredients", []):

                    export_rows.append({

                        "Origem": "Receita Fabricada",

                        "Receita": r.get("name"),

                        "Item / Ingrediente": ing.get("name"),

                        "Categoria": f"Receita: {r.get('name')}",

                        "Qtd Necessária": ing.get("needed_qty"),

                        "Qtd a Comprar (Ajustada)": ing.get("adjusted_qty"),

                        "Unidade": ing.get("unit"),

                        "Embalagem Comercial": f"{ing.get('package_size')} {ing.get('unit')}" if ing.get("package_size", 0) > 0 else "-",

                        "Preço Unitário (R$)": ing.get("unit_price"),

                        "Custo Total (R$)": ing.get("cost"),

                        "Fornecedor": suppliers_dict.get(ing.get("supplier_id"), "-"),

                        "Responsável": ing.get("assigned_to") or r.get("assigned_to", "-")

                    })

            if export_rows:

                df_export = pd.DataFrame(export_rows)

                csv_bytes = df_export.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")

                st.download_button(

                    label="📊 Baixar Lista Consolidada em CSV (Excel)",

                    data=csv_bytes,

                    file_name=f"Lista_Compras_Churrasco_{event_id}.csv",

                    mime="text/csv",

                    use_container_width=True

                )



        st.markdown("---")



        # ====================================================

        # BLOCO 1: RECEITAS FABRICADAS POR COLABORADORES

        # ====================================================

        st.write("### 🥗 1. Receitas Fabricadas por Colaboradores")

        st.caption("Receitas personalizadas (Farofas, Vinagretes, Sobremesas) com seus ingredientes detalhados, preços, rendimentos e responsáveis pelo preparo.")



        if calc_recipes:

            for r in calc_recipes:

                with st.container():

                    st.markdown(f"#### 🍲 Receita: {r.get('name')}")

                    col_r1, col_r2, col_r3 = st.columns([1.5, 1.5, 1.5])

                    with col_r1:

                        st.write(f"🧑‍🍳 **Chef / Responsável:** `{r.get('assigned_to', 'Não definido')}`")

                    with col_r2:

                        st.write(f"⚖️ **Rendimento Calculado:** `{r.get('total_yield_needed')} {r.get('yield_unit', 'kg')}`")

                    with col_r3:

                        st.write(f"💰 **Custo Total da Receita:** `R$ {float(r.get('total_cost', 0)):,.2f}`")



                    if r.get("instructions"):

                        st.caption(f"📝 *Modo de preparo:* {r.get('instructions')}")



                    ings = r.get("ingredients", [])

                    if ings:

                        df_rec_display = pd.DataFrame([

                            {

                                "Ingrediente / Insumo": ing.get("name"),

                                "Qtd Calculada": f"{ing.get('adjusted_qty')} {ing.get('unit')}",

                                "Preço Unitário": f"R$ {float(ing.get('unit_price', 0)):.2f}",

                                "Custo Total": f"R$ {float(ing.get('cost', 0)):.2f}",

                                "Fornecedor": suppliers_dict.get(ing.get("supplier_id"), "-"),

                                "Responsável": ing.get("assigned_to") or r.get("assigned_to", "-")

                            }

                            for ing in ings

                        ])

                        st.dataframe(df_rec_display, use_container_width=True, hide_index=True)

                    else:

                        st.warning("Nenhum ingrediente cadastrado para esta receita.")

                    st.write("")

        else:

            st.info("Nenhuma receita fabricada cadastrada para este evento.")



        st.markdown("---")



        # ====================================================

        # BLOCO 2: CONSUMÍVEIS DIRETOS

        # ====================================================

        st.write("### 🥩🥤 2. Consumíveis Diretos (Bebidas, Carnes, Gelo, Carvão, Descartáveis)")

        st.caption("Itens comprados prontos e agrupados por fornecedor e comprador responsável.")



        if calc_consumables:

            df_direct_display = pd.DataFrame([

                {

                    "Item": it.get("name"),

                    "Categoria": it.get("category", "-"),

                    "Embalagem Comercial": it.get("package_unit_name") or f"{it.get('package_size')} {it.get('unit')}",

                    "Qtd a Comprar": f"{it.get('adjusted_quantity')} {it.get('unit')}",

                    "Embalagens": f"{it.get('packages_needed')} un" if it.get("package_size", 0) > 0 else "-",

                    "Preço Unitário": f"R$ {float(it.get('unit_price', 0)):.2f}",

                    "Custo Total": f"R$ {float(it.get('total_cost', 0)):.2f}",

                    "Fornecedor": suppliers_dict.get(it.get("supplier_id"), "-"),

                    "Responsável pela Compra": it.get("assigned_collaborator", "-")

                }

                for it in calc_consumables

            ])

            st.dataframe(df_direct_display, use_container_width=True, hide_index=True)

        else:

            st.info("Nenhum consumível direto cadastrado para este evento.")



    # ========================================================

    # ABA 4: TAREFAS E COLABORADORES

    # ========================================================

    with tab4:

        st.subheader("Relatório de Atribuição de Tarefas e Execução")

        if tasks:

            df_tsk_rep = pd.DataFrame([

                {

                    "Tarefa": t.get("title"),

                    "Colaborador": t.get("assigned_to"),

                    "Prazo": t.get("deadline"),

                    "Status": t.get("status"),

                    "Orçamento": f"R$ {float(t.get('budget', 0)):.2f}",

                    "Gasto Real": f"R$ {float(t.get('actual_spent', 0)):.2f}",

                    "Instruções": t.get("description"),

                    "Notas de Execução": t.get("notes")

                }

                for t in tasks

            ])

            st.dataframe(df_tsk_rep, use_container_width=True, hide_index=True)

        else:

            st.info("Nenhuma tarefa cadastrada.")



