import os
import json
import yaml
import anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CRITIC AGENT — LLM Sonnet, valide les décisions dans la zone grise
# Appelé uniquement si seuil_critic_min < confidence < seuil_auto
# Relit la décision de l'agent d'analyse et confirme, corrige ou escalade.
# Client et prompt initialisés une seule fois au chargement du module.
# ---------------------------------------------------------------------------

PROMPT_PATH      = Path(__file__).parent.parent / "prompts" / "critic_agent" / "current.txt"
THRESHOLDS_PATH  = Path(__file__).parent.parent / "configs" / "thresholds.yaml"

# Singletons
_client: anthropic.Anthropic | None = None
_system_prompt: str | None = None
_llm_model: str | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        with open(PROMPT_PATH, encoding="utf-8") as f:
            _system_prompt = f.read()
    return _system_prompt


def _get_llm_model() -> str:
    global _llm_model
    if _llm_model is None:
        with open(THRESHOLDS_PATH, encoding="utf-8") as f:
            _llm_model = yaml.safe_load(f)["modele"]["llm_model"]
    return _llm_model

TOOL_SOUMETTRE_VERDICT = [
    {
        "name": "soumettre_verdict",
        "description": "Soumet le verdict final après relecture de la décision de l'agent d'analyse.",
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["confirmer", "corriger", "human_review"], "description": "confirmer = décision correcte / corriger = décision incorrecte / human_review = escalade"},
                "raisonnement_critic": {"type": "string", "description": "Justification détaillée du verdict"},
                "decision_corrigee": {"type": "string", "enum": ["charge_confirmed", "reclassification", "split_operation", "request_client_info", "human_review"], "description": "Requis uniquement si verdict = corriger"},
                "new_category_id": {"type": "integer", "description": "Requis si decision_corrigee = reclassification ou split_operation"},
                "raison_human_review": {"type": "string", "description": "Requis si verdict = human_review"}
            },
            "required": ["verdict", "raisonnement_critic"]
        }
    }
]


def critiquer_decision(operation: dict, contexte: dict, decision_agent: dict) -> dict:
    """Relit la décision de l'agent d'analyse et retourne un verdict."""
    client = _get_client()
    system_prompt = _get_system_prompt()

    prompt_utilisateur = f"""Contexte entreprise :
{json.dumps(contexte['entreprise'], ensure_ascii=False, indent=2)}

Règles comptables :
{contexte['regles']}

Catégories disponibles :
{json.dumps(contexte['categories'], ensure_ascii=False, indent=2)}

Opération analysée :
{json.dumps(operation, ensure_ascii=False, indent=2)}

Décision proposée par l'agent d'analyse :
{json.dumps(decision_agent, ensure_ascii=False, indent=2)}
"""

    messages = [{"role": "user", "content": prompt_utilisateur}]
    verdict = None

    while True:
        response = client.messages.create(
            model=_get_llm_model(),
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=TOOL_SOUMETTRE_VERDICT,
            timeout=60.0
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        for tool_call in response.content:
            if tool_call.type != "tool_use":
                continue
            if tool_call.name == "soumettre_verdict":
                verdict = dict(tool_call.input)
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": json.dumps({"status": "verdict_enregistre"})}]
                })

    if verdict is None:
        return {**decision_agent, "decision": "human_review", "raisonnement_critic": "ERREUR_AGENT : le critic n'a pas soumis de verdict", "raison_human_review": "ERREUR_CRITIC : verdict non soumis"}

    if verdict["verdict"] == "confirmer":
        return {**decision_agent, "raisonnement_critic": verdict["raisonnement_critic"]}

    elif verdict["verdict"] == "corriger":
        decision_corrigee = {**decision_agent, "decision": verdict.get("decision_corrigee", "human_review"), "raisonnement_critic": verdict["raisonnement_critic"], "corrige_par_critic": True}
        if "new_category_id" in verdict:
            decision_corrigee["new_category_id"] = verdict["new_category_id"]
        return decision_corrigee

    else:
        return {**decision_agent, "decision": "human_review", "raisonnement_critic": verdict["raisonnement_critic"], "raison_human_review": verdict.get("raison_human_review", "Escalade par le critic")}
