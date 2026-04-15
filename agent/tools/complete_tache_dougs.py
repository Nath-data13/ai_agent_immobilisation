import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "tache_completee.json"

def complete_tache_dougs(company_id: str, tache_id: str)-> dict :

    #création de la tache
    tache = {
        "company_id": company_id,
        "tache_id": tache_id,
        "status": "completee"
    }

    # charger la tache
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            historique_tache = json.load(f)
        
    else:
        historique_tache = [] 

    # ajouter la tache  
    historique_tache.append(tache)  

    # enregistrer la tache
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:   
        json.dump(historique_tache, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "company_id": company_id,
        "tache_id": tache_id
    }