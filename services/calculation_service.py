import math
from typing import Any, Dict, List, Tuple


def is_beverage_item(category: str, name: str = "", unit: str = "") -> bool:
    """Verifica se o consumível pertence ao grupo de bebidas cadastradas."""
    cat = (category or "").strip().lower()
    nm = (name or "").strip().lower()
    u = (unit or "").strip().lower()
    if cat == "bebidas" or "bebid" in cat or "refrigerante" in cat or "suco" in cat or "cerveja" in cat or "chopp" in cat or "água" in cat or "agua" in cat:
        return True
    if any(k in nm for k in ["coca-cola", "coca", "guaraná", "guarana", "suco", "refrigerante", "cerveja", "chopp", "água", "agua mineral"]):
        return True
    if u in ["l", "ml"] and "carne" not in cat and "carne" not in nm and "gelo" not in cat and "carvão" not in cat and "carvao" not in cat:
        return True
    return False


def is_meat_item(category: str, name: str = "", unit: str = "") -> bool:
    """Verifica se o consumível pertence ao grupo de carnes cadastradas."""
    cat = (category or "").strip().lower()
    nm = (name or "").strip().lower()
    if cat == "carnes" or "carne" in cat or "churrasco" in cat:
        return True
    if any(k in nm for k in [
        "alcatra", "picanha", "maminha", "contrafilé", "contra file", "costela", "fraldinha", 
        "cupim", "linguiça", "linguica", "frango", "asa", "coxinha da asa", "tulipa", "peito de frango", 
        "bovino", "suíno", "suino", "pernil", "coração", "coracao"
    ]):
        return True
    return False


