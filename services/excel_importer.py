import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from config import DEFAULT_EXCEL_FILE
from services.event_service import create_event, get_event, save_event_data


def bootstrap_demo_event_if_needed() -> str:
    """
    Verifica se já existe o evento do churrasco histórico 3º ELE 2025.
    Se não existir, importa automaticamente a partir do arquivo Excel fornecido.
    """
    event_id = "churrasco_3_ele_2025"
    if get_event(event_id):
        return event_id

    # Cria o evento base
    meta = create_event(
        name="Churrasco 3º ELE 2025",
        description="Evento demonstrativo importado da planilha histórica 'Gastos com churrasco - 3º ELE 2025.xlsx'",
        date="2025-12-18",
        created_by="Administrador Master"
    )
    event_id = meta["id"]

    # 1. Participantes
    participants = []
    # 24 alunos pagantes
    for i in range(1, 25):
        participants.append({
            "id": f"p_aluno_{i:02d}",
            "name": f"Aluno ELE {i:02d}",
            "category": "Aluno",
            "confirmed": True,
            "fee": 25.0,
            "paid": True,
            "payment_method": "PIX",
            "paid_amount": 25.0,
            "notes": "Pago via comissão de formatura"
        })
    # 3 alunos não confirmados/isentos
    for i in range(25, 28):
        participants.append({
            "id": f"p_aluno_{i:02d}",
            "name": f"Aluno ELE {i:02d}",
            "category": "Aluno",
            "confirmed": False,
            "fee": 25.0,
            "paid": False,
            "payment_method": "Pendente",
            "paid_amount": 0.0,
            "notes": "Não pôde comparecer"
        })
    # 8 Servidores / Professores
    servidores_data = [
        ("Matusalém", True, "Organizador e Churrasqueiro"),
        ("Douglas", True, "Comissão organizadora"),
        ("Venzel", True, "Comissão organizadora"),
        ("Laércio", True, "Apoio e bebidas"),
        ("Isaac", True, "Comissão"),
        ("Salgueiro", False, "Convidado de honra"),
        ("Marcelle", True, "Responsável Pão de Alho"),
        ("Júlia Marinho", True, "Responsável Picolés"),
    ]
    for name, pago, note in servidores_data:
        participants.append({
            "id": f"p_{name.lower().replace(' ', '_')}",
            "name": name,
            "category": "Servidor/Professor",
            "confirmed": True,
            "fee": 25.0,
            "paid": pago,
            "payment_method": "PIX" if pago else "Pendente",
            "paid_amount": 25.0 if pago else 0.0,
            "notes": note
        })
    # Manuela (Colaboradora de culinária)
    participants.append({
        "id": "p_manuela",
        "name": "Manuela",
        "category": "Colaboradora",
        "confirmed": True,
        "fee": 25.0,
        "paid": True,
        "payment_method": "Abatimento em Compras",
        "paid_amount": 25.0,
        "notes": "Valor abatido do reembolso da farofa/vinagrete"
    })
    save_event_data(event_id, "participants", participants, "Sistema", "Carga inicial de participantes")

    # 2. Colaboradores
    collaborators = [
        {"id": "c_matu", "name": "Matusalém", "role": "Mestre Churrasqueiro & Compras", "phone": "(11) 98765-4321", "email": "matu@escola.br"},
        {"id": "c_manu", "name": "Manuela", "role": "Chef de Acompanhamentos (Farofa e Vinagrete)", "phone": "(11) 98888-1111", "email": "manuela@escola.br"},
        {"id": "c_marcelle", "name": "Marcelle", "role": "Compras de Pão de Alho", "phone": "(11) 97777-2222", "email": "marcelle@escola.br"},
        {"id": "c_julia", "name": "Júlia Marinho", "role": "Compras de Picolés e Sobremesas", "phone": "(11) 96666-3333", "email": "julia@escola.br"},
        {"id": "c_douglas", "name": "Douglas", "role": "Apoio e Logística de Descartáveis", "phone": "(11) 95555-4444", "email": "douglas@escola.br"},
        {"id": "c_venzel", "name": "Venzel", "role": "Recepção e Caixa", "phone": "(11) 94444-5555", "email": "venzel@escola.br"},
        {"id": "c_laercio", "name": "Laércio", "role": "Logística de Bebidas e Gelo", "phone": "(11) 93333-6666", "email": "laercio@escola.br"},
    ]
    save_event_data(event_id, "collaborators", collaborators, "Sistema", "Carga inicial de colaboradores")

    # 3. Fornecedores
    suppliers = [
        {
            "id": "sup_atacadao",
            "name": "Atacadão / Supermercado Central",
            "category": "Bebidas e Mercearia",
            "contact": "Atendimento Comercial",
            "phone": "(11) 4004-0000",
            "address": "Av. Principal, 1000",
            "notes": "Melhor preço para Coca-cola, sucos e arroz"
        },
        {
            "id": "sup_acougue",
            "name": "Açougue Boi de Ouro",
            "category": "Carnes Nobres",
            "contact": "Seu Jorge",
            "phone": "(11) 4123-9988",
            "address": "Rua do Mercado, 45",
            "notes": "Alcatra e linguiças frescas fatiadas no capricho"
        },
        {
            "id": "sup_hortifruti",
            "name": "Hortifruti da Estação",
            "category": "Hortifruti & Temperos",
            "contact": "Dona Maria",
            "phone": "(11) 4222-3344",
            "address": "Rua das Feiras, 12",
            "notes": "Tomates maduros, cebolas e cheiro verde frescos"
        },
        {
            "id": "sup_sorvete",
            "name": "Fábrica e Distribuidora de Picolés Gelabem",
            "category": "Sobremesas / Gelo",
            "contact": "Carlos",
            "phone": "(11) 4333-8877",
            "address": "Rua Industrial, 30",
            "notes": "Picolés no atacado a R$ 1,50 cada"
        },
        {
            "id": "sup_descartaveis",
            "name": "Embalagens & Festas Express",
            "category": "Descartáveis",
            "contact": "Renata",
            "phone": "(11) 4555-6677",
            "address": "Av. dos Estados, 500",
            "notes": "Pratos 21cm, copos 300ml e garfos reforçados"
        }
    ]
    save_event_data(event_id, "suppliers", suppliers, "Sistema", "Carga inicial de fornecedores")

    # 4. Consumíveis (Carnes, Bebidas, Descartáveis, Gelo, Acompanhamentos)
    consumables = [
        # Bebidas
        {
            "id": "c_coca_3l",
            "name": "Coca-cola 3L",
            "category": "Bebidas",
            "unit": "L",
            "per_person": 0.1,
            "fixed_quantity": 0,
            "package_size": 3.0,
            "package_unit_name": "Garrafa de 3 Litros",
            "unit_price": 5.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Laércio",
            "notes": "Preço R$ 5,00 por litro (R$ 15 por garrafa de 3L)"
        },
        {
            "id": "c_coca_zero_2l",
            "name": "Coca-cola Zero 2L",
            "category": "Bebidas",
            "unit": "L",
            "per_person": 0.1,
            "fixed_quantity": 0,
            "package_size": 2.0,
            "package_unit_name": "Garrafa de 2 Litros",
            "unit_price": 5.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Laércio",
            "notes": "Preço R$ 5,00 por litro (R$ 10 por garrafa de 2L)"
        },
        {
            "id": "c_guarana_2l",
            "name": "Guaraná 2L",
            "category": "Bebidas",
            "unit": "L",
            "per_person": 0.1,
            "fixed_quantity": 0,
            "package_size": 2.0,
            "package_unit_name": "Garrafa de 2 Litros",
            "unit_price": 4.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Laércio",
            "notes": "Preço R$ 4,00 por litro (R$ 8 por garrafa de 2L)"
        },
        {
            "id": "c_suco_uva_1l",
            "name": "Suco de Uva 1L",
            "category": "Bebidas",
            "unit": "L",
            "per_person": 0.1,
            "fixed_quantity": 0,
            "package_size": 1.0,
            "package_unit_name": "Garrafa de 1 Litro",
            "unit_price": 8.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Laércio",
            "notes": "Suco integral"
        },
        {
            "id": "c_suco_caju_1l",
            "name": "Suco de Caju 1L",
            "category": "Bebidas",
            "unit": "L",
            "per_person": 0.1,
            "fixed_quantity": 0,
            "package_size": 1.0,
            "package_unit_name": "Garrafa de 1 Litro",
            "unit_price": 7.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Laércio",
            "notes": "Suco concentrado/pronto para beber"
        },
        {
            "id": "c_agua_gas_15l",
            "name": "Água com Gás 1,5L",
            "category": "Bebidas",
            "unit": "L",
            "per_person": 0.05,
            "fixed_quantity": 0,
            "package_size": 1.5,
            "package_unit_name": "Garrafa de 1,5 Litro",
            "unit_price": 3.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Laércio",
            "notes": "Preço R$ 3,00 por litro"
        },
        # Gelo
        {
            "id": "c_gelo",
            "name": "Gelo em Cubos (Kg)",
            "category": "Gelo / Carvão",
            "unit": "kg",
            "per_person": 0,
            "fixed_quantity": 15.0,
            "package_size": 5.0,
            "package_unit_name": "Saco de 5 Kg",
            "unit_price": 2.0,
            "price_is_per_package": False,
            "supplier_id": "sup_sorvete",
            "assigned_collaborator": "Laércio",
            "notes": "3 sacos de 5kg para caixas térmicas"
        },
        # Carnes
        {
            "id": "c_alcatra",
            "name": "Carne Bovina / Alcatra (Kg)",
            "category": "Carnes",
            "unit": "kg",
            "per_person": 0.25,
            "fixed_quantity": 2.0,
            "package_size": 1.0,
            "package_unit_name": "Kg",
            "unit_price": 40.0,
            "price_is_per_package": False,
            "supplier_id": "sup_acougue",
            "assigned_collaborator": "Matusalém",
            "notes": "Corte macio para grelha"
        },
        {
            "id": "c_linguica_toscana",
            "name": "Linguiça Toscana (Kg)",
            "category": "Carnes",
            "unit": "kg",
            "per_person": 0,
            "fixed_quantity": 2.0,
            "package_size": 1.0,
            "package_unit_name": "Kg",
            "unit_price": 20.0,
            "price_is_per_package": False,
            "supplier_id": "sup_acougue",
            "assigned_collaborator": "Matusalém",
            "notes": "Linguiça de pernil"
        },
        {
            "id": "c_linguica_defumada",
            "name": "Linguiça Defumada (Kg)",
            "category": "Carnes",
            "unit": "kg",
            "per_person": 0,
            "fixed_quantity": 1.0,
            "package_size": 1.0,
            "package_unit_name": "Kg",
            "unit_price": 25.0,
            "price_is_per_package": False,
            "supplier_id": "sup_acougue",
            "assigned_collaborator": "Matusalém",
            "notes": "Linguiça fininha defumada"
        },
        {
            "id": "c_pedacos_frango",
            "name": "Pedaços de Frango / Coxinha da Asa (Kg)",
            "category": "Carnes",
            "unit": "kg",
            "per_person": 0,
            "fixed_quantity": 1.0,
            "package_size": 1.0,
            "package_unit_name": "Kg",
            "unit_price": 20.0,
            "price_is_per_package": False,
            "supplier_id": "sup_acougue",
            "assigned_collaborator": "Matusalém",
            "notes": "Temperado"
        },
        {
            "id": "c_peito_frango",
            "name": "Peito de Frango (Kg)",
            "category": "Carnes",
            "unit": "kg",
            "per_person": 0,
            "fixed_quantity": 1.0,
            "package_size": 1.0,
            "package_unit_name": "Kg",
            "unit_price": 20.0,
            "price_is_per_package": False,
            "supplier_id": "sup_acougue",
            "assigned_collaborator": "Matusalém",
            "notes": "Filé para grelha"
        },
        # Arroz e Pão de Alho
        {
            "id": "c_arroz",
            "name": "Arroz Branco Tipo 1 (Kg)",
            "category": "Acompanhamentos",
            "unit": "kg",
            "per_person": 0.1,
            "fixed_quantity": 5.0,
            "package_size": 5.0,
            "package_unit_name": "Pacote de 5 Kg",
            "unit_price": 4.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Manuela",
            "notes": "Pacote de 5kg fechado"
        },
        {
            "id": "c_pao_alho",
            "name": "Pão de Alho Tradicional (un)",
            "category": "Acompanhamentos",
            "unit": "un",
            "per_person": 1.0,
            "fixed_quantity": 0,
            "package_size": 40.0,
            "package_unit_name": "Pacote com 40 unidades",
            "unit_price": 1.0,
            "price_is_per_package": False,
            "supplier_id": "sup_atacadao",
            "assigned_collaborator": "Marcelle",
            "notes": "Arredondado de 35 para embalagem fechada de 40 unidades"
        },
        # Descartáveis
        {
            "id": "c_prato_21cm",
            "name": "Prato Descartável 21cm",
            "category": "Descartáveis",
            "unit": "un",
            "per_person": 0,
            "fixed_quantity": 100.0,
            "package_size": 100.0,
            "package_unit_name": "Pacote com 100 un",
            "unit_price": 0.35,
            "price_is_per_package": False,
            "supplier_id": "sup_descartaveis",
            "assigned_collaborator": "Douglas",
            "notes": "Prato reforçado para churrasco"
        },
        {
            "id": "c_copo_300ml",
            "name": "Copo Descartável 300ml",
            "category": "Descartáveis",
            "unit": "un",
            "per_person": 0,
            "fixed_quantity": 100.0,
            "package_size": 100.0,
            "package_unit_name": "Pacote com 100 un",
            "unit_price": 0.35,
            "price_is_per_package": False,
            "supplier_id": "sup_descartaveis",
            "assigned_collaborator": "Douglas",
            "notes": "Copo resistente para refrigerante"
        },
        {
            "id": "c_garfo_100",
            "name": "Garfo Plástico Reforçado",
            "category": "Descartáveis",
            "unit": "un",
            "per_person": 0,
            "fixed_quantity": 100.0,
            "package_size": 100.0,
            "package_unit_name": "Pacote com 100 un",
            "unit_price": 0.20,
            "price_is_per_package": False,
            "supplier_id": "sup_descartaveis",
            "assigned_collaborator": "Douglas",
            "notes": "Garfo grande para refeição"
        },
        {
            "id": "c_papel_toalha",
            "name": "Papel Toalha (rolo)",
            "category": "Descartáveis",
            "unit": "rolo",
            "per_person": 0,
            "fixed_quantity": 1.0,
            "package_size": 1.0,
            "package_unit_name": "Rolo individual",
            "unit_price": 10.0,
            "price_is_per_package": True,
            "supplier_id": "sup_descartaveis",
            "assigned_collaborator": "Douglas",
            "notes": "Folha dupla"
        },
        {
            "id": "c_guardanapo",
            "name": "Guardanapo de Papel (pacote)",
            "category": "Descartáveis",
            "unit": "pct",
            "per_person": 0,
            "fixed_quantity": 2.0,
            "package_size": 1.0,
            "package_unit_name": "Pacote",
            "unit_price": 12.0,
            "price_is_per_package": True,
            "supplier_id": "sup_descartaveis",
            "assigned_collaborator": "Douglas",
            "notes": "2 pacotes grandes"
        },
        {
            "id": "c_papel_aluminio",
            "name": "Papel Alumínio (rolo)",
            "category": "Descartáveis",
            "unit": "rolo",
            "per_person": 0,
            "fixed_quantity": 1.0,
            "package_size": 1.0,
            "package_unit_name": "Rolo",
            "unit_price": 10.0,
            "price_is_per_package": True,
            "supplier_id": "sup_descartaveis",
            "assigned_collaborator": "Douglas",
            "notes": "Para envolver grelha e assados"
        },
        # Sobremesas
        {
            "id": "c_picole",
            "name": "Picolés Frutas e Cremosos",
            "category": "Sobremesas",
            "unit": "un",
            "per_person": 3.0,
            "fixed_quantity": 0,
            "package_size": 100.0,
            "package_unit_name": "Caixa com 100 picolés",
            "unit_price": 1.50,
            "price_is_per_package": False,
            "supplier_id": "sup_sorvete",
            "assigned_collaborator": "Júlia Marinho",
            "notes": "100 a 110 picolés sortidos"
        }
    ]
    save_event_data(event_id, "consumables", consumables, "Sistema", "Carga inicial de consumíveis")

    # 5. Receitas Fabricadas por Colaboradores (Vinagrete, Farofa, Torta)
    recipes = [
        {
            "id": "rec_vinagrete",
            "name": "Vinagrete Especial para Churrasco",
            "category": "Acompanhamentos",
            "assigned_to": "Manuela",
            "standard_yield": 3.0,
            "yield_unit": "kg",
            "portion_per_person": 0.085,
            "batch_multiplier": 1.0,
            "instructions": "Picar tomate, cebola e pimentão em cubos pequenos. Misturar o cheiro verde, temperar com sal, azeite e vinagre.",
            "ingredients": [
                {"name": "Tomate maduro", "quantity": 2.0, "unit": "kg", "unit_price": 7.0, "package_size": 1.0, "supplier_id": "sup_hortifruti"},
                {"name": "Cebola branca", "quantity": 0.5, "unit": "kg", "unit_price": 6.0, "package_size": 0.5, "supplier_id": "sup_hortifruti"},
                {"name": "Pimentão verde", "quantity": 0.3, "unit": "kg", "unit_price": 8.0, "package_size": 0.3, "supplier_id": "sup_hortifruti"},
                {"name": "Salsinha fresca", "quantity": 2.0, "unit": "maço", "unit_price": 2.0, "package_size": 1.0, "supplier_id": "sup_hortifruti"},
                {"name": "Cebolinha fresca", "quantity": 2.0, "unit": "maço", "unit_price": 2.0, "package_size": 1.0, "supplier_id": "sup_hortifruti"},
                {"name": "Vinagre de álcool/maçã", "quantity": 0.5, "unit": "L", "unit_price": 6.0, "package_size": 0.5, "supplier_id": "sup_atacadao"}
            ]
        },
        {
            "id": "rec_farofa",
            "name": "Farofa Rica com Bacon e Calabresa",
            "category": "Acompanhamentos",
            "assigned_to": "Manuela",
            "standard_yield": 3.0,
            "yield_unit": "kg",
            "portion_per_person": 0.085,
            "batch_multiplier": 1.0,
            "instructions": "Fritar o bacon e a linguiça calabresa picados com alho e cebola. Adicionar os ovos mexidos. Acrescentar a farofa pronta e misturar bem.",
            "ingredients": [
                {"name": "Farofa pronta temperada (400g)", "quantity": 2.0, "unit": "kg", "unit_price": 22.50, "package_size": 0.4, "supplier_id": "sup_atacadao"},
                {"name": "Cebola picada", "quantity": 0.5, "unit": "kg", "unit_price": 6.0, "package_size": 0.5, "supplier_id": "sup_hortifruti"},
                {"name": "Bacon em cubos", "quantity": 0.5, "unit": "kg", "unit_price": 40.0, "package_size": 0.5, "supplier_id": "sup_acougue"},
                {"name": "Linguiça calabresa defumada", "quantity": 0.5, "unit": "kg", "unit_price": 40.0, "package_size": 0.5, "supplier_id": "sup_acougue"},
                {"name": "Ovos caipiras/brancos", "quantity": 12.0, "unit": "un", "unit_price": 1.0, "package_size": 12.0, "supplier_id": "sup_atacadao"},
                {"name": "Alho picado", "quantity": 0.1, "unit": "kg", "unit_price": 20.0, "package_size": 0.1, "supplier_id": "sup_hortifruti"}
            ]
        },
        {
            "id": "rec_torta",
            "name": "Torta Doce de Maracujá",
            "category": "Sobremesas",
            "assigned_to": "Manuela",
            "standard_yield": 1.0,
            "yield_unit": "torta",
            "portion_per_person": 0,
            "batch_multiplier": 1.0,
            "instructions": "Bater leite condensado com creme de leite e suco concentrado de maracujá. Montar camadas com biscoito maisena e cobrir com raspas de chocolate.",
            "ingredients": [
                {"name": "Leite condensado (lata/caixa)", "quantity": 6.0, "unit": "un", "unit_price": 6.0, "package_size": 1.0, "supplier_id": "sup_atacadao"},
                {"name": "Creme de leite (caixa)", "quantity": 6.0, "unit": "un", "unit_price": 5.0, "package_size": 1.0, "supplier_id": "sup_atacadao"},
                {"name": "Suco concentrado de maracujá (200ml)", "quantity": 0.4, "unit": "L", "unit_price": 2.0, "package_size": 0.2, "supplier_id": "sup_atacadao"},
                {"name": "Biscoito maisena (175g)", "quantity": 6.0, "unit": "pct", "unit_price": 7.0, "package_size": 1.0, "supplier_id": "sup_atacadao"},
                {"name": "Chocolate meio amargo 100g", "quantity": 0.2, "unit": "un", "unit_price": 1.0, "package_size": 1.0, "supplier_id": "sup_atacadao"}
            ]
        }
    ]
    save_event_data(event_id, "recipes", recipes, "Sistema", "Carga inicial de receitas")

    # 6. Tarefas dos Colaboradores
    tasks = [
        {
            "id": "tsk_01",
            "title": "Preparar Farofa e Vinagrete",
            "description": "Comprar os ingredientes frescos, picar os legumes e preparar 3kg de Vinagrete e 3kg de Farofa com bacon e calabresa.",
            "assigned_to": "Manuela",
            "deadline": "2025-12-18",
            "status": "Realizada",
            "budget": 132.40,
            "actual_spent": 82.66,
            "notes": "Gastou R$ 82,66. Deduzidos R$ 25 da sua própria cota, gerando PIX de reembolso de R$ 57,66."
        },
        {
            "id": "tsk_02",
            "title": "Comprar Pão de Alho",
            "description": "Comprar pacote com 40 unidades de pão de alho na véspera e manter refrigerado.",
            "assigned_to": "Marcelle",
            "deadline": "2025-12-17",
            "status": "Realizada",
            "budget": 40.0,
            "actual_spent": 62.0,
            "notes": "Comprou marca especial de pão de alho recheado no valor de R$ 62,00. Reembolsada integralmente via PIX."
        },
        {
            "id": "tsk_03",
            "title": "Comprar 110 Picolés na Distribuidora",
            "description": "Buscar os picolés na fábrica/distribuidora em caixa de isopor com gelo antes do evento.",
            "assigned_to": "Júlia Marinho",
            "deadline": "2025-12-18",
            "status": "Realizada",
            "budget": 150.0,
            "actual_spent": 165.0,
            "notes": "Comprou 110 picolés por R$ 165,00. Reembolsada integralmente via PIX pelo caixa."
        },
        {
            "id": "tsk_04",
            "title": "Comprar Carnes e Assar Churrasco",
            "description": "Comprar as carnes no açougue (alcatra, linguiças, frango), temperar e comandar a churrasqueira.",
            "assigned_to": "Matusalém",
            "deadline": "2025-12-18",
            "status": "Realizada",
            "budget": 185.0,
            "actual_spent": 574.56,
            "notes": "Compras divididas em duas etapas (R$ 225,28 + R$ 349,28) suprindo quantidade extra com excelente qualidade."
        },
        {
            "id": "tsk_05",
            "title": "Comprar Bebidas e Gelo",
            "description": "Comprar refrigerantes Coca 3L, Guaraná, sucos e 15kg de gelo.",
            "assigned_to": "Matusalém",
            "deadline": "2025-12-18",
            "status": "Realizada",
            "budget": 183.0,
            "actual_spent": 124.0,
            "notes": "Gastou R$ 124,00 com bebidas em promoção."
        },
        {
            "id": "tsk_06",
            "title": "Providenciar Descartáveis e Limpeza",
            "description": "Buscar pratos, copos, garfos, papel toalha e sacos de lixo.",
            "assigned_to": "Douglas",
            "deadline": "2025-12-17",
            "status": "Realizada",
            "budget": 134.0,
            "actual_spent": 0.0,
            "notes": "Descartáveis foram aproveitados de estoque da escola sem custo adicional."
        },
        {
            "id": "tsk_07",
            "title": "Recepção e Fechamento de Caixa",
            "description": "Conferir comprovantes PIX dos alunos e servidores e liquidar os reembolsos dos colaboradores.",
            "assigned_to": "Venzel",
            "deadline": "2025-12-18",
            "status": "Realizada",
            "budget": 0.0,
            "actual_spent": 0.0,
            "notes": "Fechamento realizado com sobras de R$ 91,06 no saldo final."
        }
    ]
    save_event_data(event_id, "tasks", tasks, "Sistema", "Carga inicial de tarefas")

    # 7. Controle de Caixa (Entradas e Saídas / Reembolsos / Comprovantes)
    cashflow = [
        # Entradas
        {
            "id": "csh_in_alunos",
            "type": "ENTRADA",
            "category": "Contribuição Alunos",
            "description": "Pagamento de 24 alunos x R$ 25,00",
            "amount": 600.0,
            "payer_or_receiver": "Comissão de Alunos",
            "date": "2025-12-15",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "Recebido no caixa geral da turma"
        },
        {
            "id": "csh_in_profs",
            "type": "ENTRADA",
            "category": "Contribuição Servidores",
            "description": "Pagamento de 5 servidores/professores (Matusalém, Douglas, Laércio, Venzel, Isaac)",
            "amount": 125.0,
            "payer_or_receiver": "Servidores",
            "date": "2025-12-16",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "R$ 25,00 por professor"
        },
        # Saídas / Compras / PIX
        {
            "id": "csh_out_marcelle",
            "type": "SAIDA",
            "category": "Reembolso / Compras",
            "description": "PIX para Marcelle - Compra do Pão de Alho",
            "amount": 62.0,
            "payer_or_receiver": "Marcelle",
            "date": "2025-12-17",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "Comprovante conferido"
        },
        {
            "id": "csh_out_julia",
            "type": "SAIDA",
            "category": "Reembolso / Compras",
            "description": "PIX para Júlia Marinho - Compra de 110 Picolés",
            "amount": 165.0,
            "payer_or_receiver": "Júlia Marinho",
            "date": "2025-12-18",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "Comprovante conferido"
        },
        {
            "id": "csh_out_manuela",
            "type": "SAIDA",
            "category": "Reembolso / Compras",
            "description": "PIX para Manuela - Ingredientes Farofa e Vinagrete (R$ 82,66 - cota R$ 25,00)",
            "amount": 57.66,
            "payer_or_receiver": "Manuela",
            "date": "2025-12-18",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "Reembolso líquido após desconto de sua participação"
        },
        {
            "id": "csh_out_matu_carnes1",
            "type": "SAIDA",
            "category": "Carnes & Churrasco",
            "description": "Compra de carnes e insumos por Matusalém (Etapa 1)",
            "amount": 225.28,
            "payer_or_receiver": "Matusalém / Açougue",
            "date": "2025-12-18",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "Cupom fiscal arquivado"
        },
        {
            "id": "csh_out_matu_bebidas",
            "type": "SAIDA",
            "category": "Bebidas",
            "description": "Compra de refrigerantes e sucos por Matusalém",
            "amount": 124.0,
            "payer_or_receiver": "Matusalém / Atacadão",
            "date": "2025-12-18",
            "payment_method": "PIX",
            "attachment_name": "",
            "notes": "Comprovante arquivado"
        }
    ]
    save_event_data(event_id, "cashflow", cashflow, "Sistema", "Carga inicial de fluxo de caixa")

    # 8. Sugestões de exemplo
    suggestions = [
        {
            "id": "sug_01",
            "author": "Aluno Convidado",
            "user_role": "visualizador",
            "text": "Sugiro colocar uma opção de refrigerante guaraná zero no próximo churrasco!",
            "status": "Aceita",
            "created_at": "2025-12-18 14:30:00",
            "admin_response": "Ótima sugestão, incluiremos na cota de bebidas do próximo evento."
        },
        {
            "id": "sug_02",
            "author": "Douglas",
            "user_role": "colaborador",
            "text": "Podemos cotar carvão ecológico que faz menos fumaça.",
            "status": "Analisada",
            "created_at": "2025-12-18 16:00:00",
            "admin_response": "Vamos verificar o preço com os fornecedores."
        }
    ]
    save_event_data(event_id, "suggestions", suggestions, "Sistema", "Carga inicial de sugestões")

    return event_id

