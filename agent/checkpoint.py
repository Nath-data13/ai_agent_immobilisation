import json
from pathlib import Path
from threading import Lock

# ---------------------------------------------------------------------------
# CHECKPOINT — sauvegarde les décisions au fur et à mesure
# Permet la reprise automatique si le run plante en cours d'exécution.
# ---------------------------------------------------------------------------

CHECKPOINTS_PATH = Path(__file__).parent.parent / "eval" / "checkpoints"
CHECKPOINTS_PATH.mkdir(parents=True, exist_ok=True)

_lock = Lock()


def chemin(company_id: str, tache_id: str) -> Path:
    return CHECKPOINTS_PATH / f"{company_id}_{tache_id}.json"


def charger(company_id: str, tache_id: str) -> dict:
    """Retourne {operation_id: decision} pour les opérations déjà traitées."""
    p = chemin(company_id, tache_id)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauvegarder(company_id: str, tache_id: str, op_id: str, decision: dict, etat: dict):
    """Ajoute une décision à l'état partagé et persiste sur disque (thread-safe)."""
    with _lock:
        etat[op_id] = decision
        with open(chemin(company_id, tache_id), "w", encoding="utf-8") as f:
            json.dump(etat, f, ensure_ascii=False, indent=2)


def supprimer(company_id: str, tache_id: str):
    chemin(company_id, tache_id).unlink(missing_ok=True)
