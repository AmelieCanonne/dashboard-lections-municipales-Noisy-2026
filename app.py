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
    "TERKI","DELEU","FRANCESCHINI","LABIDI",
    "SARRABEYROUSE","KHETALA","BUROT","CORBANI"
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
# FONCTION INTENSITÉ COULEUR
# -----------------------------

def color_intensity(base_color, certainty):

    factor = min(max(certainty/20,0),1)

    r,g,b = base_color

    r = int(255 - (255-r)*factor)
    g = int(255 - (255-g)*factor)
    b = int(255 - (255-b)*factor)

    return [r,g,b]

# -----------------------------
# DATA
# -----------------------------

@st.cache_data(ttl=5)
def load_data():

    url="https://docs.google.com/spreadsheets/d/1-PtRHi2y2JCcw-U1aQr3FKHtuJguL1zT9naDObeOURs/export?format=csv&gid=0"

    df=pd.read_csv(url)
    df.columns=df.columns.str.strip()

    return df

df=load_data()

df = df.loc[:,~df.columns.duplicated()]

df["bureau_id"]=pd.to_numeric(df["bureau_id"],errors="coerce")
df=df.dropna(subset=["bureau_id"])
df["bureau_id"]=df["bureau_id"].astype(int)

for col in ["Votants","Exprimés","Blancs","Nuls","Inscrits"]:
    if col in df.columns:
        df[col]=pd.to_numeric(df[col],errors="coerce").fillna(0)

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

values=df[LISTES].values
idx=np.argsort(-values,axis=1)

lists_array=np.array(LISTES)

df["top1"]=lists_array[idx[:,0]]
df["top2"]=lists_array[idx[:,1]]

df["top1_voix"]=values[np.arange(len(values)),idx[:,0]]
df["top2_voix"]=values[np.arange(len(values)),idx[:,1]]

df["top1_pct"]=df["top1_voix"]/df["exprimes_safe"]*100
df["top2_pct"]=df["top2_voix"]/df["exprimes_safe"]*100

df["certitude"]=df["top1_pct"]-df["top2_pct"]

# -----------------------------
# SOLIDITÉ TENDANCE
# -----------------------------

totaux=df[LISTES].sum()

leader_global=totaux.idxmax()
second_global=totaux.sort_values(ascending=False).index[1]

avance=totaux[leader_global]-totaux[second_global]

participation_obs = (
    df["Votants"].sum() / df["Inscrits"].sum()
    if df["Inscrits"].sum() > 0 else 0
)

inscrits_restants=df[df["exprimes"]==0]["Inscrits"].sum()

voix_restantes=inscrits_restants*participation_obs

solidite=min(avance/voix_restantes,1) if voix_restantes>0 else 1

# -----------------------------
# METRIQUES
# -----------------------------

classement=totaux.sort_values(ascending=False)

bureaux_total=len(df)
bureaux_depouilles=(df["exprimes"]>0).sum()

st.progress(bureaux_depouilles/bureaux_total)

participation=(
    df["Votants"].sum()/df["Inscrits"].sum()*100
    if df["Inscrits"].sum()>0 else 0
)

c1,c2,c3,c4,c5=st.columns(5)

c1.metric("Participation",f"{participation:.1f}%")
c2.metric("Liste en tête",leader_global)
c3.metric("Avance",avance)
c4.metric("Bureaux dépouillés",f"{bureaux_depouilles}/{bureaux_total}")
c5.metric("Solidité tendance",f"{solidite*100:.1f}%")

# -----------------------------
# GEOJSON
# -----------------------------

with open("bureaux_noisy.geojson") as f:
    geojson=json.load(f)

df_map=df.set_index("bureau_id").to_dict("index")

for feature in geojson["features"]:

    bureau=int(feature["properties"]["bureau"])

    if bureau in df_map:

        row=df_map[bureau]

        leader=row["leader"]
        expr=int(row["exprimes"])
        cert=float(row["certitude"])

        base_color=COULEURS.get(leader,[200,200,200])
        color=color_intensity(base_color,cert)

    else:

        leader="AUCUN"
        expr=0
        cert=0
        color=[200,200,200]

    feature["properties"]["leader"]=leader
    feature["properties"]["exprimes"]=expr
    feature["properties"]["certitude"]=round(cert,1)
    feature["properties"]["fill_color"]=color

# -----------------------------
# CARTE
# -----------------------------

layer=pdk.Layer(
    "GeoJsonLayer",
    geojson,
    pickable=True,
    filled=True,
    stroked=True,
    get_fill_color="properties.fill_color",
    get_line_color=[0,0,0],
    auto_highlight=True
)

view=pdk.ViewState(
    latitude=48.889,
    longitude=2.462,
    zoom=13
)

deck=pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip={
    "html":"""
    <b>Bureau {bureau}</b><br/>
    Exprimés : {exprimes}<br/>
    Leader : {leader}<br/>
    Écart : {certitude} %    """}
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

st.dataframe(df[
    ["bureau_id","exprimes","leader","certitude"]+LISTES
])