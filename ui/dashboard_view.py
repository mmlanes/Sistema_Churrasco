import pandas as pd
import streamlit as st
from services.event_service import get_event, get_event_data, get_event_financial_summary


def render_dashboard(event_id: str):
    meta = get_event(event_id)
    if not meta:
        st.error("Evento não localizado.")
        return

    participants = get_event_data(event_id, "participants")
    tasks = get_event_data(event_id, "tasks")

    # Contagem de participantes
    total_parts = len(participants)
    confirmed_parts = len([p for p in participants if p.get("confirmed", True)])
    count_for_calc = confirmed_parts if confirmed_parts > 0 else (total_parts or 1)

    # Resumo financeiro unificado do evento
    fin = get_event_financial_summary(event_id, count_for_calc)

    previsto_direto = fin["previsto_direto"]
    previsto_receitas = fin["previsto_receitas"]
    total_estrutura_extra = fin["total_estrutura_extra"]
    saidas_estrutura_extra = fin["saidas_estrutura_extra"]
    previsto_total = fin["previsto_total"]
    custo_por_pessoa = fin["custo_por_pessoa"]
    total_cotas_pagas = fin["total_cotas_pagas"]
    entradas_caixa_avulsas = fin["entradas_caixa_avulsas"]
    total_arrecadado = fin["total_arrecadado"]
    total_gasto_real = fin["total_gasto_real"]
    saldo_caixa = fin["saldo_caixa"]
    cons_summary = fin["cons_summary"]

    # Tarefas
    tarefas_totais = len(tasks)
    tarefas_feitas = len([t for t in tasks if t.get("status") == "Realizada"])
    tarefas_pendentes = len([t for t in tasks if t.get("status") == "Pendente"])
    tarefas_parciais = len([t for t in tasks if t.get("status") in ["Em Andamento", "Parcial"]])

    # Cabeçalho do Dashboard
    st.title(f"📊 Painel Geral - {meta.get('name')}")
    st.caption(f"📅 Data do Evento: {meta.get('date')} | Base em: `data/events/{event_id}/`")

    # Linha 1 de Métricas Gerais
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="👥 Participantes Confirmados",
            value=f"{confirmed_parts} pessoas",
            delta=f"Total: {total_parts}" if total_parts != confirmed_parts else None
        )
    with c2:
        st.metric(
            label="💰 Orçamento Total Previsto",
            value=f"R$ {previsto_total:,.2f}",
            delta=f"R$ {custo_por_pessoa:,.2f} / pessoa"
        )
    with c3:
        st.metric(
            label="💵 Total Arrecadado",
            value=f"R$ {total_arrecadado:,.2f}",
            delta=f"Cotas: R$ {total_cotas_pagas:,.0f} | Aportes: R$ {entradas_caixa_avulsas:,.0f}"
        )
    with c4:
        delta_color = "normal" if saldo_caixa >= 0 else "inverse"
        st.metric(
            label="🏦 Saldo / Sobra de Caixa",
            value=f"R$ {saldo_caixa:,.2f}",
            delta=f"Gasto Real: R$ {total_gasto_real:,.2f}",
            delta_color=delta_color
        )

    # Linha 2 de Métricas: Consumo Per Capita (Carnes e Bebidas do Churrasco)
    k1, k2, k3 = st.columns(3)
    meat_g = cons_summary.get("meat_grams_per_person", 0.0)
    meat_kg_p = cons_summary.get("meat_kg_per_person", 0.0)
    meat_tot = cons_summary.get("total_meat_kg", 0.0)
    meat_count = cons_summary.get("meat_items_count", 0)

    drink_l = cons_summary.get("drinks_liters_per_person", 0.0)
    drink_ml = cons_summary.get("drinks_ml_per_person", 0.0)
    drink_tot = cons_summary.get("total_drinks_liters", 0.0)
    drink_count = cons_summary.get("drink_items_count", 0)

    with k1:
        st.metric(
            label="🥩 Carnes por Pessoa",
            value=f"{meat_g:.0f} g / pessoa" if meat_g < 1000 else f"{meat_kg_p:.2f} kg / pessoa",
            delta=f"Total: {meat_tot:.1f} kg ({meat_count} tipos)",
            delta_color="normal"
        )
    with k2:
        st.metric(
            label="🥤 Bebidas por Pessoa",
            value=f"{drink_l:.2f} L / pessoa" if drink_l >= 1 else f"{drink_ml:.0f} ml / pessoa",
            delta=f"Total: {drink_tot:.1f} L ({drink_count} bebidas)",
            delta_color="normal"
        )
    with k3:
        st.metric(
            label="🍽️ Custo Estimado / Pessoa",
            value=f"R$ {custo_por_pessoa:,.2f}",
            delta=f"Previsto: R$ {previsto_total:,.2f}",
            delta_color="off"
        )

    # Se houver itens de estrutura e atrações (como Futebol de Sabão)
    estrutura_items = [
        c for c in fin["calc_consumables"] 
        if "estrutura" in str(c.get("category", "")).lower() or "atração" in str(c.get("category", "")).lower() or "brinquedo" in str(c.get("category", "")).lower()
    ] + saidas_estrutura_extra

    if estrutura_items:
        with st.expander("🎪 Ver Atrações, Estrutura e Locações Contratadas", expanded=True):
            cols_est = st.columns(min(len(estrutura_items), 3))
            for idx, item in enumerate(estrutura_items):
                with cols_est[idx % len(cols_est)]:
                    st.markdown(
                        f"""
                        <div style="background: rgba(99, 102, 241, 0.08); border-left: 4px solid #6366F1; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                            <div style="font-weight: bold; color: #4338CA;">🎪 {item.get('name')}</div>
                            <div style="font-size: 0.9rem; color: #374151;">Valor: <b>R$ {float(item.get('total_cost', 0)):,.2f}</b> | Tipo: Custo Fixo do Evento</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    st.markdown("---")

    # Gráficos e Distribuições
    gcol1, gcol2 = st.columns([1.2, 1])

    with gcol1:
        st.subheader("📈 Comparativo Financeiro")
        df_comp = pd.DataFrame({
            "Categoria": ["Orçamento Previsto", "Total Arrecadado", "Gastos Reais Efetuados", "Saldo / Sobra"],
            "Valor (R$)": [previsto_total, total_arrecadado, total_gasto_real, max(saldo_caixa, 0)]
        })
        st.bar_chart(df_comp.set_index("Categoria"), color="#2563EB", use_container_width=True)

    with gcol2:
        st.subheader("🥩 Custos Previstos por Categoria")
        # Combina categorias dos consumíveis com receitas e estrutura
        cat_data = dict(cons_summary.get("category_totals", {}))
        if previsto_receitas > 0:
            cat_data["Receitas Próprias (Farofa/Vinagrete)"] = previsto_receitas
        if total_estrutura_extra > 0 and "🎪 Estrutura & Atrações" not in cat_data:
            cat_data["🎪 Estrutura & Atrações"] = total_estrutura_extra

        if cat_data:
            df_cat = pd.DataFrame(list(cat_data.items()), columns=["Categoria", "Valor (R$)"])
            st.bar_chart(df_cat.set_index("Categoria"), color="#DC2626", use_container_width=True)
        else:
            st.info("Nenhum consumível cadastrado ainda.")

    st.markdown("---")

    # Linha 3: Tarefas e Alertas
    tcol1, tcol2 = st.columns([1, 1])

    with tcol1:
        st.subheader("📋 Execução das Tarefas")
        st.write(f"- ✅ **Realizadas:** {tarefas_feitas}")
        st.write(f"- ⏳ **Parciais / Em Andamento:** {tarefas_parciais}")
        st.write(f"- ⚠️ **Pendentes:** {tarefas_pendentes}")
        
        progresso = (tarefas_feitas / tarefas_totais) if tarefas_totais > 0 else 0.0
        st.progress(progresso, text=f"Progresso Geral: {int(progresso * 100)}%")

        if tarefas_pendentes > 0:
            st.warning(f"Existem **{tarefas_pendentes} tarefa(s) pendente(s)** precisando de atenção dos colaboradores.")

    with tcol2:
        st.subheader("💡 Resumo de Atribuições Importantes")
        if tasks:
            for t in tasks[:4]:
                st_icon = "✅" if t.get("status") == "Realizada" else ("⏳" if t.get("status") == "Em Andamento" else "⚠️")
                st.write(f"{st_icon} **{t.get('title')}** → Colaborador: *{t.get('assigned_to', 'Não atribuído')}* ({t.get('status')})")
        else:
            st.info("Nenhuma tarefa atribuída ainda.")

