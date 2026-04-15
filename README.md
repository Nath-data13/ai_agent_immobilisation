# AI Agent — Révision des immobilisations 

Cas d'étude AI Agent Engineer — automatisation de la révision de clôture comptable.

**Problème** : les comptables doivent vérifier manuellement que les dépenses clients
n'ont pas été passées en charge alors qu'elles auraient dû être immobilisées.
Avec le volume de la base client, ce traitement manuel n'est plus tenable.

**Objectif** : Cet agent automatise la détection et la reclassification des dépenses comptables en immobilisations, en combinant LLM et logique métier déterministe.

---

## Prérequis

- Python 3.10+
- pip
- Accès à une clé API LLM (Anthropic)

---

## lancement du projet
```bash
# cloner le projet
git clone https://github.com/Nath-data13/agent_immo.git

# se placer dans le dossier du projet
cd agent_immo

# créer un environnement virtuel
python -m venv venv_immo

# activer l'environnement 
# windows
.\venv_immo\Scripts\activate   
# Mac /Linux
source venv_immo/bin/activate

# installer les dépendances
pip install -r requirements.txt         

```

---

## Partie 1 — Approche agentique

### Principe directeur
Séparer strictement ce qui relève du **jugement** (LLM) de ce qui relève de l'**exécution déterministe** (code Python pur). Le LLM ne touche jamais aux données — il décide, le code exécute.

### Étapes de conception et déploiement

**Phase 1 — Cadrage**
- Identifier les règles métier (seuils d'immobilisation par type d'entreprise, catégorie_comptable)
- Définir les 5 décisions possibles : `charge_confirmed`, `reclassification`, `split_operation`, `request_client_info`, `human_review`
- Définir les cas où l'humain garde la main (ambiguïté, information manquante, doute sur catégorie)

**Phase 2 — Construction**
- Modéliser le flux : collecte contexte → analyse LLM → exécution
- Écrire les prompts versionnés avec règles comptables injectées depuis RAG
- Construire la ground truth (9 opérations annotées avec justification)

**Phase 3 — Évaluation avant déploiement**
- Mesurer recall_strict, recall_système, escalade_inutile, 
- Seuil minimum : recall_strict >= 90%, escalade_inutile <= 10%

**Phase 4 — Production**
- Seuils de confiance configurables (thresholds.yaml) sans toucher au code
- Logging dans Neon DB pour traçabilité de chaque décision
- Checkpoint pour reprise automatique sur crash
- évolution future : mise en place de LLMProvider pour gérer les différents LLM

### Maîtrise de ce que fait l'agent
Toute décision est **structurée via un tool `soumettre_decision`** — le LLM ne peut pas
agir librement, il doit soumettre une décision dans un schéma contraint.
Les cas ambigus sont **systématiquement escaladés** en `human_review`.

---

## Partie 2 — Architecture agentique

### Flux agent principal

```
python -m agent.orchestrator
        │
        ├── 0. INITIALISATION
        │       Vérification de la connexion à la base Neon DB.
        │
        ├── 1. COLLECTE DU CONTEXTE (Context Agent)
        │       Récupération des données client + règles fiscales (RAG).
        │       Filtrage via CHECKPOINT pour ne traiter que les nouvelles opérations.
        │
        ├── 2. ANALYSE DES OPÉRATIONS (Analysis Agent - LLM)
        │       Analyse de chaque opération une par une.
        │       │
        │       ├── Score élevé (>= 0.80) : Décision validée directement.
        │       ├── Zone de doute (0.70 à 0.79) : Appel du CRITIC AGENT (IA de contrôle).
        │       └── Score faible (< 0.70) : Envoi direct en revue humaine.
        │       │
        │       └── Sauvegarde immédiate dans le CHECKPOINT (sécurité anti-crash).
        │
        ├── 3. EXÉCUTION (Executor)
        │       Application technique des décisions (Reclassification, Split, etc.).
        │
        ├── 4. CLÔTURE ET SAUVEGARDE
        │       Fermeture de la tâche Dougs si tout est traité.
        │       Enregistrement du rapport final dans Neon DB et en JSON local.
        │       Suppression du Checkpoint (travail terminé).
        │
        └── 5. SURVEILLANCE (Monitoring)
                Analyse automatique du taux d'erreur du run.
```

