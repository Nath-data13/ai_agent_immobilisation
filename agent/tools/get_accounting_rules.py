from pathlib import Path

RAG_PATH = Path(__file__).parent.parent.parent / "RAG" 

def get_accounting_rules(company_type: str) -> str :
    #construction du fichier dynamique
    filename = f"regles_{company_type.lower()}.md"

    #si pas le type dans les RAG exp=sci
    if not (RAG_PATH / filename).exists():
        raise ValueError(f"Aucune règle trouvée pour le type : {company_type}")
    
    #lit les regles_generales à tt type de company
    with open(RAG_PATH/"regles_generales.md", encoding="utf-8")as f:
        generales = f.read() 

    #lit la regle spécifique au type
    with open(RAG_PATH/filename, encoding="utf-8")as f:
        spécifiques = f.read() 

    #retourne les 2 collées
    return generales+ "\n\n" + spécifiques


   