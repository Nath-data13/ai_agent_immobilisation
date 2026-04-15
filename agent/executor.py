from agent.tools.update_operation_category import update_operation_category
from agent.tools.split_operation import split_operation
from agent.tools.alerte_collaborateur import alerte_collaborateur
from agent.tools.send_client_message import send_client_message

# ---------------------------------------------------------------------------
# EXECUTOR — Python pur, aucun LLM
# Lit la décision de l'agent d'analyse et exécute les tools correspondants.
# Séparation stricte entre décision (LLM) et exécution (code déterministe).
# ---------------------------------------------------------------------------

def executer_decision(decision: dict, company_id: str) -> tuple:
    """
    Exécute la décision de l'agent d'analyse.
    Retourne (resultat, tools_trace).
    """
    operation_id = decision["operation_id"]
    choix = decision["decision"]
    tools_trace = []

    if choix == "charge_confirmed":
        return {"status": "aucune_action", "operation_id": operation_id}, tools_trace

    elif choix == "reclassification":
        new_category_id = decision.get("new_category_id")
        resultat = update_operation_category(
            operation_id=operation_id,
            new_category_id=new_category_id
        )
        tools_trace.append({
            "tool_name": "update_operation_category",
            "tool_args": {"operation_id": operation_id, "new_category_id": new_category_id},
            "resultat": resultat
        })

    elif choix == "split_operation":
        montant_charge = decision.get("montant_charge")
        montant_immo = decision.get("montant_immo")
        new_category_id = decision.get("new_category_id")

        res_split = split_operation(
            company_id=company_id,
            operation_id=operation_id,
            montant_charge=montant_charge,
            montant_immo=montant_immo
        )
        tools_trace.append({
            "tool_name": "split_operation",
            "tool_args": {"company_id": company_id, "operation_id": operation_id, "montant_charge": montant_charge, "montant_immo": montant_immo},
            "resultat": res_split
        })

        res_update = update_operation_category(
            operation_id=operation_id,
            new_category_id=new_category_id
        )
        tools_trace.append({
            "tool_name": "update_operation_category",
            "tool_args": {"operation_id": operation_id, "new_category_id": new_category_id},
            "resultat": res_update
        })

    elif choix == "human_review":
        raison = decision.get("raison_human_review", "Cas ambigu")
        resultat = alerte_collaborateur(
            company_id=company_id,
            operation_id=operation_id,
            human_review_reason=raison
        )
        tools_trace.append({
            "tool_name": "alerte_collaborateur",
            "tool_args": {"company_id": company_id, "operation_id": operation_id, "human_review_reason": raison},
            "resultat": resultat
        })

    elif choix == "request_client_info":
        message = decision.get("message_client", "Information manquante")
        resultat = send_client_message(
            company_id=company_id,
            operation_id=operation_id,
            message=message
        )
        tools_trace.append({
            "tool_name": "send_client_message",
            "tool_args": {"company_id": company_id, "operation_id": operation_id, "message": message},
            "resultat": resultat
        })

    return {"status": choix, "operation_id": operation_id}, tools_trace
