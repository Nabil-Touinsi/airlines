# -*- coding: utf-8 -*-
"""
AIR-9 — Compute scores v1
Entrées :
  - release/features_by_airline.csv  (colonnes: airline, fleet_size, n_models, pct_*, pct_newgen_*)
  - release/AIR3_dataset_v1.xlsx     (fallback pour fleet_size si besoin)

Sortie  :
  - release/airline_scores.csv (airline, fleet_size, diversity, modernity_index, version_v1, qa_notes)
"""

from pathlib import Path
import pandas as pd

MIN_FLEET = 5

SRC_FEAT = Path("release/features_by_airline.csv")
SRC_AIR3 = Path("release/AIR3_dataset_v1.xlsx")
DST      = Path("release/airline_scores.csv")
DST.parent.mkdir(parents=True, exist_ok=True)

def to_num(s): return pd.to_numeric(s, errors="coerce")

def to_prop(s):
    s = to_num(s)
    over1 = s > 1
    s.loc[over1] = s.loc[over1] / 100.0
    return s.fillna(0).clip(0, 1)

def norm_name(s): return str(s).strip().upper()

# ---------- 1) charger sources ----------
if not SRC_FEAT.exists():
    raise SystemExit(f"Introuvable : {SRC_FEAT.resolve()}")
feat = pd.read_csv(SRC_FEAT)

# fallback AIR3 (au cas où il manquerait fleet_size)
air3 = None
if SRC_AIR3.exists():
    air3 = pd.read_excel(SRC_AIR3)[["airline", "fleet_size"]].copy()
    air3["airline_norm"] = air3["airline"].map(norm_name)

# ---------- 2) nettoyage minimal ----------
for c in ["airline"]:
    if c not in feat.columns:
        raise SystemExit(f"Colonne manquante dans features_by_airline.csv : '{c}'")

feat["airline_norm"] = feat["airline"].map(norm_name)

# compléter fleet_size si absent/NaN avec AIR3
if "fleet_size" not in feat.columns or feat["fleet_size"].isna().any():
    if air3 is not None:
        feat = feat.merge(air3[["airline_norm","fleet_size"]], on="airline_norm", how="left", suffixes=("","_air3"))
        if "fleet_size_x" in feat.columns:
            feat["fleet_size"] = feat["fleet_size_x"].fillna(feat.get("fleet_size_y"))
            feat = feat.drop(columns=[c for c in feat.columns if c.endswith("_x") or c.endswith("_y")])
    else:
        feat["fleet_size"] = feat.get("fleet_size", 0)

feat["fleet_size"] = to_num(feat["fleet_size"]).fillna(0)

# diversity : si absente, on la recalcule
if "diversity" not in feat.columns:
    n_models = to_num(feat.get("n_models", 0)).fillna(0)
    feat["diversity"] = (n_models / feat["fleet_size"]).replace([float("inf")], 0).fillna(0).clip(0, 1)
else:
    feat["diversity"] = to_prop(feat["diversity"])

# ---------- 3) composantes modernité ----------
# Si pct_newgen_* manquent, on les reconstruit avec les pct_* unitaires si dispo
def col(c): return c in feat.columns

if not (col("pct_newgen_narrow") and col("pct_newgen_wide")):
    # créer colonnes manquantes à 0 pour la somme
    for c in ["pct_neo","pct_max","pct_a220","pct_787","pct_a350","pct_a330neo"]:
        if c not in feat.columns: feat[c] = 0
        feat[c] = to_prop(feat[c])
    feat["pct_newgen_narrow"] = (feat["pct_neo"] + feat["pct_max"] + feat["pct_a220"]).clip(0, 1)
    feat["pct_newgen_wide"]   = (feat["pct_787"] + feat["pct_a350"] + feat["pct_a330neo"]).clip(0, 1)
else:
    feat["pct_newgen_narrow"] = to_prop(feat["pct_newgen_narrow"])
    feat["pct_newgen_wide"]   = to_prop(feat["pct_newgen_wide"])

# pct_a220 pour bonus dédié
if "pct_a220" not in feat.columns:
    feat["pct_a220"] = 0.0
feat["pct_a220"] = to_prop(feat["pct_a220"])

# ---------- 4) calcul des scores ----------
feat["modernity_index"] = (
    0.4*feat["pct_newgen_narrow"].fillna(0) +
    0.4*feat["pct_newgen_wide"].fillna(0) +
    0.2*feat["pct_a220"].fillna(0)
).clip(0, 1)

# ---------- 5) QA notes ----------
qa = pd.Series([""] * len(feat), index=feat.index)

small = feat["fleet_size"] < MIN_FLEET
qa.loc[small] = (qa.loc[small] + ";fleet_too_small").str.strip(";")

missing_components = feat[["pct_newgen_narrow","pct_newgen_wide","pct_a220"]].isna().any(axis=1)
qa.loc[missing_components] = (qa.loc[missing_components] + ";missing_component").str.strip(";")

feat["qa_notes"] = qa.replace("", pd.NA).fillna("")

# ---------- 6) export ----------
out = feat[[
    "airline", "fleet_size", "diversity", "modernity_index", "qa_notes"
]].copy()
out["version_v1"] = "v1"

# ordre final
out = out[["airline","fleet_size","diversity","modernity_index","version_v1","qa_notes"]]

DST.write_text("")  # s'assure que le chemin est créable si besoin
out.to_csv(DST, index=False, encoding="utf-8")
print(f"OK → {DST} | compagnies = {len(out)}")