### Tools disponibles

| Tool | Rôle |
|---|---|
| `get_company_context` | Type entreprise, régime TVA |
| `get_operations` | Opérations à analyser |
| `get_categories` | Catégories comptables disponibles |
| `get_accounting_rules` | Règles fiscales SARL / LMNP depuis RAG |
| `get_operation_file` | Détail de la pièce jointe (lignes facture, montants) |
| `update_operation_category` | Reclassifie une opération |
| `split_operation` | Ventile une facture mixte charge/immo |
| `send_client_message` | Demande une info manquante au client |
| `alerte_collaborateur` | Escalade au comptable |
| `complete_tache_dougs` | Clôture la tâche si tout est traité |

### Décisions possibles

| Décision | Condition | Exécution automatique |
|---|---|---|
| `charge_confirmed` | Dépense correctement en charge | ✅ conf >= 0.85 |
| `reclassification` | Doit être immobilisée | ✅ conf >= 0.80 |
| `split_operation` | Facture mixte charge + immo | ✅ conf >= 0.80 |
| `request_client_info` | Information manquante | Message client |
| `human_review` | Cas ambigu ou conf < 0.70 | Alerte comptable |


### Intégration cible avec l'existant
Ce prototype **simule l'intégration finale** dans l'écosystème de production, mais **n'est pas encore connecté au serveur MCP**.

- À terme, l'agent s'intégrera via le **serveur MCP** — chaque tool correspondra à un appel API interne
- La tâche sera créée automatiquement par le système et clôturée par l'agent si tout est résolu
- Les cas `human_review` resteront dans la queue du comptable avec la raison d'escalade

---

## Partie 3 — Résultats et Suivis

### Flux d'évaluation

```
python eval/run_eval.py
        │
        ├── 1. INITIALISATION DE LA SÉRIE
        │       Récupération des paramètres (Nombre de runs, Company ciblée).
        │       Scan du dossier /outputs pour mémoriser l'état avant les tests.
        │
        ├── 2. BOUCLE D'EXÉCUTION (N fois)
        │       Appel de lancer_analyse() → Déclenche l'Orchestrateur complet.
        │       Pause de 30s entre chaque run (Évite le blocage des API LLM).
        │
        ├── 3. COLLECTE DES RÉSULTATS
        │       Identification des nouveaux fichiers JSON générés dans /outputs.
        │       Calcul des métriques (Recall / Accuracy) via compute_metrics.py.
        │
        ├── 4. ANALYSE DE LA STABILITÉ
        │       Calcul de la Variance : Écart entre le meilleur et le pire Recall.
        │       Détection des opérations instables (celles où l'IA a hésité).
        │       Verdict : "Stable" si l'écart est inférieur à 10%.
        │
        └── 5. ARCHIVAGE FINAL
                Enregistrement dans eval_stabilites_history.json.
                (Date, Modèle utilisé, Score de stabilité, Liste des erreurs).`
