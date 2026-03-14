import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import numpy as np
import json

def metric_box(label, value, color):
    st.markdown(
        f"""
        <div style="
            background-color:{color};
            padding:12px;
            border-radius:10px;
            text-align:center;
        ">
            <div style="font-size:0.95rem;font-weight:700;color:black;">
                {label}
            </div>
            <div style="font-size:1.9rem;font-weight:700;color:black;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.set_page_config(layout="wide")

st_autorefresh(interval=5000)

st.title("Résultats 1er tour par bureau")

# -----------------------------
# CONFIGURATION
# -----------------------------

LISTES = {
    "TERKI": "UN NOUVEL ÉLAN POUR NOISY — Souad TERKI",
    "DELEU": "SAUVONS NOISY — Olivier DELEU",
    "FRANCESCHINI": "NOISY AU CŒUR — Thomas FRANCESCHINI",
    "LABIDI": "NOISY SOLIDAIRE — Karim LABIDI",
    "SARRABEYROUSE": '"Toujours Noisy" - Olivier SARRABEYROUSE',
    "KHETALA": "NOISY UNIE - Morad KHETALA",
    "BUROT": "LO - Jean-Paul BUROT",
    "CORBANI": "POIF - Corinne CORBANI"
}

colonnes_listes = list(LISTES.keys())

COULEURS = {
    "TERKI": [70,130,180],
    "DELEU": [25,25,112],
    "FRANCESCHINI": [255,215,0],
    "LABIDI": [255,105,180],
    "SARRABEYROUSE": [220,20,60],
    "KHETALA": [255,140,0],
    "BUROT": [128,0,32],
    "CORBANI": [102,0,51],
    "AUCUN": [200,200,200]
}

# -----------------------------
# CHARGEMENT DES DONNÉES
# -----------------------------

@st.cache_data(ttl=30)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1-PtRHi2y2JCcw-U1aQr3FKHtuJguL1zT9naDObeOURs/export?format=csv&gid=0"
    return pd.read_csv(url)

df = load_data()

df.columns = df.columns.str.strip()

df["bureau_id"] = pd.to_numeric(df["bureau_id"], errors="coerce")

# -----------------------------
# CONVERSION NUMERIQUE
# -----------------------------

for col in ["Votants","Exprimés","Blancs","Nuls","Inscrits"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# -----------------------------
# RENOMMAGE DES COLONNES LISTES
# -----------------------------

rename_dict = {}

for col in df.columns:
    col_upper = col.upper()
    for liste in colonnes_listes:
        if liste in col_upper:
            rename_dict[col] = liste

df.rename(columns=rename_dict, inplace=True)

df = df.loc[:, ~df.columns.duplicated()]

for liste in colonnes_listes:
    if liste not in df.columns:
        df[liste] = 0

df[colonnes_listes] = df[colonnes_listes].apply(pd.to_numeric, errors="coerce").fillna(0)

# -----------------------------
# GEOJSON
# -----------------------------

@st.cache_data
def load_geojson():
    with open("bureaux_noisy.geojson") as f:
        return json.load(f)

geojson = load_geojson()
# -----------------------------
# CALCULS
# -----------------------------

df["exprimes"] = df["Exprimés"]
df["exprimes_safe"] = df["exprimes"].replace(0,1)

for l in colonnes_listes:
    df[f"{l}_pct"] = df[l] / df["exprimes_safe"] * 100

df["leader"] = df[colonnes_listes].idxmax(axis=1)
df.loc[df["exprimes"] == 0, "leader"] = "AUCUN"

df["color"] = df["leader"].map(COULEURS)

# -----------------------------
# TOP 3
# -----------------------------

values = df[colonnes_listes].values

sorted_idx = np.argsort(-values, axis=1)

lists_array = np.array(colonnes_listes)

df["top1"] = lists_array[sorted_idx[:,0]]
df["top2"] = lists_array[sorted_idx[:,1]]
df["top3"] = lists_array[sorted_idx[:,2]]

df["top1_voix"] = values[np.arange(len(values)), sorted_idx[:,0]]
df["top2_voix"] = values[np.arange(len(values)), sorted_idx[:,1]]
df["top3_voix"] = values[np.arange(len(values)), sorted_idx[:,2]]

df["top1_pct"] = df["top1_voix"] / df["exprimes_safe"] * 100

# -----------------------------
# GEOJSON INJECTION
# -----------------------------

for feature in geojson["features"]:

    bureau = feature["properties"]["bureau"]

    ligne = df[df["bureau_id"] == bureau]

    if not ligne.empty:

        ligne = ligne.iloc[0]

        leader = ligne["leader"]

        feature["properties"]["color"] = COULEURS.get(leader,[200,200,200])
        feature["properties"]["top1"] = ligne["top1"]
        feature["properties"]["top1_voix"] = int(ligne["top1_voix"])
        feature["properties"]["top1_pct"] = round(ligne["top1_pct"],1)
        feature["properties"]["top2"] = ligne["top2"]
        feature["properties"]["top2_voix"] = int(ligne["top2_voix"])
        feature["properties"]["top3"] = ligne["top3"]
        feature["properties"]["top3_voix"] = int(ligne["top3_voix"])
        feature["properties"]["exprimes"] = int(ligne["exprimes"])

    else:

        feature["properties"]["color"] = [220,220,220]

# -----------------------------
# METRIQUES
# -----------------------------

totaux = df[colonnes_listes].sum()

classement = totaux.sort_values(ascending=False)

bureaux_remontes = (df["Exprimés"] > 0).sum()
bureaux_total = len(df)

# -----------------------------
# VOIX RESTANTES (CORRIGÉ)
# -----------------------------

total_votants = pd.to_numeric(df["Votants"], errors="coerce").fillna(0).sum()

total_depouilles = (
    pd.to_numeric(df["Exprimés"], errors="coerce").fillna(0) +
    pd.to_numeric(df["Blancs"], errors="coerce").fillna(0) +
    pd.to_numeric(df["Nuls"], errors="coerce").fillna(0)
).sum()

voix_restantes_estimees = max(0, int(total_votants - total_depouilles))

# -----------------------------
# AVANCE
# -----------------------------

if len(classement) > 1:
    avance = classement.iloc[0] - classement.iloc[1]
else:
    avance = 0

leader_global = classement.index[0] if totaux.sum() > 0 else "—"

# -----------------------------
# PROBA
# -----------------------------

prob_leader = 0

if "prob_prec" not in st.session_state:
    st.session_state.prob_prec = prob_leader

prob_leader = 0.7 * st.session_state.prob_prec + 0.3 * prob_leader

st.session_state.prob_prec = prob_leader

# -----------------------------
# METRICS UI
# -----------------------------

col1,col2,col3,col4,col5,col6,col7 = st.columns(7)

col1.metric("Bureaux dépouillés",f"{bureaux_remontes}/{bureaux_total}")

col2.metric("Liste en tête",leader_global)

col3.metric("Avance",f"{avance} voix")

col4.metric("Probabilité victoire",f"{prob_leader*100:.1f}%")

with col5:
    st.markdown("**Voix restantes**  \n**estimées**")
    st.metric("", voix_restantes_estimees)