def calculate_consumables_totals(
    consumables: List[Dict[str, Any]],
    participant_count: int
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Calcula as quantidades necessárias, arredondamento para embalagens comerciais
    (ex: garrafas de 2L, 3L, pacotes de 100un, etc.), custos totais e
    estatísticas per capita consolidadas (Litros de bebidas/pessoa e Kg/g de carne/pessoa).
    """
    calculated_items = []
    category_totals: Dict[str, float] = {}
    grand_total = 0.0

    # Controles para Bebidas
    total_drinks_base_l = 0.0
    total_drinks_adj_l = 0.0
    drink_items_count = 0
    drinks_breakdown = []

    # Controles para Carnes
    total_meat_base_kg = 0.0
    total_meat_adj_kg = 0.0
    meat_items_count = 0
    meat_breakdown = []

    for item in consumables:
        calc = dict(item)
        per_person = float(calc.get("per_person", 0) or 0)
        fixed_qty = float(calc.get("fixed_quantity", 0) or 0)
        unit = str(calc.get("unit", "un")).strip()
        unit_lower = unit.lower()
        package_size = float(calc.get("package_size", 0) or 0)
        unit_price = float(calc.get("unit_price", 0) or 0)
        price_is_per_package = bool(calc.get("price_is_per_package", False))
        category = calc.get("category", "Outros")
        name = calc.get("name", "")

        # 1. Quantidade base teórica necessária
        if per_person > 0:
            base_needed = per_person * participant_count
        else:
            base_needed = fixed_qty

        # 2. Ajuste / Arredondamento para embalagens comerciais
        if package_size > 0:
            packages_needed = math.ceil(base_needed / package_size)
            adjusted_quantity = packages_needed * package_size
        else:
            packages_needed = math.ceil(base_needed) if unit_lower in ["un", "pct", "lata", "garrafa"] else base_needed
            adjusted_quantity = packages_needed

        # 3. Cálculo financeiro
        if price_is_per_package and package_size > 0:
            total_cost = packages_needed * unit_price
        else:
            total_cost = adjusted_quantity * unit_price

        calc["base_needed"] = round(base_needed, 3)
        calc["packages_needed"] = packages_needed
        calc["adjusted_quantity"] = round(adjusted_quantity, 3)
        calc["total_cost"] = round(total_cost, 2)

        calculated_items.append(calc)

        # Agrupamento financeiro por categoria
        category_totals[category] = round(category_totals.get(category, 0.0) + total_cost, 2)
        grand_total += total_cost

        # 4. Agrupamento e Conversão de Bebidas (Litros)
        if is_beverage_item(category, name, unit):
            drink_items_count += 1
            # Fator de conversão para Litros
            if unit_lower == "ml":
                conv_l = 0.001
            elif unit_lower in ["l", "litro", "litros"]:
                conv_l = 1.0
            else:
                conv_l = 1.0  # Unidade base ou lata

            item_base_l = base_needed * conv_l
            item_adj_l = adjusted_quantity * conv_l
            total_drinks_base_l += item_base_l
            total_drinks_adj_l += item_adj_l

            drinks_breakdown.append({
                "name": name,
                "per_person_l": round(item_base_l / participant_count, 3) if participant_count > 0 else 0.0,
                "per_person_ml": round((item_base_l / participant_count) * 1000, 1) if participant_count > 0 else 0.0,
                "total_needed_l": round(item_base_l, 2),
                "total_adjusted_l": round(item_adj_l, 2),
                "unit": unit
            })

        # 5. Agrupamento e Conversão de Carnes (Kg e Gramas)
        if is_meat_item(category, name, unit):
            meat_items_count += 1
            # Fator de conversão para Kg
            if unit_lower in ["g", "grama", "gramas"]:
                conv_kg = 0.001
            elif unit_lower in ["kg", "kilo", "quilo", "quilos"]:
                conv_kg = 1.0
            else:
                conv_kg = 1.0

            item_base_kg = base_needed * conv_kg
            item_adj_kg = adjusted_quantity * conv_kg
            total_meat_base_kg += item_base_kg
            total_meat_adj_kg += item_adj_kg

            meat_breakdown.append({
                "name": name,
                "per_person_kg": round(item_base_kg / participant_count, 3) if participant_count > 0 else 0.0,
                "per_person_g": round((item_base_kg / participant_count) * 1000, 1) if participant_count > 0 else 0.0,
                "total_needed_kg": round(item_base_kg, 2),
                "total_adjusted_kg": round(item_adj_kg, 2),
                "unit": unit
            })

    # Médias Per Capita de Bebidas
    drinks_l_per_person = round(total_drinks_base_l / participant_count, 3) if participant_count > 0 else 0.0
    drinks_ml_per_person = round(drinks_l_per_person * 1000, 1)
    drinks_adj_l_per_person = round(total_drinks_adj_l / participant_count, 3) if participant_count > 0 else 0.0

    # Médias Per Capita de Carnes
    meat_kg_per_person = round(total_meat_base_kg / participant_count, 3) if participant_count > 0 else 0.0
    meat_grams_per_person = round(meat_kg_per_person * 1000, 1)
    meat_adj_kg_per_person = round(total_meat_adj_kg / participant_count, 3) if participant_count > 0 else 0.0
    meat_adj_grams_per_person = round(meat_adj_kg_per_person * 1000, 1)

    summary = {
        "grand_total": round(grand_total, 2),
        "cost_per_person": round(grand_total / participant_count, 2) if participant_count > 0 else 0.0,
        "category_totals": category_totals,
        
        # Estatísticas de Bebidas
        "total_drinks_liters": round(total_drinks_base_l, 2),
        "total_drinks_liters_adjusted": round(total_drinks_adj_l, 2),
        "drinks_liters_per_person": drinks_l_per_person,
        "drinks_ml_per_person": drinks_ml_per_person,
        "drinks_adjusted_liters_per_person": drinks_adj_l_per_person,
        "drink_items_count": drink_items_count,
        "drinks_breakdown": drinks_breakdown,

        # Estatísticas de Carnes
        "total_meat_kg": round(total_meat_base_kg, 2),
        "total_meat_kg_adjusted": round(total_meat_adj_kg, 2),
        "meat_kg_per_person": meat_kg_per_person,
        "meat_grams_per_person": meat_grams_per_person,
        "meat_adjusted_kg_per_person": meat_adj_kg_per_person,
        "meat_adjusted_grams_per_person": meat_adj_grams_per_person,
        "meat_items_count": meat_items_count,
        "meat_breakdown": meat_breakdown
    }

    return calculated_items, summary


def calculate_recipes_totals(
    recipes: List[Dict[str, Any]],
    participant_count: int
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Calcula os ingredientes e custos de itens fabricados (ex: Vinagrete, Farofa, Torta),
    escalando proporcionalmente para o número de participantes do evento.
    """
    calculated_recipes = []
    recipes_grand_total = 0.0
    all_recipe_ingredients: List[Dict[str, Any]] = []

    for r in recipes:
        calc_r = dict(r)
        standard_yield = float(calc_r.get("standard_yield", 1) or 1)
        portion_per_person = float(calc_r.get("portion_per_person", 0) or 0)
        
        if portion_per_person > 0 and participant_count > 0:
            total_yield_needed = portion_per_person * participant_count
            scale_factor = total_yield_needed / standard_yield
        else:
            scale_factor = float(calc_r.get("batch_multiplier", 1) or 1)
            total_yield_needed = standard_yield * scale_factor

        calc_r["total_yield_needed"] = round(total_yield_needed, 2)
        calc_r["scale_factor"] = round(scale_factor, 3)

        recipe_cost = 0.0
        calculated_ingredients = []

        for ing in calc_r.get("ingredients", []):
            calc_ing = dict(ing)
            qty_standard = float(calc_ing.get("quantity", 0) or 0)
            needed_qty = qty_standard * scale_factor
            package_size = float(calc_ing.get("package_size", 0) or 0)
            unit_price = float(calc_ing.get("unit_price", 0) or 0)
            unit = calc_ing.get("unit", "kg")

            if package_size > 0:
                packs = math.ceil(needed_qty / package_size)
                adjusted_qty = packs * package_size
            else:
                packs = math.ceil(needed_qty) if unit in ["un", "pct", "lata", "garrafa", "maço"] else needed_qty
                adjusted_qty = packs

            ing_cost = adjusted_qty * unit_price
            calc_ing["needed_qty"] = round(needed_qty, 3)
            calc_ing["adjusted_qty"] = round(adjusted_qty, 3)
            calc_ing["packs"] = packs if package_size > 0 else 0
            calc_ing["cost"] = round(ing_cost, 2)

            recipe_cost += ing_cost
            calculated_ingredients.append(calc_ing)

            # Para consolidar na lista de compras geral
            all_recipe_ingredients.append({
                "source_recipe": calc_r.get("name"),
                "assigned_to": calc_r.get("assigned_to", ""),
                "name": f"{calc_ing.get('name')} (p/ {calc_r.get('name')})",
                "category": f"Ingredientes: {calc_r.get('name')}",
                "unit": unit,
                "adjusted_quantity": calc_ing["adjusted_qty"],
                "unit_price": unit_price,
                "total_cost": round(ing_cost, 2),
                "supplier_id": calc_ing.get("supplier_id")
            })

        calc_r["ingredients"] = calculated_ingredients
        calc_r["total_cost"] = round(recipe_cost, 2)
        recipes_grand_total += recipe_cost
        calculated_recipes.append(calc_r)

    summary = {
        "recipes_grand_total": round(recipes_grand_total, 2),
        "all_recipe_ingredients": all_recipe_ingredients
    }

    return calculated_recipes, summary

