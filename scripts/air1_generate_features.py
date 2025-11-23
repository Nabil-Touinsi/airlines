#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIR-1 | Airlines — Génération des features par compagnie + Indice de modernité (V0)

Fonctions :
- charge dataset.xlsx (feuille "data" par défaut, ou première feuille)
- standardise des colonnes utiles (sans modifier le fichier source)
- crée un drapeau 'new_gen' (heuristique) à partir du nom de modèle
- calcule les agrégats par compagnie
- calcule des indices :
    * indice_modernite_v0  = part d'appareils "new-gen"
    * indice_public        = v0 masqué si flotte < MIN_FLEET
    * indice_penalise      = v0 pénalisé si flotte < MIN_FLEET
- exporte :
    * features_compagnie.xlsx (features + échantillon nettoyé)
    * indice_modernite_v0.xlsx (indices)
    * models_frequency.xlsx (liste des modèles et fréquences) — pour étendre la détection

Usage :
    python air1_generate_features.py --input dataset.xlsx --outdir .
Arguments :
    --input   chemin du fichier Excel source
    --sheet   nom de la feuille (optionnel)
    --outdir  dossier de sortie (défaut = .)
Dépendances : pandas, numpy, openpyxl, xlsxwriter
"""
import argparse
import os
import re
import numpy as np
import pandas as pd

# ===== Paramètres =====
MIN_FLEET = 5  # seuil de fiabilité public

# Motifs "new-gen" élargis (ajoute/ajuste selon tes libellés réels)
NEWGEN_PATTERNS = [
    # Mono-couloir nouvelles générations (Airbus NEO)
    r'\bneo\b',
    r'\ba32\dneo\b',                  # "A320neo", "A321neo"
    r'\ba32\d-2\d{2}n\w?\b',          # "A320-25xN", "A321-27xN" + éventuel suffixe (ex. A321-251NX)
    r'\ba31\d-1\d{2}n\w?\b',          # "A319-151N" (+ éventuel suffixe)
    r'\ba321\s?xlr\b',                # "A321XLR" ou "A321 XLR"
    r'\ba321\s?lr\b',                 # "A321LR"  ou "A321 LR"

    # Long-courrier nouvelles générations
    r'\b787\b',
    r'\ba350\b',
    r'\ba330neo\b',
    r'\ba330-9\d{2}\b',               # "A330-941"
    r'\ba330-8\d{2}\b',               # "A330-841" (A330-800neo)

    # Boeing 737 nouvelle génération (MAX) — variantes sans le mot MAX
    r'\bmax\b',
    r'(^|\s)b?737-7\b',               # "737-7",  "B737-7"
    r'(^|\s)b?737-8\b',               # "737-8",  "B737-8"
    r'(^|\s)b?737-9\b',               # "737-9",  "B737-9"
    r'(^|\s)b?737-10\b',              # "737-10", "B737-10"
    r'(^|\s)b?737-8-200\b',           # "737-8-200" (Ryanair)

    # A220 et précédents (CSeries)
    r'\ba220\b',
    r'\bcs(100|300)\b',               # "CS100", "CS300"
    r'cseries',                       # "CSeries"

    # Embraer E2 (avec ou sans "E2")
    r'embraer.*\be2\b',
    r'\be19[05]-e2\b',
    r'\be19[05]-2\b',                 # "E195-2" / "E190-2"
    r'\be2\b',

    # Autres
    r'\b777x\b'
]



MODEL_COL_CANDIDATES = ["detailed_aircraft_type", "aircraft_type"]
AIRLINE_COL_CANDIDATES = ["airline_name", "airline", "carrier", "company", "operator"]


# ===== Utilitaires =====
def normalize_text_series(s: pd.Series) -> pd.Series:
    """Uppercase + suppression des accents + trim."""
    s = s.astype(str).str.strip()
    s = (s.str.normalize("NFKD")
           .str.encode("ascii", errors="ignore")
           .str.decode("utf-8")
           .str.upper())
    return s


def choose_first_present(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


def detect_new_gen(model: str) -> int:
    if not isinstance(model, str):
        return 0
    m = model.lower()
    return int(any(re.search(pat, m) for pat in NEWGEN_PATTERNS))


# ===== Pipeline principal =====
def main(input_path: str, outdir: str, sheet_name: str = None):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Fichier introuvable: {input_path}")

    xls = pd.ExcelFile(input_path)
    sheet = sheet_name if sheet_name in xls.sheet_names else (sheet_name or ("data" if "data" in xls.sheet_names else xls.sheet_names[0]))
    df = xls.parse(sheet)

    # Choix des colonnes
    airline_col = choose_first_present(df.columns, AIRLINE_COL_CANDIDATES)
    model_col   = choose_first_present(df.columns, MODEL_COL_CANDIDATES)

    if airline_col is None:
        raise RuntimeError("Impossible d'identifier la colonne compagnie (ex: 'airline_name').")
    if model_col is None:
        raise RuntimeError("Impossible d'identifier la colonne modèle (ex: 'detailed_aircraft_type' ou 'aircraft_type').")

    # Dataframe de travail (sans toucher au fichier source)
    work = pd.DataFrame({
        "airline": normalize_text_series(df[airline_col]),
        "model":   normalize_text_series(df[model_col])
    })

    # Drapeau new_gen (heuristique)
    work["new_gen"] = work["model"].apply(detect_new_gen).astype(int)

    # Agrégats par compagnie
    agg = work.groupby("airline").agg(
        fleet_size=("airline", "size"),
        models_diversity=("model", pd.Series.nunique),
        new_gen_share=("new_gen", "mean")
    ).reset_index()

    # Indices
    agg["indice_modernite_v0"] = agg["new_gen_share"]

    agg["low_fleet_flag"] = (agg["fleet_size"] < MIN_FLEET).astype(int)
    agg["indice_public"] = np.where(
        agg["fleet_size"] >= MIN_FLEET,
        agg["indice_modernite_v0"],
        np.nan
    )
    agg["indice_penalise"] = agg["indice_modernite_v0"] * np.minimum(1, agg["fleet_size"] / MIN_FLEET)

    # Tri (public d'abord, puis brut)
    agg_sorted = agg.sort_values(["indice_public", "indice_modernite_v0"], ascending=False, na_position="last")

    # Export
    os.makedirs(outdir, exist_ok=True)
    features_path = os.path.join(outdir, "features_compagnie.xlsx")
    indice_path   = os.path.join(outdir, "indice_modernite_v0.xlsx")
    models_path   = os.path.join(outdir, "models_frequency.xlsx")

    # 1) Features + sample
    with pd.ExcelWriter(features_path, engine="xlsxwriter") as writer:
        work.head(1000).to_excel(writer, sheet_name="sample_raw_clean", index=False)
        agg.to_excel(writer, sheet_name="features_compagnie", index=False)

    # 2) Indices
    cols_out = [
        "airline",
        "indice_modernite_v0",
        "indice_public",
        "indice_penalise",
        "new_gen_share",
        "fleet_size",
        "models_diversity",
        "low_fleet_flag"
    ]
    agg_sorted[cols_out].to_excel(indice_path, index=False)

    # 3) Fréquences de modèles (pour affiner les motifs)
    models_freq = (work.groupby('model')
                        .size()
                        .reset_index(name='count')
                        .sort_values('count', ascending=False))
    models_freq.to_excel(models_path, index=False)

    print(f"[OK] Exporté : {features_path}")
    print(f"[OK] Exporté : {indice_path}")
    print(f"[OK] Exporté : {models_path}")


# ===== CLI =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True, help="Chemin du fichier dataset.xlsx")
    parser.add_argument("--sheet",  default=None, help="Nom de la feuille (optionnel)")
    parser.add_argument("--outdir", default=".", help="Dossier de sortie")
    args = parser.parse_args()

    main(args.input, args.outdir, args.sheet)
