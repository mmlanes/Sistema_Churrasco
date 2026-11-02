import math
from typing import Any, Dict, List, Tuple


def calculate_consumables_totals(
    consumables: List[Dict[str, Any]],
    participant_count: int
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Calcula as quantidades necessárias, arredondamento para embalagens comerciais
    (ex: garrafas de 2L, 3L, pacotes de 100un, etc.) e custos totais.
    """
    calculated_items = []
    category_totals: Dict[str, float] = {}
    grand_total = 0.0

    for item in consumables:
        calc = dict(item)
        per_person = float(calc.get("per_person", 0) or 0)
        fixed_qty = float(calc.get("fixed_quantity", 0) or 0)
        unit = calc.get("unit", "un")
        package_size = float(calc.get("package_size", 0) or 0)
        unit_price = float(calc.get("unit_price", 0) or 0)
        price_is_per_package = bool(calc.get("price_is_per_package", False))
        category = calc.get("category", "Outros")

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
            # Se não tiver tamanho de pacote fixo, arredonda para 2 casas ou inteiro se for unidade
            packages_needed = math.ceil(base_needed) if unit in ["un", "pct", "lata", "garrafa"] else base_needed
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

        # Agrupamento por categoria
        category_totals[category] = round(category_totals.get(category, 0.0) + total_cost, 2)
        grand_total += total_cost

    summary = {
        "grand_total": round(grand_total, 2),
        "cost_per_person": round(grand_total / participant_count, 2) if participant_count > 0 else 0.0,
        "category_totals": category_totals
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

