# -*- coding: utf-8 -*-
"""
AIR-5 — Export : release/features_by_airline.csv
- Source agrégée : release/AIR3_dataset_v1.xlsx (1 ligne = 1 compagnie)
- Source brute   : source/dataset.xlsx (feuille 'data') pour calculer n_models
Résultat         : 1 ligne/compagnie avec colonnes standardisées
                   + familles new-gen (n_*/pct_*) pour AIR-9
"""

from pathlib import Path
import re
import pandas as pd

MIN_FLEET = 5

SRC_AGG   = Path("release/AIR3_dataset_v1.xlsx")
SRC_RAW   = Path("source/dataset.xlsx")
SHEET_RAW = "data"
DST       = Path("release/features_by_airline.csv")
DST.parent.mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
def norm_name(s):
    """Normalise un libellé d’entreprise pour fiabiliser la jointure."""
    return str(s).strip().upper()

def to_num(s):
    return pd.to_numeric(s, errors="coerce")

def ratio(num, den):
    num = to_num(num).fillna(0)
    den = to_num(den).replace(0, pd.NA)
    r = (num / den).astype(float)
    return r.fillna(0).clip(0, 1)

# ---------- 1) charger l'agrégé ----------
if not SRC_AGG.exists():
    raise SystemExit(f"Introuvable : {SRC_AGG.resolve()}")
agg = pd.read_excel(SRC_AGG)

# standardise noms de colonnes connus
agg = agg.rename(columns={
    "models_diversity": "diversity"
})

# vérifs minimales
need = ["airline", "fleet_size"]
for c in need:
    if c not in agg.columns:
        raise SystemExit(f"Colonne manquante dans AIR3_dataset_v1.xlsx : '{c}'")

# si 'new_gen_share' absent, le déduire de indice_modernite_v0
if "new_gen_share" not in agg.columns and "indice_modernite_v0" in agg.columns:
    agg["new_gen_share"] = agg["indice_modernite_v0"]

# clé normalisée pour jointure robuste
agg["airline_norm"] = agg["airline"].apply(norm_name)

# ---------- 2) calculer n_models depuis le brut ----------
if not SRC_RAW.exists():
    raise SystemExit(f"Introuvable : {SRC_RAW.resolve()}")
raw = pd.read_excel(SRC_RAW, sheet_name=SHEET_RAW)

AIRLINE_COL = "airline_name"
MODEL_COL   = "detailed_aircraft_type" if "detailed_aircraft_type" in raw.columns else "aircraft_type"
for c in [AIRLINE_COL, MODEL_COL]:
    if c not in raw.columns:
        raise SystemExit(f"Colonne manquante dans {SRC_RAW.name}/{SHEET_RAW} : '{c}'")

raw["airline_norm"] = raw[AIRLINE_COL].apply(norm_name)

# n_models par compagnie (nb de modèles distincts)
n_models = (raw
            .groupby("airline_norm", dropna=False)[MODEL_COL]
            .nunique()
            .rename("n_models")
            .reset_index())

# ---------- 2-bis) familles new-gen par compagnie ----------
PAT = {
    # A220 = ex CSeries (CS100/300) = BD-500-1A10/1A11
    "a220":     re.compile(r"\b(a220-?1(00)?|a220-?3(00)?|cs100|cs300|bd-500-1a1[01])\b", re.I),
    "b787":     re.compile(r"\b787\b", re.I),
    "a350":     re.compile(r"\ba350\b", re.I),
    "a330neo":  re.compile(r"\b(a330-800|a330-900|a330neo|a330-?9?00?neo)\b", re.I),
    # NEO monocouloir (A319/320/321…)
    "neo":      re.compile(r"\b(a31[9]|a32[01])[- ]?\d{2,3}n\b|\b(a31[9]|a32[01])neo\b", re.I),
    # 737 MAX (codes marketing et abréviations équipementiers)
    "max":      re.compile(r"\b(737[- ]?max|7m7|7m8|7m9|7mj|max ?(7|8|9|10))\b", re.I),
}

# on déduplique (airline_norm, modèle) pour éviter les doubles comptes grossiers
models_by_airline = (raw[[ "airline_norm", MODEL_COL ]]
                     .dropna()
                     .drop_duplicates())

def tag_family(model: str):
    s = str(model).lower()
    return {
        "is_a220":    bool(PAT["a220"].search(s)),
        "is_787":     bool(PAT["b787"].search(s)),
        "is_a350":    bool(PAT["a350"].search(s)),
        "is_a330neo": bool(PAT["a330neo"].search(s)),
        "is_neo":     bool(PAT["neo"].search(s)),
        "is_max":     bool(PAT["max"].search(s)),
    }

