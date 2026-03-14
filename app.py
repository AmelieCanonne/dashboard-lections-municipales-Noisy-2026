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

# rafraîchissement automatique
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

@st.cache_data(ttl=3)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1-PtRHi2y2JCcw-U1aQr3FKHtuJguL1zT9naDObeOURs/export?format=csv&gid=0"
    return pd.read_csv(url)

df = load_data()

# IMPORTANT : chemin relatif pour Streamlit Cloud
with open("bureaux_noisy.geojson") as f:
    geojson = json.load(f)

df.rename(columns={'Code BV':'bureau_id'}, inplace=True)
df = df.replace(r'^\s*$', 0, regex=True)

for liste in colonnes_listes:
    if liste not in df.columns:
        df[liste] = 0

df[colonnes_listes] = df[colonnes_listes].apply(pd.to_numeric, errors="coerce").fillna(0)

# -----------------------------
# RENOMMAGE DES COLONNES
# -----------------------------

rename_dict = {}

for col in df.columns:
    col_upper = col.upper()
    for liste in colonnes_listes:
        if liste in col_upper:
            rename_dict[col] = liste

df.rename(columns=rename_dict, inplace=True)

# -----------------------------
# CALCULS
# -----------------------------

for liste in colonnes_listes:
    if liste not in df.columns:
        df[liste] = 0

df["exprimes"] = df[colonnes_listes].sum(axis=1)
df["exprimes_safe"] = df["exprimes"].replace(0,1)

for l in colonnes_listes:
    df[f"{l}_pct"] = df[l] / df["exprimes_safe"] * 100

df["leader"] = df[colonnes_listes].idxmax(axis=1)
df.loc[df["exprimes"] == 0, "leader"] = "AUCUN"

df["color"] = df["leader"].map(COULEURS)

# -----------------------------
# TOP 3
# -----------------------------

df["top1"] = df[colonnes_listes].idxmax(axis=1)
df["top1_voix"] = df[colonnes_listes].max(axis=1)

df["top2"] = df[colonnes_listes].apply(lambda x: x.nlargest(2).index[-1], axis=1)
df["top2_voix"] = df[colonnes_listes].apply(lambda x: x.nlargest(2).values[-1], axis=1)

df["top3"] = df[colonnes_listes].apply(lambda x: x.nlargest(3).index[-1], axis=1)
df["top3_voix"] = df[colonnes_listes].apply(lambda x: x.nlargest(3).values[-1], axis=1)

df["top1_pct"] = df["top1_voix"] / df["exprimes_safe"] * 100

# -----------------------------
# INJECTION DANS GEOJSON
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

bureaux_remontes = (df["exprimes"] > 0).sum()
bureaux_total = len(df)

bureaux_restants = bureaux_total - bureaux_remontes

if bureaux_remontes > 0:
    moyenne_exprimes = df[df["exprimes"] > 0]["exprimes"].mean()
    voix_restantes_estimees = int(bureaux_restants * moyenne_exprimes)
else:
    voix_restantes_estimees = 0

# -----------------------------
# VOIX NECESSAIRES
# -----------------------------

voix_necessaires = 0
score_minimum_second = 0

if totaux.sum() > 0 and voix_restantes_estimees > 0 and len(classement) > 1:

    premier = classement.index[0]
    deuxieme = classement.index[1]

    voix_premier = totaux[premier]
    voix_deuxieme = totaux[deuxieme]

    avance = voix_premier - voix_deuxieme
    voix_necessaires = avance + 1

    score_minimum_second = (
        (voix_deuxieme + voix_restantes_estimees) /
        (voix_premier + voix_deuxieme + voix_restantes_estimees)
    ) * 100

else:
    avance = 0

leader_global = classement.index[0] if totaux.sum() > 0 else "—"

# -----------------------------
# PROBA
# -----------------------------

prob_leader = 0

# LISSAGE
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

with col6:
    metric_box(
        "Voix nécessaires au 2nd pour prendre la tête",
        voix_necessaires,
        "#eef6ff"
    )

with col7:
    metric_box(
        "Score minimum du second dans les bureaux restants",
        f"{score_minimum_second:.1f}%",
        "#fff4e6"
    )

# -----------------------------
# CARTE
# -----------------------------

layer = pdk.Layer(
    "GeoJsonLayer",
    geojson,
    pickable=True,
    auto_highlight=True,
    get_fill_color="properties.color",
    get_line_color=[0,0,0]
)

view_state = pdk.ViewState(
    latitude=48.889,
    longitude=2.462,
    zoom=13
)

tooltip = {
    "html": """
    <b>Bureau {bureau}</b><br>
    Exprimés : {exprimes}<br><br>

    🥇 {top1} : {top1_voix} voix ({top1_pct}%)<br>
    🥈 {top2} : {top2_voix} voix<br>
    🥉 {top3} : {top3_voix} voix
    """,
    "style": {"backgroundColor": "black", "color": "white"}
}

col_map, col_chart = st.columns([2,1])

with col_map:

    st.subheader("Carte des bureaux")

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip
        )
    )

with col_chart:

    st.subheader("Scores globaux")

    fig = px.bar(
        x=classement.index,
        y=classement.values,
        text=classement.values
    )

    fig.update_traces(textposition="outside")

    st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# TABLEAU
# -----------------------------

st.subheader("Résultats par bureau")

st.dataframe(
    df[["bureau_id","exprimes","leader"] + colonnes_listes]
)