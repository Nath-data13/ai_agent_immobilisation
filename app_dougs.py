import streamlit as st
import json
import yaml
import time
from pathlib import Path

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Use cas AI agent Engineer",
    page_icon="",
    layout="wide"
)

# --- STYLE PERSONNALISE (LOOK & FEEL DOUGS) ---
st.markdown("""
    <style>
    :root {
        --dougs-blue: #1E3A8A;
        --dougs-light-bg: #F3F4F6;
    }
    .stApp {
        background-color: var(--dougs-light-bg);
    }
    h1 {
        color: #1E3A8A !important;
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-weight: 700;
    }
    .result-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #1E3A8A;
        margin-bottom: 20px;
        color: #1F2937;
    }
    div.stButton > button:first-child {
        background-color: #1E3A8A;
        color: white;
        border-radius: 8px;
        border: none;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #3B82F6;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURATION DES CHEMINS ---
ROOT_DIR = Path(__file__).parent.absolute()
FILENAME = "run_v1.0_claudesonnet46_company_1_20260413_1924.json"
DATA_FILE = ROOT_DIR / "data" / "operations_cpta.json"
CONFIG_FILE = ROOT_DIR / "configs" / "thresholds.yaml"
OUTPUT_FILE = ROOT_DIR / "eval" / "outputs" / FILENAME

# --- CHARGEMENT DES DONNEES ---
def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
    return {
        "seuils": {
            "charge_confirmed": 0.85,
            "reclassification": 0.80,
            "split_operation": 0.80,
            "seuil_critic_min": 0.70,
            "human_review_max": 0.70
        }
    }

def get_historical_result(operation_id):
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            for entry in data.get('results', []):
                if str(entry.get('operation_id')) == str(operation_id):
                    return entry['runs'][0] if entry.get('runs') else None
    return None

def load_all_operations():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

# --- INTERFACE ---

st.title("AI Agent Charges vs Immobilisations")
st.write("Contôle de révision comptable automatisée")

# Sidebar : AFFICHAGE DE TOUS TES SEUILS
with st.sidebar:
    st.markdown("### Configuration des Seuils")
    config = load_config()
    s = config['seuils']
    
    st.markdown("**Execution Automatique**")
    st.info(f"Charge : {s['charge_confirmed']}")
    st.info(f"Reclass : {s['reclassification']}")
    st.info(f"Split : {s['split_operation']}")
    
    st.markdown("**Zones d'Arbitrage**")
    st.warning(f"Critic Agent : {s['seuil_critic_min']} a 0.80")
    st.error(f"Human Review : < {s['human_review_max']}")
    
    st.markdown("---")
    st.caption(f"Fichier : {FILENAME}")

# Corps principal
ops = load_all_operations()
if ops:
    def format_op(x):
        return f"{x.get('wording', 'Op')} - {x.get('amount_eur', 0)} euros"

    # 1. On affiche le titre en plus gros avec du Markdown (H2)
    st.markdown("## Sélectionner une opération :")

    # 2. On utilise le selectbox avec un label vide (ou caché)
    selected_op = st.selectbox(
        "label_hidden", # Ce texte ne sera pas visible
        ops, 
        format_func=format_op,
        label_visibility="collapsed" # Cette option cache le label par défaut
    )
        
    

    op_id = selected_op.get('operation_id') or selected_op.get('id')

    if st.button("Lancer l'Analyse"):
        with st.status("Traitement par l'agent en cours...", expanded=True) as status:
            st.write("Etape 1 : Consultation du contexte client...")
            time.sleep(0.5)
            
            result = get_historical_result(op_id)
            
            if result:
                score = result.get('confidence_score', 0)
                decision = result.get('decision', 'unknown')
                
                # Verification par rapport aux seuils
                seuil_auto = s.get(decision.lower(), 0.80)
                
                if score >= seuil_auto:
                    msg, color_code = "AUTOMATIQUE", "green"
                elif score >= s['seuil_critic_min']:
                    msg, color_code = "CRITIC AGENT", "orange"
                else:
                    msg, color_code = "HUMAN REVIEW", "red"

                status.update(label=f"Analyse terminee - Statut : {msg}", state="complete")
                
                # Affichage formaté
                st.markdown(f"""
                    <div class="result-card">
                        <h3 style="margin-top:0; color:#1E3A8A;">Decision : {decision.upper()}</h3>
                        <p>Score de confiance : <b>{score:.2f}</b></p>
                        <p>Seuil requis pour auto-validation : <b>{seuil_auto}</b></p>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("#### Raisonnement de l'intelligence artificielle")
                st.info(result.get('reasoning', 'Pas de detail.'))
            else:
                status.update(label="Donnee introuvable", state="error")
                st.warning(f"ID {op_id} non repertorie dans les archives.")
else:
    st.error("Aucune donnee operationnelle chargee.")