tags = models_by_airline[MODEL_COL].map(tag_family).apply(pd.Series)
models_tagged = pd.concat([models_by_airline[["airline_norm"]], tags], axis=1)

counts = (models_tagged
          .groupby("airline_norm", dropna=False)
          .sum(numeric_only=True)
          .reset_index()
          .rename(columns={
              "is_a220":"n_a220", "is_787":"n_787", "is_a350":"n_a350",
              "is_a330neo":"n_a330neo", "is_neo":"n_neo", "is_max":"n_max"
          }))

# fusionne ces comptes avec n_models (même clé)
n_models = n_models.merge(counts, on="airline_norm", how="left").fillna(0)

# ---------- 3) fusion + corrections demandées ----------
out = agg.merge(n_models, on="airline_norm", how="left")

# valeurs numériques propres
for c in ["fleet_size", "n_models", "diversity", "new_gen_share",
          "indice_modernite_v0", "indice_public", "indice_penalise"]:
    if c in out.columns:
        out[c] = to_num(out[c])

# recalculs imposés
# - n_models manquants -> 0
out["n_models"] = out["n_models"].fillna(0)

# - diversity = n_models / fleet_size (sécurisée)
out["diversity"] = ratio(out["n_models"], out["fleet_size"])

# - v0 = new_gen_share si présent
if "new_gen_share" in out.columns:
    out["indice_modernite_v0"] = out["new_gen_share"]

# - indices public/pénalisé pour petites flottes
if "new_gen_share" in out.columns:
    out["indice_public"] = out.apply(
        lambda r: 0 if pd.isna(r["fleet_size"]) or r["fleet_size"] < MIN_FLEET else r["new_gen_share"],
        axis=1
    )
    out["indice_penalise"] = out.apply(
        lambda r: (r["new_gen_share"] * 0.8) if pd.isna(r["fleet_size"]) or r["fleet_size"] < MIN_FLEET else r["new_gen_share"],
        axis=1
    )

# --- dériver les pct_* (proportions 0-1), clamp et sécurisation
for c in ["n_a220","n_787","n_a350","n_a330neo","n_neo","n_max"]:
    if c not in out.columns: out[c] = 0
    out[c] = to_num(out[c]).fillna(0)

out["pct_a220"]     = ratio(out["n_a220"],    out["fleet_size"])
out["pct_787"]      = ratio(out["n_787"],     out["fleet_size"])
out["pct_a350"]     = ratio(out["n_a350"],    out["fleet_size"])
out["pct_a330neo"]  = ratio(out["n_a330neo"], out["fleet_size"])
out["pct_neo"]      = ratio(out["n_neo"],     out["fleet_size"])
out["pct_max"]      = ratio(out["n_max"],     out["fleet_size"])

# composantes AIR-9 (prêtes à l'emploi)
out["pct_newgen_narrow"] = (out["pct_neo"] + out["pct_max"] + out["pct_a220"]).clip(0, 1)
out["pct_newgen_wide"]   = (out["pct_787"] + out["pct_a350"] + out["pct_a330neo"]).clip(0, 1)

# dédup sur airline (au cas où)
out = out.drop_duplicates(subset=["airline"], keep="first")

# ---------- colonnes finales et ordre ----------
cols = [
    "airline", "fleet_size", "n_models", "diversity",
    "new_gen_share", "indice_modernite_v0", "indice_public", "indice_penalise",
    "n_a220","n_787","n_a350","n_a330neo","n_neo","n_max",
    "pct_a220","pct_787","pct_a350","pct_a330neo","pct_neo","pct_max",
    "pct_newgen_narrow","pct_newgen_wide"
]
for c in cols:
    if c not in out.columns:
        out[c] = 0
out = out[cols].fillna(0)

# ---------- 4) export ----------
out.to_csv(DST, index=False, encoding="utf-8")
print(f"OK → {DST} | compagnies = {len(out)}")

# ---------- mini validateur ----------
dup_agg     = int(agg["airline"].duplicated().sum())
zero_models = int((out["n_models"] == 0).sum())
neq_v0_ngs  = int(("new_gen_share" in out.columns) and
                  (out["indice_modernite_v0"] != out["new_gen_share"]).sum())
print(f"DUP airl. (AGRÉGÉ) : {dup_agg} | n_models==0 : {zero_models} | v0≠new_gen_share : {neq_v0_ngs}")

# (optionnel) aperçu
print(out.head(10))
