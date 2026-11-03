import io
from datetime import datetime
from typing import Any, Dict, List

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    FPDF = object
    HAS_FPDF = False


def is_pdf_available() -> bool:
    return HAS_FPDF


def clean_txt(text: Any) -> str:
    """Garante compatibilidade com latin-1 nas fontes nativas do PDF."""
    if text is None:
        return ""
    s = str(text)
    # Substituições comuns de caracteres que possam quebrar em latin-1
    replacements = {
        "–": "-", "—": "-", """: '"', """: '"', "’": "'", "‘": "'",
        "•": "*", "…": "...", "º": "o", "ª": "a", "🔥": ""
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def fmt_moeda(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ChurrascoPDF(FPDF):
    def __init__(self, title_doc: str, event_name: str):
        super().__init__()
        self.title_doc = title_doc
        self.event_name = event_name

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(20, 30, 60)
        self.cell(0, 10, clean_txt(f"Calculadora de Churrasco - {self.event_name}"), new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(90, 100, 110)
        self.cell(0, 6, clean_txt(f"{self.title_doc} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"), new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, clean_txt(f"Página {self.page_no()}/{{nb}} - Sistema de Gestão e Calculadora de Churrasco"), align="C")


def generate_general_event_pdf(
    event_meta: Dict[str, Any],
    participants: List[Dict[str, Any]],
    consumables: List[Dict[str, Any]],
    recipes: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    cashflow: List[Dict[str, Any]],
    consumables_summary: Dict[str, Any],
    recipes_summary: Dict[str, Any]
) -> bytes:
    """Gera o Relatório Executivo e Geral do Evento."""
    pdf = ChurrascoPDF("Relatório Geral do Evento", event_meta.get("name", "Evento"))
    pdf.alias_nb_pages()
    pdf.add_page()

    # Informações Básicas
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, clean_txt("1. RESUMO GERAL DO EVENTO"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(95, 6, clean_txt(f"Nome do Evento: {event_meta.get('name')}"))
    pdf.cell(95, 6, clean_txt(f"Data: {event_meta.get('date')}"), new_x="LMARGIN", new_y="NEXT")
    
    total_parts = len(participants)
    confirmed_parts = len([p for p in participants if p.get("confirmed")])

    # Unificação de arrecadação (Cotas + Fundo de Formatura + Outras entradas)
    cotas_alunos = sum(float(p.get("paid_amount", 0) or 0) for p in participants if p.get("paid"))
    entradas_caixa_avulsas = sum(
        float(c.get("amount", 0)) for c in cashflow
        if c.get("type") == "ENTRADA" and not c.get("is_participant_fee") and "cotas dos participantes" not in str(c.get("description", "")).lower() and str(c.get("category", "")) != "Cotas dos Participantes"
    )
    total_collected = cotas_alunos + entradas_caixa_avulsas

    pdf.cell(95, 6, clean_txt(f"Total Participantes: {total_parts} (Confirmados: {confirmed_parts})"))
    pdf.cell(95, 6, clean_txt(f"Total Arrecadado: {fmt_moeda(total_collected)}"), new_x="LMARGIN", new_y="NEXT")

    total_previsto = consumables_summary.get("grand_total", 0.0) + recipes_summary.get("recipes_grand_total", 0.0)
    cost_per_person = total_previsto / (confirmed_parts or 1)
    
    balanco_val = total_collected - total_previsto
    balanco_label = f"Sobra Prevista: {fmt_moeda(balanco_val)}" if balanco_val >= 0 else f"Falta Arrecadar: {fmt_moeda(abs(balanco_val))}"

    pdf.cell(95, 6, clean_txt(f"Orçamento Previsto (Itens + Receitas): {fmt_moeda(total_previsto)}"))
    pdf.cell(95, 6, clean_txt(f"Balanço: {balanco_label}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, clean_txt(f"Custo Estimado / Pessoa: {fmt_moeda(cost_per_person)}"))

    meat_g = consumables_summary.get("meat_grams_per_person", 0.0)
    meat_tot = consumables_summary.get("total_meat_kg", 0.0)
    drink_l = consumables_summary.get("drinks_liters_per_person", 0.0)
    drink_tot = consumables_summary.get("total_drinks_liters", 0.0)
    pdf.cell(95, 6, clean_txt(f"Carnes / Pessoa: {meat_g:.0f} g (Total: {meat_tot:.1f} kg)"))
    pdf.cell(95, 6, clean_txt(f"Bebidas / Pessoa: {drink_l:.2f} L (Total: {drink_tot:.1f} L)"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 2. Resumo de Consumíveis Principais
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, clean_txt("2. CONSUMÍVEIS E ITENS DIRETOS"), new_x="LMARGIN", new_y="NEXT")
    
    # Cabeçalho Tabela
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 6, clean_txt("Item"), border=1, fill=True)
    pdf.cell(30, 6, clean_txt("Categoria"), border=1, fill=True)
    pdf.cell(25, 6, clean_txt("Qtd/Pessoa"), border=1, fill=True, align="C")
    pdf.cell(25, 6, clean_txt("Qtd Ajustada"), border=1, fill=True, align="C")
    pdf.cell(25, 6, clean_txt("Preço Unit."), border=1, fill=True, align="R")
    pdf.cell(25, 6, clean_txt("Total"), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    for c in consumables:
        pdf.cell(60, 5, clean_txt(c.get("name", "")[:35]), border=1)
        pdf.cell(30, 5, clean_txt(c.get("category", "")[:18]), border=1)
        pdf.cell(25, 5, clean_txt(f"{c.get('per_person', 0)} {c.get('unit', '')}"), border=1, align="C")
        pdf.cell(25, 5, clean_txt(f"{c.get('adjusted_quantity', 0)} {c.get('unit', '')}"), border=1, align="C")
        pdf.cell(25, 5, clean_txt(fmt_moeda(float(c.get("unit_price", 0)))), border=1, align="R")
        pdf.cell(25, 5, clean_txt(fmt_moeda(float(c.get("total_cost", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(165, 6, clean_txt("Subtotal Consumíveis Diretos:"), border=1, align="R")
    pdf.cell(25, 6, clean_txt(fmt_moeda(consumables_summary.get("grand_total", 0.0))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 3. Itens Fabricados / Receitas (Farofa, Vinagrete, etc.)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, clean_txt("3. RECEITAS FABRICADAS POR COLABORADORES (Farofas, Vinagretes, etc.)"), new_x="LMARGIN", new_y="NEXT")

    for r in recipes:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(248, 248, 248)
        pdf.cell(0, 6, clean_txt(f"Receita: {r.get('name')} | Responsável: {r.get('assigned_to', 'Não definido')} | Custo: {fmt_moeda(r.get('total_cost', 0))}"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(80, 5, clean_txt("Ingrediente"), border=1)
        pdf.cell(35, 5, clean_txt("Qtd Calculada"), border=1, align="C")
        pdf.cell(35, 5, clean_txt("Preço Unit."), border=1, align="R")
        pdf.cell(40, 5, clean_txt("Custo Total"), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 8)
        for ing in r.get("ingredients", []):
            pdf.cell(80, 5, clean_txt(ing.get("name", "")[:45]), border=1)
            pdf.cell(35, 5, clean_txt(f"{ing.get('adjusted_qty', 0)} {ing.get('unit', '')}"), border=1, align="C")
            pdf.cell(35, 5, clean_txt(fmt_moeda(float(ing.get("unit_price", 0)))), border=1, align="R")
            pdf.cell(40, 5, clean_txt(fmt_moeda(float(ing.get("cost", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # 4. Status das Tarefas dos Colaboradores
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, clean_txt("4. QUADRO DE TAREFAS DOS COLABORADORES"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(65, 6, clean_txt("Tarefa"), border=1, fill=True)
    pdf.cell(40, 6, clean_txt("Colaborador"), border=1, fill=True)
    pdf.cell(25, 6, clean_txt("Prazo"), border=1, fill=True, align="C")
    pdf.cell(30, 6, clean_txt("Status"), border=1, fill=True, align="C")
    pdf.cell(30, 6, clean_txt("Gasto Real"), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    for t in tasks:
        pdf.cell(65, 5, clean_txt(t.get("title", "")[:35]), border=1)
        pdf.cell(40, 5, clean_txt(t.get("assigned_to", "Pendente")[:25]), border=1)
        pdf.cell(25, 5, clean_txt(t.get("deadline", "")), border=1, align="C")
        pdf.cell(30, 5, clean_txt(t.get("status", "")), border=1, align="C")
        pdf.cell(30, 5, clean_txt(fmt_moeda(float(t.get("actual_spent", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def generate_cashflow_pdf(
    event_meta: Dict[str, Any],
    cashflow_items: List[Dict[str, Any]],
    participants: List[Dict[str, Any]]
) -> bytes:
    """Gera o Relatório Financeiro e Prestação de Contas em PDF."""
    pdf = ChurrascoPDF("Prestação de Contas e Fluxo de Caixa", event_meta.get("name", "Evento"))
    pdf.alias_nb_pages()
    pdf.add_page()

    entradas = [c for c in cashflow_items if c.get("type") == "ENTRADA"]
    saidas = [c for c in cashflow_items if c.get("type") == "SAIDA"]

    total_in = sum(float(c.get("amount", 0)) for c in entradas)
    total_out = sum(float(c.get("amount", 0)) for c in saidas)
    saldo = total_in - total_out

    # Resumo do Caixa
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, clean_txt("RESUMO DO CAIXA"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(60, 7, clean_txt(f"Total de Entradas: {fmt_moeda(total_in)}"), border=1)
    pdf.cell(60, 7, clean_txt(f"Total de Gastos/Saídas: {fmt_moeda(total_out)}"), border=1)
    pdf.cell(70, 7, clean_txt(f"SALDO FINAL / SOBRA: {fmt_moeda(saldo)}"), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Tabela de Entradas
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 100, 30)
    pdf.cell(0, 7, clean_txt("ENTRADAS (Contribuições e Recebimentos)"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(25, 6, clean_txt("Data"), border=1, fill=True)
    pdf.cell(70, 6, clean_txt("Descrição"), border=1, fill=True)
    pdf.cell(45, 6, clean_txt("Origem/Pagador"), border=1, fill=True)
    pdf.cell(20, 6, clean_txt("Forma"), border=1, fill=True, align="C")
    pdf.cell(30, 6, clean_txt("Valor"), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 30, 30)
    for c in entradas:
        pdf.cell(25, 5, clean_txt(c.get("date", "")), border=1)
        pdf.cell(70, 5, clean_txt(c.get("description", "")[:45]), border=1)
        pdf.cell(45, 5, clean_txt(c.get("payer_or_receiver", "")[:28]), border=1)
        pdf.cell(20, 5, clean_txt(c.get("payment_method", "")), border=1, align="C")
        pdf.cell(30, 5, clean_txt(fmt_moeda(float(c.get("amount", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # Tabela de Saídas e Reembolsos
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(160, 30, 30)
    pdf.cell(0, 7, clean_txt("SAÍDAS (Gastos, Compras e Reembolsos PIX)"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(25, 6, clean_txt("Data"), border=1, fill=True)
    pdf.cell(70, 6, clean_txt("Descrição"), border=1, fill=True)
    pdf.cell(45, 6, clean_txt("Destino/Favorecido"), border=1, fill=True)
    pdf.cell(20, 6, clean_txt("Forma"), border=1, fill=True, align="C")
    pdf.cell(30, 6, clean_txt("Valor"), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 30, 30)
    for c in saidas:
        pdf.cell(25, 5, clean_txt(c.get("date", "")), border=1)
        pdf.cell(70, 5, clean_txt(c.get("description", "")[:45]), border=1)
        pdf.cell(45, 5, clean_txt(c.get("payer_or_receiver", "")[:28]), border=1)
        pdf.cell(20, 5, clean_txt(c.get("payment_method", "")), border=1, align="C")
        pdf.cell(30, 5, clean_txt(fmt_moeda(float(c.get("amount", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def generate_shopping_list_pdf(
    event_meta: Dict[str, Any],
    consumables: List[Dict[str, Any]],
    recipes: List[Dict[str, Any]],
    suppliers_dict: Dict[str, str],
    participant_count: int = 0
) -> bytes:
    """
    Gera o Relatório Detalhado da Lista de Compras para o Churrasco,
    incluindo itens diretos e todas as receitas fabricadas, com seus
    ingredientes, unidades, quantidades, preços unitários, custos totais e responsáveis.
    """
    pdf = ChurrascoPDF("Relatório de Compras & Insumos", event_meta.get("name", "Evento"))
    pdf.alias_nb_pages()
    pdf.add_page()

    # Normalização de receitas (seja calc_recipes completo ou lista plana de ingredientes)
    normalized_recipes = []
    if recipes:
        if isinstance(recipes[0], dict) and "ingredients" in recipes[0]:
            normalized_recipes = recipes
        else:
            rec_map = {}
            for ing in recipes:
                src = ing.get("source_recipe", "Receita Fabricada")
                if src not in rec_map:
                    rec_map[src] = {
                        "name": src,
                        "assigned_to": ing.get("assigned_to", "Colaborador"),
                        "total_cost": 0.0,
                        "ingredients": []
                    }
                rec_map[src]["ingredients"].append(ing)
                rec_map[src]["total_cost"] += float(ing.get("total_cost", 0))
            normalized_recipes = list(rec_map.values())

    tot_consumables = sum(float(c.get("total_cost", 0)) for c in consumables)
    tot_recipes = sum(float(r.get("total_cost", 0)) for r in normalized_recipes)
    grand_total = tot_consumables + tot_recipes
    cost_per_person = grand_total / (participant_count or 1) if participant_count else 0.0

    # 1. Bloco de Informações Básicas / Resumo
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 7, clean_txt("INFORMAÇÕES GERAIS DE COMPRAS E INSUMOS"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(95, 6, clean_txt(f"Evento: {event_meta.get('name', 'Churrasco')}"))
    pdf.cell(95, 6, clean_txt(f"Data Prevista: {event_meta.get('date', '-')}"), new_x="LMARGIN", new_y="NEXT")

    part_txt = f"{participant_count} pessoas confirmadas" if participant_count else "Conforme planejamento"
    pdf.cell(95, 6, clean_txt(f"Base de Cálculo: {part_txt}"))
    pdf.cell(95, 6, clean_txt(f"Valor Total Estimado: {fmt_moeda(grand_total)}"), new_x="LMARGIN", new_y="NEXT")
    if participant_count:
        pdf.cell(95, 6, clean_txt(f"Custo Médio / Participante: {fmt_moeda(cost_per_person)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 2. Seção de Itens Diretos
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 7, clean_txt("1. CONSUMÍVEIS DIRETOS (BEBIDAS, CARNES, GELO, CARVÃO, DESCARTÁVEIS)"), new_x="LMARGIN", new_y="NEXT")

    # Colunas: Item(42), Categoria(22), Qtd/Emb(28), Preço(20), Total(22), Fornecedor(30), Responsável(26) = 190mm
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 235, 245)
    pdf.cell(42, 6, clean_txt("Item"), border=1, fill=True)
    pdf.cell(22, 6, clean_txt("Categoria"), border=1, fill=True)
    pdf.cell(28, 6, clean_txt("Qtd a Comprar"), border=1, fill=True, align="C")
    pdf.cell(20, 6, clean_txt("Preço Unit."), border=1, fill=True, align="R")
    pdf.cell(22, 6, clean_txt("Custo Total"), border=1, fill=True, align="R")
    pdf.cell(30, 6, clean_txt("Fornecedor"), border=1, fill=True)
    pdf.cell(26, 6, clean_txt("Responsável"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 30, 30)
    for c in consumables:
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(230, 235, 245)
            pdf.cell(42, 6, clean_txt("Item"), border=1, fill=True)
            pdf.cell(22, 6, clean_txt("Categoria"), border=1, fill=True)
            pdf.cell(28, 6, clean_txt("Qtd a Comprar"), border=1, fill=True, align="C")
            pdf.cell(20, 6, clean_txt("Preço Unit."), border=1, fill=True, align="R")
            pdf.cell(22, 6, clean_txt("Custo Total"), border=1, fill=True, align="R")
            pdf.cell(30, 6, clean_txt("Fornecedor"), border=1, fill=True)
            pdf.cell(26, 6, clean_txt("Responsável"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8)

        sup_name = suppliers_dict.get(c.get("supplier_id"), "-") or "-"
        resp_name = c.get("assigned_collaborator", "-") or "-"
        qtd_txt = f"{c.get('adjusted_quantity', 0)} {c.get('unit', '')}"
        if c.get("package_size", 0) > 0 and c.get("packages_needed", 0) > 0:
            qtd_txt = f"{c.get('packages_needed')}x ({c.get('adjusted_quantity')} {c.get('unit', '')})"

        pdf.cell(42, 5, clean_txt(c.get("name", "")[:24]), border=1)
        pdf.cell(22, 5, clean_txt(c.get("category", "")[:13]), border=1)
        pdf.cell(28, 5, clean_txt(qtd_txt[:18]), border=1, align="C")
        pdf.cell(20, 5, clean_txt(fmt_moeda(float(c.get("unit_price", 0)))), border=1, align="R")
        pdf.cell(22, 5, clean_txt(fmt_moeda(float(c.get("total_cost", 0)))), border=1, align="R")
        pdf.cell(30, 5, clean_txt(sup_name[:18]), border=1)
        pdf.cell(26, 5, clean_txt(resp_name[:16]), border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(112, 6, clean_txt("Subtotal Consumíveis Diretos:"), border=1, align="R")
    pdf.cell(22, 6, clean_txt(fmt_moeda(tot_consumables)), border=1, align="R")
    pdf.cell(56, 6, clean_txt(""), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 3. Seção de Receitas Fabricadas por Colaboradores
    if normalized_recipes:
        if pdf.get_y() > 235:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 7, clean_txt("2. RECEITAS FABRICADAS POR COLABORADORES (FAROFAS, VINAGRETES, ACOMPANHAMENTOS)"), new_x="LMARGIN", new_y="NEXT")

        for r in normalized_recipes:
            if pdf.get_y() > 225:
                pdf.add_page()

            # Cabeçalho da Receita com Chef / Responsável e Rendimento
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(245, 248, 252)
            pdf.set_text_color(20, 30, 60)
            rec_title = f"RECEITA: {r.get('name')} | Responsável: {r.get('assigned_to', 'Não definido')}"
            rec_sub = f"Rendimento Calculado: {r.get('total_yield_needed', '-')} {r.get('yield_unit', 'kg')} | Custo da Receita: {fmt_moeda(float(r.get('total_cost', 0)))}"
            pdf.cell(0, 6, clean_txt(rec_title), border="LTR", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, clean_txt(rec_sub), border="LBR", fill=True, new_x="LMARGIN", new_y="NEXT")

            # Colunas da Tabela de Ingredientes:
            # Ingrediente(52), Qtd(24), Unidade(16), Preço(22), Total(24), Fornecedor(28), Responsável(24) = 190mm
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(235, 240, 248)
            pdf.set_text_color(40, 50, 70)
            pdf.cell(52, 5, clean_txt("Ingrediente / Insumo"), border=1, fill=True)
            pdf.cell(24, 5, clean_txt("Qtd a Comprar"), border=1, fill=True, align="C")
            pdf.cell(16, 5, clean_txt("Unidade"), border=1, fill=True, align="C")
            pdf.cell(22, 5, clean_txt("Preço Unit."), border=1, fill=True, align="R")
            pdf.cell(24, 5, clean_txt("Custo Total"), border=1, fill=True, align="R")
            pdf.cell(28, 5, clean_txt("Fornecedor"), border=1, fill=True)
            pdf.cell(24, 5, clean_txt("Responsável"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

            ings = r.get("ingredients", [])
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(30, 30, 30)
            rec_cost = 0.0

            if ings:
                for ing in ings:
                    if pdf.get_y() > 272:
                        pdf.add_page()
                    ing_name = ing.get("name", "")
                    if " (p/ " in ing_name:
                        ing_name = ing_name.split(" (p/ ")[0]
                    ing_qty = ing.get("adjusted_qty") if ing.get("adjusted_qty") is not None else ing.get("adjusted_quantity", 0)
                    ing_unit = ing.get("unit", "")
                    ing_price = float(ing.get("unit_price", 0))
                    ing_cost = float(ing.get("cost") if ing.get("cost") is not None else ing.get("total_cost", 0))
                    rec_cost += ing_cost
                    ing_sup = suppliers_dict.get(ing.get("supplier_id"), "-") or "-"
                    ing_resp = ing.get("assigned_to") or r.get("assigned_to", "-") or "-"

                    pdf.cell(52, 5, clean_txt(ing_name[:30]), border=1)
                    pdf.cell(24, 5, clean_txt(str(ing_qty)), border=1, align="C")
                    pdf.cell(16, 5, clean_txt(str(ing_unit)[:10]), border=1, align="C")
                    pdf.cell(22, 5, clean_txt(fmt_moeda(ing_price)), border=1, align="R")
                    pdf.cell(24, 5, clean_txt(fmt_moeda(ing_cost)), border=1, align="R")
                    pdf.cell(28, 5, clean_txt(ing_sup[:17]), border=1)
                    pdf.cell(24, 5, clean_txt(ing_resp[:15]), border=1, new_x="LMARGIN", new_y="NEXT")

                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(114, 5, clean_txt(f"Subtotal Receita '{r.get('name')}':"), border=1, align="R")
                pdf.cell(24, 5, clean_txt(fmt_moeda(rec_cost or float(r.get("total_cost", 0)))), border=1, align="R")
                pdf.cell(52, 5, clean_txt(""), border=1, new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.cell(190, 5, clean_txt("Nenhum ingrediente cadastrado nesta receita."), border=1, align="C", new_x="LMARGIN", new_y="NEXT")

            pdf.ln(3)

        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(114, 6, clean_txt("Subtotal Geral de Todas as Receitas:"), border=1, align="R")
        pdf.cell(24, 6, clean_txt(fmt_moeda(tot_recipes)), border=1, align="R")
        pdf.cell(52, 6, clean_txt(""), border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # 4. Resumo Financeiro Consolidado
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(225, 235, 250)
    pdf.set_text_color(10, 30, 70)
    pdf.cell(0, 7, clean_txt("3. RESUMO GERAL FINANCEIRO DA LISTA DE COMPRAS"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(130, 6, clean_txt("Subtotal Consumíveis Diretos (Bebidas, Carnes, Gelo, Carvão, Descartáveis):"), border=1)
    pdf.cell(60, 6, clean_txt(fmt_moeda(tot_consumables)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.cell(130, 6, clean_txt("Subtotal Receitas Fabricadas (Farofas, Vinagretes, Acompanhamentos):"), border=1)
    pdf.cell(60, 6, clean_txt(fmt_moeda(tot_recipes)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(130, 7, clean_txt("VALOR TOTAL GERAL DA COMPRA:"), border=1, fill=True)
    pdf.cell(60, 7, clean_txt(fmt_moeda(grand_total)), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())

