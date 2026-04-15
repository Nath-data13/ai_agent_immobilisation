import json
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

# import fonction qui charge les bonnes réponses depuis compute_metrics.py
from compute_metrics import charger_ground_truth

# ---------------------------------------------------------------------------
# COMPARE RUNS — Compare N runs côte à côte et sauvegarde resultats
#
# Usage :
#   python eval/compare_runs.py                      ← tous les outputs dispo
#   python eval/compare_runs.py --last 5             ← les 5 derniers runs
#   python eval/compare_runs.py --company company_1  ← filtre par company
# ---------------------------------------------------------------------------


def comparer(fichiers: list, company_id: str = None):
    """ compare plusieurs runs et sauvegarde les résultats dans compare_history.json"""

    # 1 chargement de tous les runs
    liste_runs = []
    for fichier in fichiers:
        with open(fichier, encoding="utf-8") as f:
            data = json.load(f)

        metadonnees = data["metadata"]

        # si on filtre par company, on saute les autres company
        if company_id and metadonnees.get("company_id") != company_id:
            continue

        # on transforme les reusltats en dict indexé par operation_id
        decisions_agent = {}
        for r in data["results"]:
            if r["runs"]:
                decisions_agent[r["operation_id"]] = r["runs"][0]

        liste_runs.append({
            "metadonnees": metadonnees,
            "decisions_agent": decisions_agent,
            "nom_fichier": fichier.name
        })     
    if not liste_runs:
        print("Aucun run trouvé.")
        return       

    # 2 chargement de la verite terrain
    source_verite = charger_ground_truth()
    company_analysee = liste_runs[0]["metadonnees"].get("company_id")

    verite_filtree = {}
    for op_id, verite in source_verite.items():
        if verite["company_id"] == company_analysee:
            verite_filtree[op_id] = verite

    nombre_runs = len(liste_runs)   

    # 3 analyse des décisions par opération
    operations_instables = []
    decisions_par_operation = []

    for op_id, verite in verite_filtree.items():
        decision_attendue = verite["decision_attendue"]

        # On collecte la décision de chaque run pour cette opération
        liste_decisions = []
        for run in liste_runs:
            decision = run["decisions_agent"].get(op_id, {}).get("decision", "MANQUANTE")
            liste_decisions.append(decision)

        # L'opération est stable si tous les runs ont donné la même décision
        est_stable = len(set(liste_decisions)) == 1
        if not est_stable:
            operations_instables.append(op_id)

        # On compte manuellement combien de fois chaque décision apparaît
        comptage = {}
        for decision in liste_decisions:
            if decision not in comptage:
                comptage[decision] = 0
            comptage[decision] += 1

        # On trie du plus fréquent au moins fréquent
        frequences = []
        for decision, nb_fois in sorted(comptage.items(), key=lambda x: x[1], reverse=True):
            frequences.append({"decision": decision, "nb_fois": nb_fois, "sur": nombre_runs})

        decisions_par_operation.append({
            "operation_id":      op_id,
            "decision_attendue": decision_attendue,
            "est_stable":        est_stable,
            "decisions_par_run": liste_decisions,
            "frequences":        frequences
        })


    # 4 Calcul du score et recall par run 
    liste_recalls = []

    for run in liste_runs:
        decisions_ce_run = []

        for op_id, verite in verite_filtree.items():
            decision_agent = run["decisions_agent"].get(op_id, {}).get("decision", "MANQUANTE")
            decisions_ce_run.append({
                "decision_agent":    decision_agent,
                "decision_attendue": verite["decision_attendue"],
                "correct":           decision_agent == verite["decision_attendue"]
            })

        # Score global = % de bonnes réponses toutes opérations confondues
        total = len(decisions_ce_run)
        corrects = sum(1 for d in decisions_ce_run if d["correct"])
        run["score"] = corrects / total if total else 0

        # Recall strict = % d'immobilisations correctement détectées (sans escalade)
        immos_decidees = []

        for d in decisions_ce_run:
            if d["decision_attendue"] in {"reclassification", "split_operation"}:
                if d["decision_agent"] != "human_review":
                    immos_decidees.append(d)
        if immos_decidees:
            recall = sum(1 for d in immos_decidees if d["correct"]) / len(immos_decidees)
        else:
            recall = 0
        liste_recalls.append(recall)
        run["recall"] = recall

    # 5 Sauvegarde complète dans compare_history.json 
    dossier_resultats = Path(__file__).parent / "results"
    dossier_resultats.mkdir(exist_ok=True)
    fichier_historique = dossier_resultats / "compare_history.json"

    # Construction de l'entrée
    nouvelle_entree = {
        "date":                    datetime.now().isoformat(),
        "company_id":              company_analysee,
        "nombre_runs":             nombre_runs,
        "operations_instables":    operations_instables,
        "variance_recall":         round(max(liste_recalls) - min(liste_recalls), 3) if liste_recalls else None,
        "decisions_par_operation": decisions_par_operation,  # détail complet par opération
        "detail_runs":             []
    }

    # Infos par run
    for run in liste_runs:
        nouvelle_entree["detail_runs"].append({
            "run_id":         run["metadonnees"].get("run_id"),
            "model":          run["metadonnees"].get("model"),
            "prompt_version": run["metadonnees"].get("prompt_version"),
            "score_global":   round(run.get("score", 0), 3),
            "recall_strict":  round(run.get("recall", 0), 3),
        })

    # Chargement de l'historique existant (ou liste vide si premier appel)
    if fichier_historique.exists():
        with open(fichier_historique, encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = []

    historique.append(nouvelle_entree)
    with open(fichier_historique, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    print(f"✅ Comparaison sauvegardée → {fichier_historique}")

#  Lancement depuis le terminal 
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--last",    type=int, default=None, help="N derniers runs (ex: --last 5)")
    parser.add_argument("--company", type=str, default=None, help="Filtrer par company (ex: --company company_1)")
    args = parser.parse_args()

    # Récupération de tous les fichiers outputs, triés chronologiquement
    dossier_outputs = Path(__file__).parent / "outputs"
    tous_les_fichiers = sorted(dossier_outputs.glob("*.json"))

    if not tous_les_fichiers:
        print("Aucun fichier dans eval/outputs/")
        sys.exit(1)

    # Si --last est précisé, on ne prend que les N derniers
    if args.last:
        tous_les_fichiers = tous_les_fichiers[-args.last:]
    comparer(tous_les_fichiers, company_id=args.company)     

