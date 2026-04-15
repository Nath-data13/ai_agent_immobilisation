from agent.tools.get_company_context import get_company_context
from agent.tools.get_operations import get_operations
from agent.tools.get_categories import get_categories
from agent.tools.get_accounting_rules import get_accounting_rules

# ---------------------------------------------------------------------------
# CONTEXT AGENT — Python pur, aucun LLM
# Récupère tout le contexte nécessaire avant l'analyse des opérations.
# Appelle les tools directement sans passer par un LLM.
# ---------------------------------------------------------------------------

def collecter_contexte(company_id: str) -> tuple:
    """
    Collecte le contexte complet de l'entreprise.
    Retourne (contexte, tools_trace) pour le logging.
    """
    entreprise = get_company_context(company_id)
    operations = get_operations(company_id)
    categories = get_categories()
    regles = get_accounting_rules(entreprise["type"])

    contexte = {
        "entreprise": entreprise,
        "operations": operations,
        "categories": categories,
        "regles": regles
    }

    # trace pour le logger — même format que les autres tools
    tools_trace = [
        {"tool_name": "get_company_context",  "tool_args": {"company_id": company_id},                       "resultat": entreprise},
        {"tool_name": "get_operations",        "tool_args": {"company_id": company_id},                       "resultat": operations},
        {"tool_name": "get_categories",        "tool_args": {},                                               "resultat": categories},
        {"tool_name": "get_accounting_rules",  "tool_args": {"company_type": entreprise["type"]},     "resultat": regles},
    ]

    return contexte, tools_trace
