import agent.checkpoint as checkpoint

# ---------------------------------------------------------------------------
# Tests du checkpoint — sans LLM, sans appel API
# Vérifie que la reprise sur crash fonctionne correctement
# ---------------------------------------------------------------------------

COMPANY = "test_company"
TACHE = "test_tache"


def teardown_function():
    """Nettoie le checkpoint après chaque test."""
    checkpoint.supprimer(COMPANY, TACHE)


def test_checkpoint_vide_au_depart():
    etat = checkpoint.charger(COMPANY, TACHE)
    assert etat == {}


def test_checkpoint_sauvegarde_et_recharge():
    etat = {}
    decision = {"operation_id": "op_1", "decision": "charge_confirmed", "confidence": 0.95}
    checkpoint.sauvegarder(COMPANY, TACHE, "op_1", decision, etat)

    etat_recharge = checkpoint.charger(COMPANY, TACHE)
    assert "op_1" in etat_recharge
    assert etat_recharge["op_1"]["decision"] == "charge_confirmed"


def test_checkpoint_supprime():
    etat = {}
    checkpoint.sauvegarder(COMPANY, TACHE, "op_1", {"decision": "charge_confirmed"}, etat)
    checkpoint.supprimer(COMPANY, TACHE)

    etat_apres = checkpoint.charger(COMPANY, TACHE)
    assert etat_apres == {}


def test_checkpoint_plusieurs_operations():
    etat = {}
    checkpoint.sauvegarder(COMPANY, TACHE, "op_1", {"decision": "charge_confirmed"}, etat)
    checkpoint.sauvegarder(COMPANY, TACHE, "op_2", {"decision": "reclassification"}, etat)

    etat_recharge = checkpoint.charger(COMPANY, TACHE)
    assert len(etat_recharge) == 2
    assert etat_recharge["op_2"]["decision"] == "reclassification"
