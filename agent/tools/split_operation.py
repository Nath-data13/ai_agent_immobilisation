import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "split_file.json"

def split_operation(operation_id: str, company_id: str, montant_charge: float, montant_immo: float) -> dict:
    """Ventile une facture mixte en deux parties : montant en charge et montant en immobilisation."""


    #création du slipt
    split_operation = {
        "company_id": company_id,
        "operation_id": operation_id,
        "montant_charge": montant_charge,
        "montant_immo": montant_immo,
        "status": "completee"
    }

    # charger le split
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            historique_split = json.load(f)
        
    else:
        historique_split = [] 

    # ajouter la tache  
    historique_split.append(split_operation)  

    # enregistrer la tache
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:   
        json.dump(historique_split, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "company_id": company_id,
        "operation_id": operation_id,
        "montant_charge": montant_charge,
        "montant_immo": montant_immo
    }