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
    total_collected = sum(p.get("paid_amount", 0) for p in participants if p.get("paid"))
    
    pdf.cell(95, 6, clean_txt(f"Total Participantes: {total_parts} (Confirmados: {confirmed_parts})"))
    pdf.cell(95, 6, clean_txt(f"Total Arrecadado: {fmt_moeda(total_collected)}"), new_x="LMARGIN", new_y="NEXT")

    total_previsto = consumables_summary.get("grand_total", 0.0) + recipes_summary.get("recipes_grand_total", 0.0)
    cost_per_person = total_previsto / (confirmed_parts or 1)
    
    pdf.cell(95, 6, clean_txt(f"Orçamento Previsto (Itens + Receitas): {fmt_moeda(total_previsto)}"))
    pdf.cell(95, 6, clean_txt(f"Custo Estimado / Pessoa: {fmt_moeda(cost_per_person)}"), new_x="LMARGIN", new_y="NEXT")
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
    recipe_ingredients: List[Dict[str, Any]],
    suppliers_dict: Dict[str, str]
) -> bytes:
    """Gera a Lista de Compras Completa com Arredondamento Comercial."""
    pdf = ChurrascoPDF("Lista de Compras Consolidada", event_meta.get("name", "Evento"))
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 7, clean_txt("ITENS DIRETOS (BEBIDAS, CARNES, DESCARTÁVEIS, GELO)"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 6, clean_txt("Item"), border=1, fill=True)
    pdf.cell(35, 6, clean_txt("Embalagem/Formato"), border=1, fill=True)
    pdf.cell(30, 6, clean_txt("Qtd a Comprar"), border=1, fill=True, align="C")
    pdf.cell(40, 6, clean_txt("Fornecedor Recomendado"), border=1, fill=True)
    pdf.cell(25, 6, clean_txt("Estimativa"), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    for c in consumables:
        sup_name = suppliers_dict.get(c.get("supplier_id"), "Não informado")
        pack_info = c.get("package_unit_name") or f"Pacote {c.get('package_size')} {c.get('unit')}"
        pdf.cell(60, 5, clean_txt(c.get("name", "")[:35]), border=1)
        pdf.cell(35, 5, clean_txt(pack_info[:22]), border=1)
        pdf.cell(30, 5, clean_txt(f"{c.get('adjusted_quantity', 0)} {c.get('unit', '')}"), border=1, align="C")
        pdf.cell(40, 5, clean_txt(sup_name[:25]), border=1)
        pdf.cell(25, 5, clean_txt(fmt_moeda(float(c.get("total_cost", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    if recipe_ingredients:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 7, clean_txt("INGREDIENTES PARA RECEITAS (FAROFA, VINAGRETE, ETC.)"), new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(70, 6, clean_txt("Ingrediente"), border=1, fill=True)
        pdf.cell(40, 6, clean_txt("Receita Destino"), border=1, fill=True)
        pdf.cell(30, 6, clean_txt("Qtd Necessária"), border=1, fill=True, align="C")
        pdf.cell(25, 6, clean_txt("Preço Unit."), border=1, fill=True, align="R")
        pdf.cell(25, 6, clean_txt("Total"), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 8)
        for ing in recipe_ingredients:
            pdf.cell(70, 5, clean_txt(ing.get("name", "")[:42]), border=1)
            pdf.cell(40, 5, clean_txt(ing.get("source_recipe", "")[:24]), border=1)
            pdf.cell(30, 5, clean_txt(f"{ing.get('adjusted_quantity', 0)} {ing.get('unit', '')}"), border=1, align="C")
            pdf.cell(25, 5, clean_txt(fmt_moeda(float(ing.get("unit_price", 0)))), border=1, align="R")
            pdf.cell(25, 5, clean_txt(fmt_moeda(float(ing.get("total_cost", 0)))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())

