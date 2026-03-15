import gspread
import pandas as pd
import numpy as np
import time
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------------
# CONNEXION GOOGLE SHEETS
# -----------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("/Users/ameliecanonne/swift-drive-490306-t3-b5bb9d1b6d10.json", scope)

client = gspread.authorize(creds)

sheet = client.open("Résultats par bureau Municipales 1er tour").sheet1


# -----------------------------
# LISTES
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

# score moyen simulé
scores = [0.28,0.24,0.15,0.10,0.09,0.06,0.05,0.03]


# -----------------------------
# HEADER
# -----------------------------

header = [
    "bureau_id",
    "Votants",
    "Exprimés",
    "Blancs",
    "Nuls",
    "Inscrits"
] + LISTES

sheet.clear()
sheet.append_row(header)


# -----------------------------
# SIMULATION BUREAUX
# -----------------------------

for bureau in range(1,22):

    inscrits = np.random.randint(800,1200)

    participation = np.random.uniform(0.55,0.70)

    votants = int(inscrits * participation)

    blancs = np.random.randint(0,10)
    nuls = np.random.randint(0,5)

    exprimes = votants - blancs - nuls


    # calcul des voix
    voix = []
    reste = exprimes

    for i,score in enumerate(scores):

        if i == len(scores)-1:
            v = reste
        else:
            v = int(exprimes * score * np.random.uniform(0.9,1.1))
            reste -= v

        voix.append(v)


    row = [
        bureau,
        votants,
        exprimes,
        blancs,
        nuls,
        inscrits
    ] + voix


    sheet.append_row(row)

    print(f"Bureau {bureau} simulé")

    # délai pour simulation soirée électorale
    time.sleep(2)