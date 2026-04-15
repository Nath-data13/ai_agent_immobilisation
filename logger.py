import json
import logging
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

log = logging.getLogger("logger")

load_dotenv()

# Connexion Neon
def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS source_operations (
    operation_id VARCHAR PRIMARY KEY,
    company_id VARCHAR,
    date VARCHAR,
    wording VARCHAR,
    montant_ttc NUMERIC,
    category_actuelle VARCHAR,
    category_id_actuel INTEGER,
    file_uuid VARCHAR
);
CREATE TABLE IF NOT EXISTS runs (
    run_id                  VARCHAR PRIMARY KEY,
    timestamp               TIMESTAMPTZ NOT NULL,
    company_id              VARCHAR NOT NULL,
    tache_id                VARCHAR NOT NULL,
    llm_model               TEXT,
    nb_charge_confirmed     INTEGER DEFAULT 0,
    nb_reclassification     INTEGER DEFAULT 0,
    nb_human_review         INTEGER DEFAULT 0,
    nb_request_client_info  INTEGER DEFAULT 0,
    nb_split_operation      INTEGER DEFAULT 0,
    rapport_final           TEXT
);
CREATE TABLE IF NOT EXISTS run_operations (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR REFERENCES runs(run_id),
    operation_id VARCHAR,
    decision_agent VARCHAR,
    tool_name VARCHAR,
    tool_args JSONB,
    resultat JSONB
);
CREATE TABLE IF NOT EXISTS run_decisions (
    id SERIAL PRIMARY KEY,
    run_id          VARCHAR REFERENCES runs(run_id),
    operation_id    VARCHAR NOT NULL,
    decision_agent  VARCHAR NOT NULL
)
"""

# PRIORITÉ DES DÉCISIONS :
# Si l'agent utilise plusieurs outils pour une même opération, on garde le plus impactant.
# Ex: S'il fait une "alerte_collaborateur" (niveau 1), ça écrase tout le reste.
PRIORITE_DECISIONS = {
    "alerte_collaborateur":      ("human_review", 1),
    "split_operation":           ("split_operation", 2),
    "update_operation_category": ("reclassification", 3),
    "send_client_message":       ("request_client_info", 4),
}

# GESTION DE LA BASE DE DONNÉES (Neon DB)

def import_source_data():
    """Importe les données comptables brutes depuis le JSON vers la table source."""
    chemin_data = Path(__file__).parent / "data" / "operations_cpta.json"

    with open(chemin_data, encoding="utf-8") as f:
        liste_operations = json.load(f)

    conn = get_connection()
    cur = conn.cursor()

    for op in liste_operations:
        cur.execute(
            "INSERT INTO source_operations VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (op["operation_id"], op["company_id"], op["date"], op["wording"],
             op["amount_eur"], op["category"], op["category_id"], op["file_uuid"])
        )

    conn.commit()
    cur.close()
    conn.close()


def init_db():
    """Initialise les tables dans NeonDB si elles n'existent pas encore."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    cur.close()
    conn.close()