```

### 1 — Agent trop prudent
**Symptôme** : trop de `human_review` sur des cas évidents → escalade_inutile élevé.

**Court terme** : ajuster les seuils dans `configs/thresholds.yaml` sans toucher au code.
Baisser `seuil_critic_min` de 0.70 à 0.65, retravailler le prompt pour qu'il soit moins hésitant.

**Moyen terme** : pipeline d'évaluation `eval/` avec ground truth — mesurer recall_strict et escalade_inutile sur chaque version de prompt. Ne déployer que si les métriques s'améliorent.

### 2 — Tool `get_operation_file` tombe en erreur
**Symptôme** : l'agent reçoit une erreur lors de la récupération des pièces jointes.

**Court terme** : Filet de sécurité dans orchestrator.py si l’appel échoue, le système ne crash pas, l’opération est isolée et routée vers `Human_review` - Plan de secours avec `checkpoint.py` qui sauvegarde l'état d'avancement

**Moyen terme** : Réduire le volume human_review` avec un retry (ex : 3 tentatives) - Maintenir les pytests/test_tools.py` pour validation fonctionnement - Analyse de l’historique et de la traçabilité des runs dans Neon pour essayer d’identifier des patterns d’erreurs pour traiter l’origine de la panne (rate_limit, erreur serveur 500)

### 3 — Agent interrompt son analyse
**Symptôme** : le LLM s'arrête entre deux étapes sans soumettre de décision.

**Court terme** : utiliser le `checkpoint.py` pour limiter les ressources et gagner du temps - forcer l’agent à aller au bout de l’analyse dans le prompt - Ajustement des pauses entre les runs pour respecter les quotas (Rate Limits) des fournisseurs. 

**Moyen terme** : traçabilité  Néon : audit du raisonnement et diagnostic - Architecture multi-agents (hybride)

---

## Partie 4 — Migration LLM

### Méthodologie

**Étape 1 — Avant la migration**
- Lancer 5 runs avec le modèle actuel → sauvegarder les outputs dans `eval/outputs/`
- Calculer les métriques de référence (recall_strict, variance, escalade_inutile)

**Étape 2 — Migration**
- Changer le modèle dans une seule constante (`LLM_MODEL` dans `orchestrator.py`)
- Les prompts sont versionnés (`prompts/agent_analyse/current.txt`) — aucune modification

**Étape 3 — Vérification**
- Lancer 5 runs avec le nouveau modèle sur les mêmes données
- Comparer avec `eval/compare_runs.py` : delta recall_strict, régressions, instabilités

**Étape 4 — Décision**
- Si recall_strict >= référence ET variance stable → migration validée
- Si régression → rollback immédiat (changer la constante, redéployer)

### Garantie
Les prompts étant versionnés et les données de test fixes (ground truth),
la comparaison est **reproductible et objective** — pas d'effet de bord possible.

---

## Structure du projet

```
agent/
├── orchestrator.py       # Chef d'orchestre — coordonne tout
├── context_agent.py      # Collecte contexte (Python pur)
├── analysis_agent.py     # Analyse LLM — prend la décision
├── critic_agent.py       # Second regard sur les cas ambigus
├── executor.py           # Exécute la décision (Python pur)
├── checkpoint.py         # Reprise automatique sur crash
└── tools/                # 10 tools Python purs

configs/
└── thresholds.yaml       # Seuils de confiance configurables

data/
├── categories.json       # données des catégories comptables 
├── documents.json        # données du détail des factures 
├── entreprise.json       # données de l'entreprise
└── operations_cpte.json  # données de l'opération      

prompts/
├── agent_analyse/        # Prompt versionné (current.txt + v1.0.txt)
└── critic_agent/         # Prompt critic versionné

RAG/
├── categories_cpta.md     # catégorie comptable
├── regles_generales.md    # Règles communes
├── regles_sarl.md         # Seuil 500€ HT, PCG 311-3
└── regles_lmnp.md         # Seuil 500€ TTC, réparation vs amélioration

eval/
├──checkpoints/                 # sauvegarde temporaire du run en action        
├── data/ground_truth.json      # 9 opérations annotées
├── outputs/run_v1.0.json       # sauvegarde des runs
├── results/compute_metrics.py  # Recall strict, recall système
├── results/compare_runs.py     # Comparaison N runs
├── results/run_eval.py         # Lance N runs successifs
└── results/analysis.ipynb      # Visualisation des performances


tests/
├── test_tools.py           # Tests tools de collecte
├── test_executor.py        # Tests routing des décisions
└── test_checkpoint.py      # Tests reprise sur crash

logger.py                   # Logging Neon DB (traçabilité production)
monitoring.py               # Surveillance automatique des performances post-run  
requirements.txt            # dépendance du projet              
.env                        # variables d'environnement 
.gitignore                      

```

## Lancement de l'agent et des éval

```bash
# Lancer l'agent
python -m agent.orchestrator

# Évaluer les métriques
python eval/compute_metrics.py

# Comparer N runs
python eval/compare_runs.py --last 5 --company company_1

# lancer l'évaluation compléte sur 3 run
python eval/run_eval.py

# Tests unitaires (sans API, sans coût)
pytest tests/ -v
```
