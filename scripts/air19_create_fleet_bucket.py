# -*- coding: utf-8 -*-
"""
AIR-19 — Créer label fleet_bucket (Small/Medium/Large)
- Source : release/features_by_airline.csv
- Logique : buckets basés sur les tertiles de fleet_size
- Résultat : release/features_knn.csv (toutes les features + colonne fleet_bucket)
"""

from pathlib import Path
import pandas as pd

SRC = Path("release/features_by_airline.csv")
DST = Path("release/features_knn.csv")

if not SRC.exists():
    raise SystemExit(f"Introuvable : {SRC.resolve()}")

# ---------- 1) Charger les données ----------
df = pd.read_csv(SRC)

if "fleet_size" not in df.columns:
    raise SystemExit("Colonne 'fleet_size' introuvable dans features_by_airline.csv")

# On ignore les lignes sans fleet_size pour le calcul des tertiles
fleet = df["fleet_size"].dropna()

if fleet.empty:
    raise SystemExit("Aucune valeur de fleet_size disponible pour calculer les tertiles.")

# ---------- 2) Calcul des tertiles ----------
q1, q2 = fleet.quantile([1/3, 2/3])

print("Seuils des tertiles de fleet_size :")
print(f" - Small  : fleet_size <= {q1:.2f}")
print(f" - Medium : {q1:.2f} < fleet_size <= {q2:.2f}")
print(f" - Large  : fleet_size > {q2:.2f}")

def bucket_fleet_size(x):
    if pd.isna(x):
        return None  # ou "Unknown" si tu préfères
    if x <= q1:
        return "Small"
    elif x <= q2:
        return "Medium"
    else:
        return "Large"

# ---------- 3) Appliquer le bucket ----------
df["fleet_bucket"] = df["fleet_size"].apply(bucket_fleet_size)

print("\nRépartition par bucket :")
print(df["fleet_bucket"].value_counts(dropna=False))

# ---------- 4) Sauvegarde ----------
DST.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(DST, index=False, encoding="utf-8")

print(f"\nOK : fichier écrit -> {DST}")