def save_run(company_id: str, tache_id: str, llm_model: str, historique_outils: list, rapport_final: str):
    """Sauvegarde tout le "cerveau" et les décisions de l'agent après un Run."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp = datetime.now().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    # Dictionnaire de traduction (Nom de l'outil technique → Nom de la décision comptable)
    CORRESPONDANCE_OUTILS = {
        "update_operation_category": "reclassification",
        "split_operation":           "split_operation",
        "alerte_collaborateur":      "human_review",
        "send_client_message":       "request_client_info",
        "complete_tache_dougs":      "tache_completee"
    }

    # 1 : Analyser tout l'historique pour trouver la décision finale 
    
    # A) On liste toutes les opérations que l'agent a lues (via l'outil get_operation_file)
    operations_lues = []
    for outil in historique_outils:
        if outil["tool_name"] == "get_operation_file":
            op_id = outil["tool_args"].get("operation_id")
            if op_id and op_id not in operations_lues:
                operations_lues.append(op_id)

    # B) On cherche s'il a pris une décision spécifique pour ces opérations
    decisions_par_operation = {}
    for outil in historique_outils:
        op_id = outil["tool_args"].get("operation_id")
        nom_outil = outil["tool_name"]
        
        if not op_id:
            continue
            
        if nom_outil in PRIORITE_DECISIONS:
            decision_label, niveau_priorite = PRIORITE_DECISIONS[nom_outil]
            
            # Si on n'a pas encore de décision, ou si on trouve une décision plus prioritaire
            decision_actuelle = decisions_par_operation.get(op_id)
            if decision_actuelle is None or niveau_priorite < decision_actuelle["priorite"]:
                decisions_par_operation[op_id] = {
                    "decision": decision_label, 
                    "priorite": niveau_priorite
                }

    # C) Conclusion par défaut :
    # Si une opération a été lue mais n'a reçu aucune action (A moins B), 
    # c'est que l'agent a jugé silencieusement que tout allait bien ("charge_confirmed")
    for op_id in operations_lues:
        if op_id not in decisions_par_operation:
            decisions_par_operation[op_id] = {
                "decision": "charge_confirmed",
                "priorite": 99
            }

    # D) On fait les totaux pour les métriques du Run
    compteur_decisions = {}
    for op_id, details in decisions_par_operation.items():
        decision = details["decision"]
        if decision not in compteur_decisions:
            compteur_decisions[decision] = 0
        compteur_decisions[decision] += 1

    # ── ÉTAPE 2 : Sauvegarde dans NeonDB ──

    # TABLE RUNS : On l'insère en tout premier (les autres tables en ont besoin)
    cur.execute(
        """INSERT INTO runs VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            run_id, timestamp, company_id, tache_id, llm_model,
            compteur_decisions.get("charge_confirmed", 0),
            compteur_decisions.get("reclassification", 0),
            compteur_decisions.get("human_review", 0),
            compteur_decisions.get("request_client_info", 0),
            compteur_decisions.get("split_operation", 0),
            rapport_final
        )
    )

    # TABLE RUN_OPERATIONS : Une ligne par outil utilisé (Le Brouillon complet)
    for outil in historique_outils:
        op_id = outil["tool_args"].get("operation_id")
        decision_liee = CORRESPONDANCE_OUTILS.get(outil["tool_name"])
        
        cur.execute(
            "INSERT INTO run_operations (run_id, operation_id, decision_agent, tool_name, tool_args, resultat) VALUES (%s, %s, %s, %s, %s, %s)",
            (run_id, op_id, decision_liee, outil["tool_name"], json.dumps(outil["tool_args"]), json.dumps(outil["resultat"]))
        )

    # TABLE RUN_DECISIONS : Une ligne par opération (Le Résultat propre)
    for op_id, details in decisions_par_operation.items():
        decision_finale = details["decision"]
        
        # C'est ici que tu avais enlevé les 3 colonnes inutiles, c'est appliqué !
        cur.execute(
            "INSERT INTO run_decisions (run_id, operation_id, decision_agent) VALUES (%s, %s, %s)",
            (run_id, op_id, decision_finale)
        )

    conn.commit()
    cur.close()
    conn.close()


# SAUVEGARDE LOCALE JSON — Création des logs .json pour l'évaluation locale

OUTPUTS_PATH = Path(__file__).parent / "eval" / "outputs"
OUTPUTS_PATH.mkdir(parents=True, exist_ok=True)

def _charger_config_modele() -> dict:
    chemin_config = Path(__file__).parent / "configs" / "thresholds.yaml"
    import yaml
    with open(chemin_config, encoding="utf-8") as f:
        return yaml.safe_load(f)["modele"]

_config_courante = _charger_config_modele()
PROMPT_VERSION   = _config_courante["prompt_version"]
LLM_MODEL        = _config_courante["llm_model"]


def sauvegarder_output(company_id: str, liste_decisions: list):
    """Génère le fichier JSON pour que compute_metrics.py et run_eval.py puissent travailler."""
    horodatage = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier = f"run_{PROMPT_VERSION}_{LLM_MODEL.replace('-', '')}_{company_id}_{horodatage}.json"
    chemin = OUTPUTS_PATH / nom_fichier

    # Restructuration pour grouper par operation_id
    dictionnaire_resultats = {}
    for decision in liste_decisions:
        op_id = decision.get("operation_id")
        if op_id not in dictionnaire_resultats:
            dictionnaire_resultats[op_id] = {"operation_id": op_id, "runs": []}
            
        dictionnaire_resultats[op_id]["runs"].append({
            "decision": decision.get("decision"),
            "confidence_score": decision.get("confidence"),
            "reasoning": decision.get("reasoning")
        })

    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {"run_id": horodatage, "company_id": company_id, "prompt_version": PROMPT_VERSION, "model": LLM_MODEL},
            "results": list(dictionnaire_resultats.values())
        }, f, ensure_ascii=False, indent=2)

    log.info("[output] Sauvegardé → %s", chemin.name)

