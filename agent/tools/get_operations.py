import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "operations_cpta.json"

def get_operations(company_id: str) -> list :
    with open(DATA_PATH, encoding="utf-8")as f:
        operations = json.load(f)

    results = []
    for operation in operations:
        if operation["company_id"] == company_id:
            results.append(operation)
    
    if not results:
        raise ValueError(f"Aucune operation trouvée pour : {company_id}")
    return results    