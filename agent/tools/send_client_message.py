import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "messages_sent.json"

def send_client_message(company_id: str, operation_id: str, message: str) -> dict:
    """Simule l'envoi d'un message au client via Intercom."""

    # 1. Créer l'enregistrement du message
    message_record = {
        "company_id": company_id,
        "operation_id": operation_id,
        "message": message
    }

    # 2. Charger la liste existante (ou créer une liste vide)
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = []

    # 3. Ajouter et sauvegarder
    historique.append(message_record)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    return {"status": "success", "operation_id": operation_id}
