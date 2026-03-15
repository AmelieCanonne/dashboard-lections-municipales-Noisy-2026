import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide")

st_autorefresh(interval=5000)

st.title("Résultats 1er tour par bureau")

# -----------------------------
# CONFIG
# -----------------------------

LISTES = [
    "TERKI",
    "DELEU",
    "FRANCESCHINI",
    "LABIDI",
    "SARRABEYROUSE",
    "KHETALA",
    "BUROT",
    "CORBANI"
]

COULEURS = {
    "TERKI":[70,130,180],
    "DELEU":[25,25,112],
    "FRANCESCHINI":[255,215,0],
    "LABIDI":[255,105,180],
    "SARRABEYROUSE":[220,20,60],
    "KHETALA":[255,140,0],
    "BUROT":[128,0,32],
    "CORBANI":[102,0,51],
    "AUCUN":[200,200,200]
}

# -----------------------------
# DATA
# -----------------------------

@st.cache_data(ttl=30)
def load_data():
    url="https://docs.google.com/spreadsheets/d/1-PtRHi2y2JCcw-U1aQr3FKHtuJguL1zT9naDObeOURs/export?format=csv&gid=0"
    df=pd.read_csv(url)
    df.columns=df.columns.str.strip()
    return df

df=load_data()

# conversion numérique
for col in ["bureau_id","Votants","Exprimés","Blancs","Nuls","Inscrits"]:
    if col in df.columns:
        df[col]=pd.to_numeric(df[col],errors="coerce").fillna(0)

# colonnes listes
for l in LISTES:
    if l not in df.columns:
        df[l]=0
    df[l]=pd.to_numeric(df[l],errors="coerce").fillna(0)

# -----------------------------
# CALCULS
# -----------------------------

df["exprimes"]=df["Exprimés"]
df["exprimes_safe"]=df["exprimes"].replace(0,1)

# leader bureau
df["leader"]=df[LISTES].idxmax(axis=1)
df.loc[df["exprimes"]==0,"leader"]="AUCUN"

df["color"]=df["leader"].map(COULEURS)

# top 3
values=df[LISTES].values
idx=np.argsort(-values,axis=1)

lists_array=np.array(LISTES)

df["top1"]=lists_array[idx[:,0]]
df["top2"]=lists_array[idx[:,1]]
df["top3"]=lists_array[idx[:,2]]

df["top1_voix"]=values[np.arange(len(values)),idx[:,0]]
df["top2_voix"]=values[np.arange(len(values)),idx[:,1]]
df["top3_voix"]=values[np.arange(len(values)),idx[:,2]]

df["top1_pct"]=df["top1_voix"]/df["exprimes_safe"]*100

# -----------------------------
# METRIQUES
# -----------------------------

totaux=df[LISTES].sum()
classement=totaux.sort_values(ascending=False)

bureaux_total=len(df)
bureaux_depouilles=(df["Exprimés"]>0).sum()

# barre progression
progress_depouillement=bureaux_depouilles/bureaux_total if bureaux_total>0 else 0

st.progress(progress_depouillement)
st.caption(f"Dépouillement : {bureaux_depouilles}/{bureaux_total} bureaux")

# participation
total_inscrits=df["Inscrits"].sum()
total_votants=df["Votants"].sum()

if total_inscrits>0:
    participation=total_votants/total_inscrits*100
else:
    participation=np.nan

# voix restantes
total_depouilles=(df["Exprimés"]+df["Blancs"]+df["Nuls"]).sum()
voix_restantes=max(0,int(total_votants-total_depouilles))

# avance
if len(classement)>1:
    avance=classement.iloc[0]-classement.iloc[1]
else:
    avance=0

leader=classement.index[0] if totaux.sum()>0 else "—"

# score minimum second
score_min_second=0
voix_necessaires=0

if voix_restantes>0 and len(classement)>1:

    premier=classement.index[0]
    second=classement.index[1]

    voix_premier=totaux[premier]
    voix_second=totaux[second]

    voix_necessaires=(voix_premier-voix_second)+1

    score_min_second=(voix_second+voix_restantes)/(voix_premier+voix_second+voix_restantes)*100

# -----------------------------
# METRICS UI
# -----------------------------

c1,c2,c3,c4,c5,c6,c7=st.columns(7)

if np.isnan(participation):
    participation_display="—"
else:
    participation_display=f"{participation:.1f}%"

c1.metric("Participation",participation_display)
c2.metric("Liste en tête",leader)
c3.metric("Avance",f"{avance} voix")
c4.metric("Probabilité victoire","0%")

with c5:
    st.metric("Voix restantes",voix_restantes)

with c6:
    st.metric("Voix nécessaires au 2nd",voix_necessaires)

with c7:
    st.metric("Score minimum du second",f"{score_min_second:.1f}%")

# -----------------------------
# GEOJSON
# -----------------------------

@st.cache_data
def load_geo():
    with open("bureaux_noisy.geojson") as f:
        return json.load(f)

geojson=load_geo()

for feature in geojson["features"]:

    bureau=feature["properties"]["bureau"]
    ligne=df[df["bureau_id"]==bureau]

    if not ligne.empty:

        ligne=ligne.iloc[0]

        feature["properties"]["color"]=ligne["color"]

        feature["properties"]["top1"]=ligne["top1"]
        feature["properties"]["top1_voix"]=int(ligne["top1_voix"])
        feature["properties"]["top1_pct"]=round(ligne["top1_pct"],1)

        feature["properties"]["top2"]=ligne["top2"]
        feature["properties"]["top2_voix"]=int(ligne["top2_voix"])

        feature["properties"]["top3"]=ligne["top3"]
        feature["properties"]["top3_voix"]=int(ligne["top3_voix"])

        feature["properties"]["exprimes"]=int(ligne["exprimes"])

# -----------------------------
# CARTE
# -----------------------------

layer=pdk.Layer(
    "GeoJsonLayer",
    geojson,
    pickable=True,
    get_fill_color="properties.color",
    get_line_color=[0,0,0]
)

view=pdk.ViewState(latitude=48.889,longitude=2.462,zoom=13)

col_map,col_chart=st.columns([2,1])

with col_map:

    st.subheader("Carte des bureaux")

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view
        )
    )

with col_chart:

    st.subheader("Scores globaux")

    fig=px.bar(
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

table=df[["bureau_id","exprimes","leader"]+LISTES].copy()
table=table.replace(0,"—")

st.dataframe(table)