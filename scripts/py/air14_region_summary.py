# -*- coding: utf-8 -*-
"""
AIR-14 — Export : release/region_summary.csv

Objectif :
- Résumer la modernité moyenne de la flotte par région
- Mettre en avant les compagnies les plus modernes de chaque région
"""

from pathlib import Path
import pandas as pd
import unicodedata
import re

TOP_N = 3

SRC_RAW = Path("source/dataset.xlsx")
SHEET_RAW = "data"
SRC_MAP = Path("source/country_region_mapping.csv")
SRC_SCORES = Path("release/airline_scores.csv")
DST = Path("release/region_summary.csv")

DST.parent.mkdir(parents=True, exist_ok=True)

# ---------- Helpers de normalisation ----------
STOP_WORDS_FR = {
    "ETAT", "ETATS", "UNIS", "ETATSUNIS",
    "ARABE", "ARABES",
    "EMIRAT", "EMIRATS",
    "REPUBLIQUE", "ROYAUME",
    "UNION", "FEDERALE", "FEDERAL",
    "DU", "DE", "DES", "LA", "LE", "LES", "D", "L",
    "SAINT", "SAINTE"
}

def normalize_str(s: str) -> str:
    """Uppercase + suppression des accents + caractères non alphabétiques."""
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().strip()
    s = re.sub(r"[^A-Z]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def extract_country_tokens(country_clean: str):
    tokens = country_clean.split()
    good = []
    for t in tokens:
        if len(t) < 4:
            continue
        if t in STOP_WORDS_FR:
            continue
        good.append(t)
    return good or tokens

def build_country_token_table(mapping_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in mapping_df.iterrows():
        country = row["country"]
        country_clean = row["country_clean"]
        for tok in extract_country_tokens(country_clean):
            rows.append({"country": country, "token": tok})
    return pd.DataFrame(rows).drop_duplicates()

def guess_country_from_name(airline_name: str, token_table: pd.DataFrame):
    """Heuristique sur le nom de la compagnie."""
    if not isinstance(airline_name, str):
        return None
    name_clean = normalize_str(airline_name)
    if not name_clean:
        return None
    matches = []
    for _, row in token_table.iterrows():
        tok = row["token"]
        if tok and tok in name_clean:
            matches.append(row["country"])
    if not matches:
        return None
    return matches[0]

# ---------- Mapping manuel Compagnie -> Pays (ta liste) ----------
MANUAL_COUNTRY_RAW = {
    "SALAMAIR": "Oman",
    "CEBU PACIFIC": "Philippines",
    "ROYAL AIR MAROC": "Maroc",
    "PHILIPPINE AIRLINES": "Philippines",
    "AERO MONGOLIA": "Mongolie",
    "AIRSWIFT": "Philippines",
    "AUSTRIA - AIR FORCE": "Autriche",
    "BRAZIL - ARMY": "Brésil",
    "CZECHIA - AIR FORCE": "République tchèque",
    "EADS CASA": "Espagne",
    "MAVI GAK AIRLINES": "Turquie",
    "MEXICO - NAVY": "Mexique",
    "RUSSIA - NATIONAL GUARD": "Russie",
    "SINGAPORE - AIR FORCE": "Singapour",
    "SPAIN - GUARDIA CIVIL": "Espagne",
    "TRANSPORTES AAREOS PEGASO": "Mexique",
    "AERO DILI": "Timor oriental",   # important pour matcher le mapping
    "BERMUDAIR": "Bermudes",
    "BH AIR": "Bulgarie",
    "ESTONIA - AIR FORCE": "Estonie",
    "FLYERBIL AIRLINE": "Suède",
    "GREECE - ARMY": "Grèce",
    "HYDRO-QUABEC": "Canada",
    "LATVIA - AIR FORCE": "Lettonie",
    "LIFT": "Afrique du Sud",
    "MOAAMBIQUE EXPRESSO": "Mozambique",
    "MONGOLIAN AIRWAYS": "Mongolie",
    "PERU - NAVY": "Pérou",
    "POLAND - NAVY": "Pologne",
    "PRIVATMAIR": "Suisse",
    "ROYAL STAR AVIATION": "États-Unis",
    "ROYALAIR PHILIPPINES": "Philippines",
    "SEAIR INTERNATIONAL": "Philippines",
    "SERVICIOS AAREOS ILSA": "Mexique",
    "SKYHIGH DOMINICANA": "République dominicaine",
    "SKYJET AIRLINES": "Philippines",
    "SUNLIGHT AIR": "Philippines",
    "SWITZERLAND - AIR FORCE": "Suisse",
    "TAR MEXICO": "Mexique",
    "ZORTE AIR": "Mongolie",
    # Ceux marqués “non déterminé” / “NAN” / “pas compagnie aérienne”
    # restent volontairement sans pays
}

# dictionnaire normalisé pour être robuste (accents, espaces…)
MANUAL_COUNTRY = {normalize_str(k): v for k, v in MANUAL_COUNTRY_RAW.items()}

def get_manual_country(airline_name: str):
    if not isinstance(airline_name, str):
        return None
    key = normalize_str(airline_name)
    return MANUAL_COUNTRY.get(key)

# ---------- 1) Vérifier les fichiers ----------
if not SRC_RAW.exists():
    raise SystemExit(f"Introuvable : {SRC_RAW.resolve()}")
if not SRC_MAP.exists():
    raise SystemExit(f"Introuvable : {SRC_MAP.resolve()}")
if not SRC_SCORES.exists():
    raise SystemExit(f"Introuvable : {SRC_SCORES.resolve()}")

# ---------- 2) Charger les données ----------
raw = pd.read_excel(SRC_RAW, sheet_name=SHEET_RAW)
mapping = pd.read_csv(SRC_MAP)

# Compléter le mapping avec quelques pays manquants
EXTRA_REGION = {
    "Philippines": "Asia",
    "Maroc": "Africa",
    "Mongolie": "Asia",
    "États-Unis": "North America",
}

extra_rows = pd.DataFrame(
    [{"country": c, "region": r} for c, r in EXTRA_REGION.items()]
)

mapping = pd.concat([mapping, extra_rows], ignore_index=True)

scores = pd.read_csv(SRC_SCORES)


# Contrôles colonnes
for col in ["airline_name", "country"]:
    if col not in raw.columns:
        raise SystemExit(f"Colonne manquante dans dataset.xlsx : '{col}'")

for col in ["country", "region"]:
    if col not in mapping.columns:
        raise SystemExit(f"Colonne manquante dans country_region_mapping.csv : '{col}'")

for col in ["airline", "modernity_index"]:
    if col not in scores.columns:
        raise SystemExit(f"Colonne manquante dans airline_scores.csv : '{col}'")

# Normaliser les pays dans le mapping
mapping["country_clean"] = mapping["country"].apply(normalize_str)
mapping["country_norm"] = mapping["country_clean"]

# Table (pays, token) pour l’heuristique
country_tokens = build_country_token_table(mapping)

# ---------- 3) Airline -> pays via dataset ----------
tmp = (
    raw.groupby(["airline_name", "country"])
       .size()
       .reset_index(name="n")
)

idx = tmp.groupby("airline_name")["n"].idxmax()
airline_country = tmp.loc[idx, ["airline_name", "country"]].copy()

airline_country["airline_key"] = (
    airline_country["airline_name"].astype(str).str.upper().str.strip()
)
scores["airline_key"] = (
    scores["airline"].astype(str).str.upper().str.strip()
)

merged = scores.merge(
    airline_country[["airline_key", "country"]],
    on="airline_key",
    how="left",
)

# ---------- 4) Override manuel Compagnie -> Pays ----------
mask_missing_country = merged["country"].isna()
if mask_missing_country.any():
    merged.loc[mask_missing_country, "country_manual"] = merged.loc[mask_missing_country, "airline"].apply(
        get_manual_country
    )
    merged["country"] = merged["country"].fillna(merged["country_manual"])

# ---------- 5) Heuristique sur le nom de la compagnie ----------
mask_missing_country = merged["country"].isna()
if mask_missing_country.any():
    merged.loc[mask_missing_country, "country_guess"] = merged.loc[mask_missing_country, "airline"].apply(
        lambda name: guess_country_from_name(name, country_tokens)
    )
    merged["country"] = merged["country"].fillna(merged["country_guess"])

# ---------- 6) Mapping pays -> région ----------
merged["country_norm"] = merged["country"].apply(
    lambda x: normalize_str(x) if pd.notna(x) else x
)

merged = merged.merge(
    mapping[["country_norm", "region"]],
    on="country_norm",
    how="left",
)

# ---------- Debug : compagnies sans région ----------
missing = merged[merged["region"].isna()][["airline", "country"]].drop_duplicates()
missing_path = Path("release/air14_missing_region.csv")
missing.to_csv(missing_path, index=False, encoding="utf-8")
print(f"{len(missing)} compagnies sans région exportées dans {missing_path}")
print("Compagnies sans région :")
print(missing.sort_values("airline").to_string(index=False))

# ---------- 7) Filtre final ----------
before = len(merged)
merged = merged.dropna(subset=["region", "modernity_index"])
after = len(merged)
if after == 0:
    raise SystemExit("Plus aucune compagnie après filtrage sur 'region' et 'modernity_index'.")

print(f"{before - after} compagnies ignorées (pas de pays/région connue).")

# ---------- 8) Agrégation par région ----------
def build_top_airlines(group, top_n=TOP_N):
    g = group.sort_values("modernity_index", ascending=False).head(top_n)
    return "; ".join(
        f"{row['airline']} ({row['modernity_index']:.3f})"
        for _, row in g.iterrows()
    )

summary_basic = (
    merged
    .groupby("region", as_index=False)
    .agg(
        n_airlines=("airline", "nunique"),
        mean_modernity_index=("modernity_index", "mean"),
    )
)

top_series = (
    merged
    .sort_values("modernity_index", ascending=False)
    .groupby("region")
    .apply(lambda g: build_top_airlines(g, TOP_N))
)

top_df = top_series.reset_index(name="top_airlines")

summary = summary_basic.merge(top_df, on="region")
summary = summary.sort_values("mean_modernity_index", ascending=False)

# ---------- 9) Export ----------
summary.to_csv(DST, index=False, encoding="utf-8")
print(f"OK : {DST} créé avec {len(summary)} lignes.")
