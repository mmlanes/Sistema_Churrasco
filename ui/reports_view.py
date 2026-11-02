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
        with c1:
            st.markdown("#### 👥 Participação")
            st.write(f"- Total de Inscritos: **{len(participants)} pessoas**")
            st.write(f"- Confirmados no cálculo: **{confirmed_count} pessoas**")
            total_arrecadado = sum(float(p.get("paid_amount", 0)) for p in participants if p.get("paid"))
            st.write(f"- Valor Total Quitado: **R$ {total_arrecadado:,.2f}**")

        with c2:
            st.markdown("#### 💰 Orçamento Estimado")
            prev_direto = cons_summary["grand_total"]
            prev_rec = rec_summary["recipes_grand_total"]
            prev_total = prev_direto + prev_rec
            st.write(f"- Consumíveis Diretos: **R$ {prev_direto:,.2f}**")
            st.write(f"- Receitas Fabricadas: **R$ {prev_rec:,.2f}**")
            st.write(f"- **Total Orçado:** **R$ {prev_total:,.2f}** (R$ {(prev_total / confirmed_count):,.2f} / pessoa)")

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

        st.markdown("---")

        # Botão de Emissão em PDF
        if is_pdf_available():
            pdf_bytes = generate_general_event_pdf(
                meta, participants, calc_consumables, calc_recipes, tasks, cashflow, cons_summary, rec_summary
            )
            st.download_button(
                label="📥 Baixar Relatório Geral em PDF",
                data=pdf_bytes,
                file_name=f"Relatorio_Geral_{event_id}.pdf",
                mime="application/pdf",
                type="primary"
            )
        else:
            st.warning("⚠️ Biblioteca 'fpdf2' não encontrada no ambiente atual. Para gerar PDFs, instale com: `pip install fpdf2`")

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
    # ABA 3: LISTA DE COMPRAS COM ARREDONDAMENTO
    # ========================================================
    with tab3:
        st.subheader("Lista de Compras com Ajuste de Embalagens Comerciais")
        st.caption("Evita faltas no churrasco arredondando garrafas de 2L/3L, fardos e ingredientes inteiros.")

        recipe_ings = rec_summary.get("all_recipe_ingredients", [])
        if is_pdf_available():
            pdf_shop_bytes = generate_shopping_list_pdf(meta, calc_consumables, recipe_ings, suppliers_dict)
            st.download_button(
                label="📥 Baixar Lista de Compras em PDF",
                data=pdf_shop_bytes,
                file_name=f"Lista_Compras_{event_id}.pdf",
                mime="application/pdf",
                type="primary"
            )
        else:
            st.warning("⚠️ Instale 'fpdf2' (`pip install fpdf2`) para habilitar o download em PDF.")

        st.markdown("---")
        st.write("##### Bebidas e Consumíveis Principais:")
        df_shop_v = pd.DataFrame([
            {
                "Item": it["name"],
                "Embalagem Comercial": it.get("package_unit_name", f"{it.get('package_size')} {it.get('unit')}"),
                "Qtd Mínima": f"{it.get('base_needed')} {it.get('unit')}",
                "Embalagens a Comprar": f"{it.get('packages_needed')} un" if it.get("package_size", 0) > 0 else "-",
                "Volume/Peso Final": f"{it.get('adjusted_quantity')} {it.get('unit')}",
                "Preço Unitário": f"R$ {float(it.get('unit_price', 0)):.2f}",
                "Custo Total": f"R$ {float(it.get('total_cost', 0)):.2f}",
                "Fornecedor": suppliers_dict.get(it.get("supplier_id"), "-")
            }
            for it in calc_consumables
        ])
        st.dataframe(df_shop_v, use_container_width=True, hide_index=True)

        if recipe_ings:
            st.write("##### Ingredientes para Farofas e Vinagretes:")
            df_rec_v = pd.DataFrame([
                {
                    "Ingrediente": ing.get("name"),
                    "Receita": ing.get("source_recipe"),
                    "Qtd Calculada": f"{ing.get('adjusted_quantity')} {ing.get('unit')}",
                    "Preço Unitário": f"R$ {float(ing.get('unit_price', 0)):.2f}",
                    "Custo Estimado": f"R$ {float(ing.get('total_cost', 0)):.2f}",
                    "Fornecedor": suppliers_dict.get(ing.get("supplier_id"), "-")
                }
                for ing in recipe_ings
            ])
            st.dataframe(df_rec_v, use_container_width=True, hide_index=True)

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

