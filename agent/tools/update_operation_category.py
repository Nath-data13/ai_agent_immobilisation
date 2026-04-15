import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "operations_cpta.json"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "operation_update.json"

def update_operation_category(operation_id: str, new_category_id: int) -> dict:
    """Met à jour la catégorie d'une opération comptable."""

    
    with open(DATA_PATH, encoding="utf-8")as f:
        op_category = json.load(f)

    found = False  # on part du principe que l'opération n'existe pas
    for operation in op_category:
        if operation["operation_id"] == operation_id: #si on trouve l'op_id
            operation["category_id"] = new_category_id # on modifie
            found = True # on a trouvé l'op_id

    #si pas de operation_id
    if not found:
        raise ValueError(f"Aucune categorie trouvée pour : {operation_id}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(op_category, f, ensure_ascii=False, indent=2)

          
    return {
        "status": "success",
        "operation_id": operation_id,
        "new_category_id": new_category_id
}          