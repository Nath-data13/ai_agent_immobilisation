from pydantic import BaseModel, Field
from typing import Optional, Literal

# ---------------------------------------------------------------------------
# SCHÉMAS DE DONNÉES — Vision de la structure avant implémentation
# Ces modèles décrivent ce que l'agent analyse, décide et produit
# pour chaque opération bancaire.
# ---------------------------------------------------------------------------


# Données brutes de l'opération (issues de get_operations)
class SourceData(BaseModel):
    wording: str                  # libellé de l'opération
    amount_eur: float             # montant TTC en euros
    category_actuelle: str        # catégorie actuelle choisie par le client
    category_id_actuel: int       # identifiant de la catégorie actuelle
    file_uuid: str                # identifiant de la pièce jointe


# Proposition de reclassification (utilisée si décision = reclassification)
class Proposition(BaseModel):
    category_id: int              # identifiant de la nouvelle catégorie
    compte_pcg: str               # compte PCG associé (ex: 2183)
    category_wording: str         # libellé de la catégorie proposée


# Ventilation d'une facture mixte (utilisée si décision = split_operation)
class SplitOperation(BaseModel):
    montant_charge: float         # part à conserver en charge
    montant_immo: float           # part à immobiliser


# Message client ou alerte collaborateur
class ClientRequest(BaseModel):
    message: str                  # contenu du message envoyé
    collaborateur_alerte: Optional[str] = None  # raison de l'alerte si human_review


# ---------------------------------------------------------------------------
# MODÈLE PRINCIPAL — Une analyse par opération
# ---------------------------------------------------------------------------
class OperationAnalysis(BaseModel):
    operation_id: str

    decision: Literal[
        "charge_confirmed",    # dépense correctement en charge, rien à faire
        "reclassification",    # doit être immobilisée
        "split_operation",     # facture mixte : partie charge + partie immo
        "request_client_info", # information manquante, on demande au client
        "human_review"         # cas ambigu, jugement humain requis
    ]

    confidence: float = Field(ge=0.0, le=1.0)  # niveau de certitude (0 → 1)
    reasoning: str                               # raisonnement détaillé en 5 étapes

    source_data: SourceData                      # données de l'opération analysée

    proposition: Optional[Proposition] = None   # si reclassification
    split: Optional[SplitOperation] = None      # si split_operation

    action_requise: Literal[
        "auto_apply",          # confidence suffisante → exécution automatique
        "human_review",        # ambiguïté → alerte collaborateur
        "request_client_info"  # info manquante → message client
    ]

    human_review_reason: Optional[str] = None   # si human_review
    client_request: Optional[ClientRequest] = None  # si request_client_info ou reclassification sans date
