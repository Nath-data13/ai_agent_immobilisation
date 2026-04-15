import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "categories.json"

def get_categories() -> list :

    if not (DATA_PATH).exists():
        raise FileNotFoundError(f"Fichier categories.json introuvable : {DATA_PATH}")
    
    with open(DATA_PATH, encoding="utf-8")as f:
        categories = json.load(f)
     
    return categories  