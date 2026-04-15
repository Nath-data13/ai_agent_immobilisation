import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
#  COMPUTE METRICS — Évalue les décisions de l'agent contre la bonne réponse
#
# Métriques calculées :
#   - recall_strict      : % d'immobilisations correctement détectées (sans escalade)
#   - recall_system      : % d'immobilisations capturées (incl. human_review comme filet)
#   - escalade_inutile   : % de cas faciles envoyés en human_review par erreur
#   - cas_instables      : opérations qui changent de décision entre runs
#
# Usage :
#   python eval/compute_metrics.py                          ← dernier output
#   python eval/compute_metrics.py eval/outputs/run_...json ← fichier précis
# ---------------------------------------------------------------------------

# Chemin vers les bonnes réponses attendues
CHEMIN_VERITE = Path(__file__).parent / "data" / "ground_truth.json"

# Décisions qui correspondent à une immobilisation
DECISIONS_IMMO = {"reclassification", "split_operation"}

def charger_ground_truth() -> dict:
    """Charge les bonnes réponses depuis ground_truth.json"""
    with open(CHEMIN_VERITE, encoding="utf-8") as f:
        liste = json.load(f)

    # On transforme la liste en dictionnaire indexé par operation_id
    verite = {}
    for element in liste:
        verite[element["operation_id"]] = element
    return verite

def compute_metrics(chemin_output: str):
    """Calcule les métriques d'un run et sauvegarde tout dans metrics_history.json"""

    # 1. Chargement du fichier de résultats de l'agent
    with open(chemin_output, encoding="utf-8") as f:
        data = json.load(f)

    metadonnees = data["metadata"]
    company_id = metadonnees.get("company_id")

    # Transformation des résultats en dictionnaire indexé par operation_id
    resultats_agent = {}
    for r in data["results"]:
        resultats_agent[r["operation_id"]] = r

    # 2. Chargement de la vérité terrain filtrée sur la company du run
    source_verite = charger_ground_truth()
    verite_filtree = {}
    for op_id, verite in source_verite.items():
        if verite["company_id"] == company_id:
            verite_filtree[op_id] = verite

    # 3. Construction de la liste de comparaisons (décision agent vs attendu)
    liste_decisions = []
    for op_id, verite in verite_filtree.items():
        decision_attendue = verite["decision_attendue"]
        difficulte = verite.get("difficulty", "inconnu")
        runs_agent = resultats_agent.get(op_id, {}).get("runs", [])
        if not runs_agent:
            runs_agent = [{"decision": "MANQUANTE", "confidence_score": None}]

        for run in runs_agent:
            liste_decisions.append({
                "operation_id":      op_id,
                "decision_agent":    run["decision"],
                "decision_attendue": decision_attendue,
                "confiance":         run.get("confidence_score"),
                "difficulte":        difficulte,
                "correct":           run["decision"] == decision_attendue
            })

    # 4. Recall strict
    # Parmi les immos où l'agent a décidé (sans escalader), combien sont correctes ?
    immos_decidees = []
    for d in liste_decisions:
        if d["decision_attendue"] in DECISIONS_IMMO and d["decision_agent"] != "human_review":
            immos_decidees.append(d)

    nb_immos_correctes = 0
    for d in immos_decidees:
        if d["correct"]:
            nb_immos_correctes += 1
    if immos_decidees:
        recall_strict = nb_immos_correctes / len(immos_decidees)
    else:
        recall_strict = 0

    # 5. Recall système
    # human_review = filet de sécurité : une immo escaladée est "capturée"
    toutes_immos = []
    for d in liste_decisions:
        if d["decision_attendue"] in DECISIONS_IMMO:
            toutes_immos.append(d)

    immos_capturees = []
    for d in toutes_immos:
        if d["decision_agent"] in DECISIONS_IMMO or d["decision_agent"] == "human_review":
            immos_capturees.append(d)

    if toutes_immos:
        recall_system = len(immos_capturees) / len(toutes_immos)
    else:
        recall_system = 0

    # 6. Taux d'escalade inutile
    # Sur les cas "faciles", combien sont envoyés en human_review par erreur 
    cas_faciles = []

    for d in liste_decisions:
        if d["difficulte"] == "facile":
            cas_faciles.append(d)

    escalades_inutiles = []
    for d in cas_faciles:
        if d["decision_agent"] == "human_review":
            escalades_inutiles.append(d)
    if cas_faciles:
        taux_escalade_inutile = len(escalades_inutiles) / len(cas_faciles)
    else:
        taux_escalade_inutile = 0    

    # 7. Détection des cas instables
    # Une opération est instable si l'agent donne des décisions différentes entre runs
    cas_instables = []
    for op_id in verite_filtree:
        decisions_sur_cet_op = []
        for d in liste_decisions:
            if d["operation_id"] == op_id:
                decisions_sur_cet_op.append(d["decision_agent"])
        if len(set(decisions_sur_cet_op)) > 1:  # plus d'une décision différente = instable
            cas_instables.append(op_id)

    # 8. Construction du résumé global
    total = len(verite_filtree)
    nb_corrects = 0
    for d in liste_decisions:
        if d["correct"]:
            nb_corrects += 1

    # 9. Sauvegarde complète dans metrics_history.json
    dossier_resultats = Path(__file__).parent / "results"
    dossier_resultats.mkdir(exist_ok=True)
    fichier = dossier_resultats / "metrics_history.json"

    nouvelle_entree = {
        # Infos du run
        "run_id":                metadonnees.get("run_id"),
        "company_id":            company_id,
        "model":                 metadonnees.get("model"),
        "prompt_version":        metadonnees.get("prompt_version"),
        # Métriques globales
        "score_global":          round(nb_corrects / total, 3) if total else 0,
        "recall_strict":         round(recall_strict, 3),
        "recall_system":         round(recall_system, 3),
        "escalade_inutile_rate": round(taux_escalade_inutile, 3),
        "nombre_instables":      len(cas_instables),
        "operations_instables":  cas_instables,
        # Détail opération par opération
        "resultats_par_operation": liste_decisions
    }
    # Chargement de l'historique existant (ou liste vide si premier run)
    if fichier.exists():
        with open(fichier, encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = []
    historique.append(nouvelle_entree)

    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    print(f"✅ Métriques sauvegardées → {fichier}")

    # 10. Retour des métriques pour les autres modules (monitoring.py, run_eval.py)
    # Note : les clés du return restent en anglais car attendues par ces modules

    return {
        "prompt_version":        metadonnees.get("prompt_version"),
        "model":                 metadonnees.get("model"),
        "recall_strict":         round(recall_strict, 3),
        "recall_system":         round(recall_system, 3),
        "escalade_inutile_rate": round(taux_escalade_inutile, 3),
        "unstable_cases":        cas_instables,
        "n_unstable":            len(cas_instables)
    }
if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Pas d'argument → on prend le dernier output disponible
        outputs = sorted(Path(__file__).parent.glob("outputs/*.json"))
        if not outputs:
            print("Aucun fichier output trouvé dans eval/outputs/")
            sys.exit(1)
        chemin = str(outputs[-1])
    else:
        chemin = sys.argv[1]
    compute_metrics(chemin)
