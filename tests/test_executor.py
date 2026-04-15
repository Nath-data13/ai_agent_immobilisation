from agent.executor import executer_decision

# ---------------------------------------------------------------------------
# Tests de l'executor — sans LLM, sans appel API
# Vérifie que chaque décision appelle le bon tool et retourne le bon statut
# ---------------------------------------------------------------------------


def test_charge_confirmed_aucune_action():
    decision = {"operation_id": "op_test", "decision": "charge_confirmed"}
    resultat, trace = executer_decision(decision, "company_1")
    assert resultat["status"] == "aucune_action"
    assert trace == []  # aucun tool appelé


def test_reclassification_appelle_update():
    decision = {"operation_id": "op_893", "decision": "reclassification", "new_category_id": 11}
    resultat, trace = executer_decision(decision, "company_1")
    assert resultat["status"] == "reclassification"
    assert any(t["tool_name"] == "update_operation_category" for t in trace)


def test_human_review_appelle_alerte():
    decision = {"operation_id": "op_893", "decision": "human_review", "raison_human_review": "cas ambigu"}
    resultat, trace = executer_decision(decision, "company_1")
    assert resultat["status"] == "human_review"
    assert any(t["tool_name"] == "alerte_collaborateur" for t in trace)


def test_request_client_info_appelle_message():
    decision = {"operation_id": "op_893", "decision": "request_client_info", "message_client": "Merci de préciser"}
    resultat, trace = executer_decision(decision, "company_1")
    assert resultat["status"] == "request_client_info"
    assert any(t["tool_name"] == "send_client_message" for t in trace)


def test_split_operation_appelle_split_et_update():
    decision = {
        "operation_id": "op_891",
        "decision": "split_operation",
        "montant_charge": 300.0,
        "montant_immo": 500.0,
        "new_category_id": 11
    }
    resultat, trace = executer_decision(decision, "company_1")
    assert resultat["status"] == "split_operation"
    tool_names = [t["tool_name"] for t in trace]
    assert "split_operation" in tool_names
    assert "update_operation_category" in tool_names
