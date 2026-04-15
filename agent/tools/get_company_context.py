import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "entreprises.json"

def get_company_context(company_id: str) -> dict :
    with open(DATA_PATH, encoding="utf-8")as f:
        companies = json.load(f)

    for company in companies:
        if company["company_id"] == company_id:
            return company

    raise ValueError(f"Entreprise non trouvée : {company_id}")
        