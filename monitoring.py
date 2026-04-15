import json
import logging
import os
import urllib.request
import yaml
from pathlib import Path

from eval.compute_metrics import compute_metrics

# ---------------------------------------------------------------------------
# MONITORING — Surveillance automatique des performances post-run
# Calcule recall_strict et escalade_inutile sur le dernier output.
# Envoie une alerte Slack si les métriques passent sous les seuils configurés.
# Appelé automatiquement par l'orchestrator à la fin de chaque run.
# ---------------------------------------------------------------------------

THRESHOLDS_PATH = Path(__file__).parent / "configs" / "thresholds.yaml"
OUTPUTS_PATH    = Path(__file__).parent / "eval" / "outputs"

log = logging.getLogger("monitoring")


def _charger_seuils_alertes() -> dict:
    with open(THRESHOLDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["alertes"]


def _envoyer_alerte_slack(message: str):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        log.warning("[monitoring] SLACK_WEBHOOK_URL non défini — alerte non envoyée")
        return
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        log.info("[monitoring] Alerte Slack envoyée")
    except Exception as e:
        log.error("[monitoring] Échec envoi Slack : %s", e)


def surveiller_run(company_id: str):
    """
    Calcule les métriques du dernier output pour company_id.
    Envoie une alerte Slack si recall_strict ou escalade_inutile dépassent les seuils.
    """
    # Dernier fichier output pour cette company
    outputs = sorted(OUTPUTS_PATH.glob(f"*_{company_id}_*.json"))
    if not outputs:
        log.warning("[monitoring] Aucun output trouvé pour %s", company_id)
        return

    dernier_output = str(outputs[-1])
    log.info("[monitoring] Analyse de %s", Path(dernier_output).name)

    try:
        metriques = compute_metrics(dernier_output)
    except Exception as e:
        log.error("[monitoring] Erreur calcul métriques : %s", e)
        return

    seuils = _charger_seuils_alertes()
    alertes = []

    recall = metriques["recall_strict"]
    escalade = metriques["escalade_inutile_rate"]
    modele = metriques.get("model", "?")
    prompt = metriques.get("prompt_version", "?")

    if recall < seuils["recall_strict_min"]:
        alertes.append(
            f"recall_strict = {recall:.1%} < seuil {seuils['recall_strict_min']:.0%} "
            f"→ l'agent rate des immobilisations"
        )

    if escalade > seuils["escalade_inutile_max"]:
        alertes.append(
            f"escalade_inutile = {escalade:.1%} > seuil {seuils['escalade_inutile_max']:.0%} "
            f"→ l'agent est trop prudent"
        )

    if alertes:
        message = (
            f":rotating_light: *ALERTE AGENT IMMO — {company_id}*\n"
            f"Modèle : `{modele}` | Prompt : `{prompt}`\n"
            + "\n".join(f"• {a}" for a in alertes)
            + f"\nFichier : `{Path(dernier_output).name}`"
        )
        log.warning("[monitoring] ALERTE : %s", " | ".join(alertes))
        _envoyer_alerte_slack(message)
    else:
        log.info("[monitoring] %s — métriques OK (recall=%.1f%%, escalade=%.1f%%)",
                 company_id, recall * 100, escalade * 100)
