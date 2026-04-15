import pytest
from agent.tools.get_company_context import get_company_context
from agent.tools.get_operations import get_operations
from agent.tools.get_categories import get_categories
from agent.tools.get_accounting_rules import get_accounting_rules

# ---------------------------------------------------------------------------
# Tests des tools de collecte — sans LLM, sans appel API
# ---------------------------------------------------------------------------


def test_get_company_context_company1():
    result = get_company_context("company_1")
    assert result["company_id"] == "company_1"
    assert result["type"] == "SARL"


def test_get_company_context_company2():
    result = get_company_context("company_2")
    assert result["company_id"] == "company_2"
    assert result["type"] == "LMNP"


def test_get_company_context_inconnu():
    with pytest.raises(ValueError):
        get_company_context("company_inconnue")


def test_get_operations_filtre_par_company():
    ops = get_operations("company_1")
    assert len(ops) > 0
    assert all(op["company_id"] == "company_1" for op in ops)


def test_get_operations_company1_et_company2_distinctes():
    ops1 = get_operations("company_1")
    ops2 = get_operations("company_2")
    ids1 = {op["operation_id"] for op in ops1}
    ids2 = {op["operation_id"] for op in ops2}
    assert ids1.isdisjoint(ids2)  # aucun op_id en commun


def test_get_categories_non_vide():
    cats = get_categories()
    assert len(cats) > 0
    assert all("id" in c for c in cats)


def test_get_accounting_rules_sarl():
    rules = get_accounting_rules("SARL")
    assert "500" in rules  # seuil SARL présent


def test_get_accounting_rules_lmnp():
    rules = get_accounting_rules("LMNP")
    assert "500" in rules  # seuil LMNP présent


def test_get_accounting_rules_type_inconnu():
    with pytest.raises(ValueError):
        get_accounting_rules("SCI_INCONNUE")
