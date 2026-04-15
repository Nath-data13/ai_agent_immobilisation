import argparse
import time
import sys
import json
from datetime import datetime
from pathlib import Path

# On indique à Python qu'il peut importer des fichiers du dossier courant (eval)
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent)) # Ajoute la racine du projet

# Import de la fonction d'analyse depuis l'orchestrateur de l'agent
from agent.orchestrator import lancer_analyse

# Import de notre nouvel outil de calcul de métriques simple
from compute_metrics import compute_metrics

# Temps de pause entre chaque exécution pour ne pas se faire bloquer par l'API (Anthropic, OpenAI...)
PAUSE_ENTRE_RUNS = 30  # en secondes

# ---------------------------------------------------------------------------
# RUN EVAL — Lance l'agent plusieurs fois de suite et vérifie s'il est stable
#
# Objectif : L'agent fait-il les mêmes choix si on lui pose 3 fois le même test ?
#
# Usage :
#   python eval/run_eval.py                  ← 3 runs, toutes les companies
#   python eval/run_eval.py --runs 5         ← 5 runs
#   python eval/run_eval.py --company company_1 --runs 3

# Liste des couples (company_id, tache_id) par défaut
COMPANIES_PAR_DEFAUT = [("company_1", "tache-002"), ("company_2", "tache-002")]

def lancer_plusieurs_runs(company_id: str, tache_id: str, nombre_de_runs: int):
    """Lance l'agent et sauvegarde la stabilité globale dans eval_stabilites_history.json."""
    
    print(f"\n DÉMARRAGE ÉVALUATION : {company_id} ({nombre_de_runs} tentatives)")
    dossier_outputs = Path(__file__).parent / "outputs"
    
    # 1. Mémoriser quels fichiers existaient *avant* de lancer
    fichiers_avant = []
    for f in dossier_outputs.glob("*.json"):
        fichiers_avant.append(str(f))

    # 2. On fait tourner l'agent en boucle N fois
    for numero_run in range(1, nombre_de_runs + 1):
        print(f"Exécution du Run {numero_run}/{nombre_de_runs} en cours...")
        
        # Le "cerveau" se met en route
        lancer_analyse(company_id=company_id, tache_id=tache_id)
        
        if numero_run < nombre_de_runs:
            print(f"     [Pause de {PAUSE_ENTRE_RUNS}s]...")
            time.sleep(PAUSE_ENTRE_RUNS)

    # 3. Trouver les nouveaux fichiers générés
    nouveaux_fichiers = []
    for f in dossier_outputs.glob("*.json"):
        chemin_complet = str(f)
        if chemin_complet not in fichiers_avant and company_id in f.name:
            nouveaux_fichiers.append(chemin_complet)
            
    nouveaux_fichiers = sorted(nouveaux_fichiers)

    if not nouveaux_fichiers:
        print(" Aucun output généré (problème d'analyse).")
        return
    
    # 4. Calculer les notes pour chaque nouvelle tentative
    # Cela sauvegarde AUSSI automatiquement chaque run dans metrics_history.json 
    bilan_des_runs = []
    for fichier in nouveaux_fichiers:
        metriques = compute_metrics(fichier)
        bilan_des_runs.append(metriques)
    if len(bilan_des_runs) < 2:
        print("  Impossible d'évaluer la stabilité avec 1 seul run.")
        return
    
    # 5. Calcul de la Variance (L'agent a-t-il été régulier ?)
    liste_des_recalls = []
    for metrique in bilan_des_runs:
        liste_des_recalls.append(metrique["recall_strict"])

    point_le_plus_bas = min(liste_des_recalls)
    point_le_plus_haut = max(liste_des_recalls)
    ecart = point_le_plus_haut - point_le_plus_bas
    est_stable = ecart <= 0.10  # Vrai si la différence est max 10%

    # 6. Lister précisément les opérations qui posent souci (instables)
    operations_qui_hesitent = []
    for metrique in bilan_des_runs:
        for operation in metrique["unstable_cases"]:
            if operation not in operations_qui_hesitent:
                operations_qui_hesitent.append(operation)
    operations_qui_hesitent = sorted(operations_qui_hesitent)

     # 7. SAUVEGARDE JSON (, on écrit dans le fichier)
    dossier_resultats = Path(__file__).parent / "results"
    dossier_resultats.mkdir(exist_ok=True)
    fichier_historique = dossier_resultats / "eval_stabilites_history.json"

    nouvelle_entree = {
        "date": datetime.now().isoformat(),
        "company_id": company_id,
        "nombre_de_runs": nombre_de_runs,
        "modele_utilise": bilan_des_runs[0].get("model"),
        "variance_recall": round(ecart, 3),
        "est_stable": est_stable,
        "pire_recall": round(point_le_plus_bas, 3),
        "meilleur_recall": round(point_le_plus_haut, 3),
        "operations_instables": operations_qui_hesitent,
        "historique_des_runs_concernes": nouveaux_fichiers
    }

     # Chargement de l'ancien historique s'il existe
    if fichier_historique.exists():
        with open(fichier_historique, encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = []

    historique.append(nouvelle_entree)
    with open(fichier_historique, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    print(f"Série terminée ! Bilan sauvegardé dans {fichier_historique.name}")

# Lancement depuis le terminal 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="Combien de fois répéter le test ? (défaut: 3)")
    parser.add_argument("--company", type=str, default=None, help="Cibler une company spécifique ? (optionnel)")
    args = parser.parse_args()

    if args.company:
        liste_a_tester = [(args.company, "tache-002")]
    else:
        liste_a_tester = COMPANIES_PAR_DEFAUT
    for company_id, tache_id in liste_a_tester:
        lancer_plusieurs_runs(company_id=company_id, tache_id=tache_id, nombre_de_runs=args.runs)
