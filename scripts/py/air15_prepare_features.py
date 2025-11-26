# -*- coding: utf-8 -*-
"""
AIR-15 — Préparation des features pour le clustering K-means

Objectif :
    Créer un fichier unique avec toutes les colonnes nécessaires
    au clustering K-means.

Entrées :
    - release/features_by_airline.csv  (AIR-5)
    - release/airline_scores.csv       (AIR-9)

Sortie :
    - release/air15_features_for_clustering.csv

1 ligne = 1 compagnie
Colonnes :
    - airline (identifiant)
    - fleet_size
    - n_models
    - diversity
    - modernity_index
    - new_gen_share
    - pct_a220
    - pct_787
    - pct_a350
    - pct_a330neo
    - pct_neo
    - pct_max
    - pct_newgen_narrow
    - pct_newgen_wide
"""

from pathlib import Path
import pandas as pd

# ---------- 0) Constantes de chemin ----------
FEATURES_SRC = Path("release/features_by_airline.csv")
SCORES_SRC = Path("release/airline_scores.csv")
DST = Path("release/air15_features_for_clustering.csv")

DST.parent.mkdir(parents=True, exist_ok=True)

# ---------- 1) Charger les fichiers sources ----------
if not FEATURES_SRC.exists():
    raise SystemExit(f"Introuvable : {FEATURES_SRC.resolve()}")

if not SCORES_SRC.exists():
    raise SystemExit(f"Introuvable : {SCORES_SRC.resolve()}")

features = pd.read_csv(FEATURES_SRC)
scores = pd.read_csv(SCORES_SRC)

# On ne garde dans airline_scores que ce qui est vraiment utile ici
scores_small = scores[["airline", "modernity_index"]].copy()

# ---------- 2) Jointure sur 'airline' ----------
merged = features.merge(scores_small, on="airline", how="inner")

# ---------- 3) Sélection des colonnes utiles ----------
cols = [
    "airline",
    "fleet_size",
    "n_models",
    "diversity",
    "modernity_index",
    "new_gen_share",
    "pct_a220",
    "pct_787",
    "pct_a350",
    "pct_a330neo",
    "pct_neo",
    "pct_max",
    "pct_newgen_narrow",
    "pct_newgen_wide",
]

missing = [c for c in cols if c not in merged.columns]
if missing:
    raise SystemExit(f"Colonnes manquantes dans le merged : {missing}")

air15 = merged[cols].copy()

# Optionnel : trier par nom de compagnie pour la lisibilité
air15 = air15.sort_values("airline").reset_index(drop=True)

# ---------- 4) Export ----------
air15.to_csv(DST, index=False, encoding="utf-8")
print(f"OK : {len(air15)} compagnies exportées vers {DST}")
