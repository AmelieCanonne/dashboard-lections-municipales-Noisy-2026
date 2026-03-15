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

@st.cache_data(ttl=10)
def load_data():

    url="https://docs.google.com/spreadsheets/d/1-PtRHi2y2JCcw-U1aQr3FKHtuJguL1zT9naDObeOURs/export?format=csv&gid=0"

    df=pd.read_csv(url)

    df.columns=df.columns.str.strip()

    return df

df=load_data()

df = df.loc[:,~df.columns.duplicated()]

df["bureau_id"]=pd.to_numeric(df["bureau_id"],errors="coerce").astype("Int64")

# conversion numérique
for col in ["Votants","Exprimés","Blancs","Nuls","Inscrits"]:
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
bureaux_depouilles=(df["exprimes"]>0).sum()

st.progress(bureaux_depouilles/bureaux_total)
st.caption(f"Dépouillement : {bureaux_depouilles}/{bureaux_total}")

participation=df["Votants"].sum()/df["Inscrits"].sum()*100

c1,c2,c3,c4=st.columns(4)

c1.metric("Participation",f"{participation:.1f}%")
c2.metric("Liste en tête",classement.index[0])
c3.metric("Avance",classement.iloc[0]-classement.iloc[1])
c4.metric("Bureaux dépouillés",f"{bureaux_depouilles}/{bureaux_total}")

# -----------------------------
# GEOJSON
# -----------------------------

@st.cache_data
def load_geo():

    with open("bureaux_noisy.geojson") as f:

        geo=json.load(f)

    return geo

geojson=load_geo()

# dictionnaire bureau -> ligne dataframe
df_map=df.set_index(df["bureau_id"].astype(int)).to_dict("index")
st.write("Bureaux dans df_map :", list(df_map.keys())[:20])
st.write("Premier bureau geojson :", geojson["features"][0]["properties"]["bureau"])
# enrichissement du geojson
for feature in geojson["features"]:

    props = feature["properties"]

    bureau = int(props["bureau"])

    props["color"] = [200,200,200]
    props["leader"] = "AUCUN"
    props["exprimes"] = 0

    if bureau in df_map:

        ligne=df_map[bureau]

        props["color"]=COULEURS.get(ligne["leader"],[200,200,200])
        props["leader"]=ligne["leader"]
        props["exprimes"]=int(ligne["exprimes"])

# -----------------------------
# CARTE
# -----------------------------

layer=pdk.Layer(
    "GeoJsonLayer",
    data=geojson,
    pickable=True,
    get_fill_color="properties.color",
    get_line_color=[0,0,0],
    opacity=0.8,
    auto_highlight=True
)

view=pdk.ViewState(latitude=48.889,longitude=2.462,zoom=13)

deck=pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip={"html":"<b>Bureau {bureau}</b><br/>Exprimes : {exprimes}<br/>Leader : {leader}"}
)

col_map,col_chart=st.columns([2,1])

with col_map:

    st.subheader("Carte des bureaux")

    st.pydeck_chart(deck)

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

st.dataframe(df[["bureau_id","exprimes","leader"]+LISTES])