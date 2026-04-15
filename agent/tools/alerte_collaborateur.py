import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "alerte.json"

def alerte_collaborateur(company_id: str, operation_id: str, human_review_reason: str) -> dict :

    # création de l'alerte
    alerte_collaborateur = {
        "company_id": company_id,
        "operation_id": operation_id,
        "alerte": human_review_reason
    }

    # je l'alerte
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            historique_alerte = json.load(f)
    else:
        historique_alerte = []

    # ajouter l'alerte_collaborateur
    historique_alerte.append(alerte_collaborateur) 

    # sauvegarder
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(historique_alerte, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "company_id": company_id,
        "operation_id": operation_id,
        "human_review_reason": human_review_reason 
    }
