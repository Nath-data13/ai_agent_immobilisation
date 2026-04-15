import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from agent.context_agent import collecter_contexte
from agent.analysis_agent import analyser_operation, charger_seuils
from agent.critic_agent import critiquer_decision
from agent.executor import executer_decision
from agent.tools.complete_tache_dougs import complete_tache_dougs
import agent.checkpoint as checkpoint
from logger import save_run, init_db, sauvegarder_output
from monitoring import surveiller_run

# ---------------------------------------------------------------------------
# ORCHESTRATEUR — Python pur, aucun LLM
# Coordonne : Collecte → Analyse (+ Critic si zone grise) → Exécution → Clôture
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("orchestrator")

DECISIONS_CLOTURABLES = {"charge_confirmed", "reclassification", "split_operation"}

load_dotenv()
try:
    init_db()
except Exception as e:
    log.warning("Connexion Neon indisponible : %s — logging DB désactivé", e)


def _est_zone_grise(decision: dict, seuils: dict) -> bool:
    confidence = decision.get("confidence", 0.0)
    choix = decision.get("decision")
    if confidence < seuils["seuil_critic_min"]:
        return False
    seuil_auto = seuils.get(choix)
    return seuil_auto is not None and confidence < seuil_auto


def lancer_analyse(company_id: str, tache_id: str) -> list:
    log.info("Démarrage — %s / %s", company_id, tache_id)
    tools_trace_global = []
    seuils = charger_seuils()

    # ── 1. Collecte du contexte ────────────────────────────────────────────
    try:
        contexte, trace = collecter_contexte(company_id)
        tools_trace_global.extend(trace)
    except Exception as e:
        log.error("Erreur collecte contexte : %s", e)
        return []

    operations = contexte["operations"]
    log.info("[context_agent] %d opération(s) récupérée(s)", len(operations))

    # ── 2. Reprise sur checkpoint ──────────────────────────────────────────
    etat = checkpoint.charger(company_id, tache_id)
    if etat:
        log.info("Reprise — %d opération(s) déjà traitée(s)", len(etat))
    operations_restantes = [op for op in operations if op.get("operation_id") not in etat]

    # ── 3. Analyse en parallèle ────────────────────────────────────────────
    def _analyser(operation: dict) -> tuple[dict, list]:
        op_id = operation.get("operation_id", "?")
        log.info("[analysis_agent] Analyse de %s", op_id)
        try:
            decision, trace = analyser_operation(operation, contexte)
        except Exception as e:
            log.error("[analysis_agent] Erreur sur %s : %s", op_id, e)
            decision = {"operation_id": op_id, "decision": "human_review", "confidence": 0.0,
                        "reasoning": f"ERREUR_TECHNIQUE : {e}", "raison_human_review": f"ERREUR_TECHNIQUE : {e}"}
            trace = []

        log.info("[analysis_agent] %s → %s (conf: %.2f)",
                 op_id, decision["decision"], decision.get("confidence", 0.0))

        if _est_zone_grise(decision, seuils):
            log.info("[critic_agent] Zone grise sur %s → relecture...", op_id)
            try:
                decision = critiquer_decision(operation, contexte, decision)
                log.info("[critic_agent] %s → %s", op_id, decision["decision"])
            except Exception as e:
                log.error("[critic_agent] Erreur sur %s : %s — décision conservée", op_id, e)

        checkpoint.sauvegarder(company_id, tache_id, op_id, decision, etat)
        return decision, trace

    decisions = list(etat.values())
    with ThreadPoolExecutor(max_workers=min(len(operations_restantes) or 1, 1)) as pool:# passage à 1.1 au lieu de 1.2 car trop error rate limit avec claude
        futures = {pool.submit(_analyser, op): op for op in operations_restantes}
        for future in as_completed(futures):
            decision, trace = future.result()
            decisions.append(decision)
            tools_trace_global.extend(trace)

    # ── 4. Exécution ───────────────────────────────────────────────────────
    rapport = []
    for decision in decisions:
        resultat, trace = executer_decision(decision, company_id)
        rapport.append(resultat)
        tools_trace_global.extend(trace)

    # ── 5. Clôture si toutes les opérations sont traitées ──────────────────
    if {d["decision"] for d in decisions}.issubset(DECISIONS_CLOTURABLES):
        log.info("Toutes les opérations traitées → clôture de la tâche")
        res = complete_tache_dougs(company_id=company_id, tache_id=tache_id)
        tools_trace_global.append({"tool_name": "complete_tache_dougs",
                                    "tool_args": {"company_id": company_id, "tache_id": tache_id},
                                    "resultat": res})
    else:
        log.info("Opération(s) en attente → tâche non clôturée")

    # ── 6. Sauvegarde + nettoyage ──────────────────────────────────────────
    sauvegarder_output(company_id=company_id, liste_decisions=decisions)
    checkpoint.supprimer(company_id, tache_id)

    try:
        seuils = charger_seuils()
        save_run(company_id=company_id, tache_id=tache_id, llm_model=seuils.get("llm_model", "unknown"),
                 historique_outils=tools_trace_global, rapport_final=json.dumps(rapport, ensure_ascii=False))
    except Exception as e:
        log.error("Erreur sauvegarde Neon : %s", e)

    # ── 7. Surveillance des performances ──────────────────────────────────────
    try:
        surveiller_run(company_id)
    except Exception as e:
        log.error("Erreur monitoring : %s", e)

    return rapport


if __name__ == "__main__":
    for company_id, tache_id in [("company_1", "tache-002"), ("company_2", "tache-002")]:
        log.info("=" * 50)
        log.info("ANALYSE : %s", company_id)
        rapport = lancer_analyse(company_id=company_id, tache_id=tache_id)
        log.info("Résumé %s :", company_id)
        for r in rapport:
            log.info("  %s → %s", r["operation_id"], r["status"])
