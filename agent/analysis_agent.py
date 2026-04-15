import os
import json
import time
import yaml
import anthropic
from pathlib import Path
from dotenv import load_dotenv
from agent.tools.get_operation_file import get_operation_file

load_dotenv()

# ---------------------------------------------------------------------------
# ANALYSIS AGENT — LLM Sonnet, analyse UNE seule opération
# Prompt chargé depuis prompts/agent_analyse/current.txt (versionné)
# Seuils chargés depuis configs/thresholds.yaml (modifiables sans toucher au code)
# Client et prompts initialisés une seule fois au chargement du module (pas à chaque appel)
# ---------------------------------------------------------------------------

PROMPT_PATH     = Path(__file__).parent.parent / "prompts" / "agent_analyse" / "current.txt"
THRESHOLDS_PATH = Path(__file__).parent.parent / "configs" / "thresholds.yaml"

# Singletons — lus une seule fois au démarrage
_client: anthropic.Anthropic | None = None
_seuils: dict | None = None
_system_prompt: str | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def charger_seuils() -> dict:
    global _seuils
    if _seuils is None:
        with open(THRESHOLDS_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        _seuils = config["seuils"]
        _seuils["llm_model"] = config["modele"]["llm_model"]
        _seuils["prompt_version"] = config["modele"]["prompt_version"]
    return _seuils


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        seuils = charger_seuils()
        with open(PROMPT_PATH, encoding="utf-8") as f:
            prompt = f.read()
        _system_prompt = prompt + f"""
## SEUILS ACTIFS (depuis configs/thresholds.yaml)
- charge_confirmed    : confidence >= {seuils['charge_confirmed']} → exécution automatique
- reclassification    : confidence >= {seuils['reclassification']} → exécution automatique
- split_operation     : confidence >= {seuils['split_operation']} → exécution automatique
- Zone grise          : {seuils['seuil_critic_min']} <= confidence < seuil_auto → critic obligatoire
- human_review direct : confidence < {seuils['human_review_max']}
"""
    return _system_prompt


TOOLS_ANALYSE = [
    {
        "name": "get_operation_file",
        "description": "Récupère le détail de la pièce jointe (facture ou ticket). Retourne les lignes de facture et le montant total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_uuid": {
                    "type": "string",
                    "description": "Identifiant unique de la pièce jointe"
                },
                "operation_id": {
                    "type": "string",
                    "description": "Identifiant de l'opération associée"
                }
            },
            "required": ["file_uuid", "operation_id"]
        }
    },
    {
        "name": "soumettre_decision",
        "description": "Soumet la décision finale après analyse. OBLIGATOIRE — appeler en dernier après get_operation_file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation_id": {"type": "string", "description": "Identifiant de l'opération analysée"},
                "decision": {"type": "string", "enum": ["charge_confirmed", "reclassification", "split_operation", "request_client_info", "human_review"], "description": "Décision finale"},
                "confidence": {"type": "number", "description": "Niveau de confiance entre 0 et 1"},
                "reasoning": {"type": "string", "description": "Raisonnement détaillé en 5 étapes"},
                "new_category_id": {"type": "integer", "description": "Requis si reclassification ou split_operation"},
                "message_client": {"type": "string", "description": "Requis si request_client_info"},
                "raison_human_review": {"type": "string", "description": "Requis si human_review"},
                "montant_charge": {"type": "number", "description": "Requis si split_operation — part en charge"},
                "montant_immo": {"type": "number", "description": "Requis si split_operation — part immobilisée"}
            },
            "required": ["operation_id", "decision", "confidence", "reasoning"]
        }
    }
]


def appeler_avec_retry(fonction, tool_args: dict, max_tentatives: int = 3) -> dict: #  retry = on réessaie intelligemment, fallback = si tout échoue, on escalade à un humain plutôt que de crasher.
    """Retry automatique — attend 1s, 2s, 4s entre chaque tentative."""
    for tentative in range(max_tentatives):
        try:
            return fonction(**tool_args)
        except Exception as e:
            if tentative < max_tentatives - 1:
                time.sleep(2 ** tentative)
            else:
                return {"erreur": str(e), "status": "echec_apres_retry"}


def analyser_operation(operation: dict, contexte: dict) -> tuple:
    """Analyse UNE opération avec le LLM. Retourne (decision, tools_trace)."""
    client = _get_client()
    system_prompt = _get_system_prompt()
    seuils = charger_seuils()

    prompt_utilisateur = f"""Contexte entreprise :
{json.dumps(contexte['entreprise'], ensure_ascii=False, indent=2)}

Règles comptables :
{contexte['regles']}

Catégories disponibles :
{json.dumps(contexte['categories'], ensure_ascii=False, indent=2)}

Opération à analyser :
{json.dumps(operation, ensure_ascii=False, indent=2)}
"""

    messages = [{"role": "user", "content": prompt_utilisateur}]
    tools_trace = []
    decision_finale = None

    max_steps = 6
    step_count = 0

    while step_count < max_steps:
        step_count += 1
        response = client.messages.create(
            model=seuils["llm_model"],
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
            tools=TOOLS_ANALYSE,
            timeout=60.0
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        for tool_call in response.content:
            if tool_call.type != "tool_use":
                continue

            tool_args = dict(tool_call.input)

            if tool_call.name == "soumettre_decision":
                decision_finale = tool_args
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": json.dumps({"status": "decision_enregistree"})}]
                })

            elif tool_call.name == "get_operation_file":
                resultat = appeler_avec_retry(get_operation_file, tool_args)
                tools_trace.append({"tool_name": "get_operation_file", "tool_args": tool_args, "resultat": resultat})
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": json.dumps(resultat)}]
                })

    if decision_finale is None:
        decision_finale = {
            "operation_id": operation.get("operation_id", "inconnu"),
            "decision": "human_review",
            "confidence": 0.0,
            "reasoning": "L'agent n'a pas soumis de décision",
            "raison_human_review": "ERREUR_AGENT : décision non soumise"
        }

    return decision_finale, tools_trace
