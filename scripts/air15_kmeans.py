# -*- coding: utf-8 -*-
"""
AIR-15 — K-means (clustering)

Objectif :
    Appliquer un clustering K-means sur les compagnies aériennes à partir
    des features préparées dans AIR-15 (air15_features_for_clustering.csv).

Étapes :
    1) Charger le fichier de features.
    2) Séparer l'identifiant (airline) des colonnes numériques.
    3) Standardiser les features numériques.
    4) Tester k dans {2, 3, 4, 5} :
        - entraîner KMeans
        - calculer l'inertie (méthode du coude)
        - calculer le silhouette_score
      -> choisir le k qui maximise le silhouette_score.
    5) Ré-entraîner KMeans avec ce k optimal.
    6) Exporter :
        - release/air15_k_scores.csv            (k, inertia, silhouette)
        - release/air15_clusters_by_airline.csv (airline + features + cluster)
        - release/air15_cluster_centroids.csv   (centroid par cluster, échelle d'origine)
        - release/air15_pca_clusters.csv        (PC1, PC2 pour visualisation)
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
 
SRC = Path("release/air15_features_for_clustering.csv")
DST_K_SCORES = Path("release/air15_k_scores.csv")
DST_CLUSTERS = Path("release/air15_clusters_by_airline.csv")
DST_CENTROIDS = Path("release/air15_cluster_centroids.csv")
DST_PCA = Path("release/air15_pca_clusters.csv")

for p in [DST_K_SCORES, DST_CLUSTERS, DST_CENTROIDS, DST_PCA]:
    p.parent.mkdir(parents=True, exist_ok=True)

# ---------- 1) Charger les données ----------
if not SRC.exists():
    raise SystemExit(f"Introuvable : {SRC.resolve()}")

df = pd.read_csv(SRC)

if "airline" not in df.columns:
    raise SystemExit("La colonne 'airline' est manquante dans le fichier source.")

# Identifiant et features numériques
id_col = "airline"
feature_cols = [c for c in df.columns if c != id_col]

X = df[feature_cols].copy()

# Vérification rapide : toutes numériques ?
if not np.all([np.issubdtype(X[c].dtype, np.number) for c in X.columns]):
    non_numeric = [c for c in X.columns if not np.issubdtype(X[c].dtype, np.number)]
    raise SystemExit(f"Colonnes non numériques détectées : {non_numeric}")

# ---------- 2) Standardisation ----------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------- 3) Tester plusieurs valeurs de k ----------
k_values = [2, 3, 4, 5]
k_results = []

for k in k_values:
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X_scaled)

    inertia = model.inertia_
    sil = silhouette_score(X_scaled, labels)

    k_results.append({"k": k, "inertia": inertia, "silhouette": sil})
    print(f"k={k}  inertia={inertia:.2f}  silhouette={sil:.4f}")

k_df = pd.DataFrame(k_results).sort_values("k")
k_df.to_csv(DST_K_SCORES, index=False, encoding="utf-8")
print(f"\nScores par k exportés vers {DST_K_SCORES}")

# ---------- 4) Choisir le meilleur k (max silhouette) ----------
best_row = max(k_results, key=lambda d: d["silhouette"])
best_k = best_row["k"]
print(f"\n--> k optimal choisi (silhouette max) : k={best_k} (score={best_row['silhouette']:.4f})")

# ---------- 5) Réentraîner KMeans avec k optimal ----------
best_model = KMeans(n_clusters=best_k, n_init=10, random_state=42)
final_labels = best_model.fit_predict(X_scaled)

# ---------- 6) Export des clusters par compagnie ----------
clusters_df = df.copy()
clusters_df["cluster"] = final_labels

clusters_df.to_csv(DST_CLUSTERS, index=False, encoding="utf-8")
print(f"Clusters par compagnie exportés vers {DST_CLUSTERS}")

# ---------- 7) Export des centroïdes (échelle d'origine) ----------
centers_scaled = best_model.cluster_centers_
centers_original = scaler.inverse_transform(centers_scaled)

centroids_df = pd.DataFrame(centers_original, columns=feature_cols)
centroids_df.insert(0, "cluster", range(best_k))

centroids_df.to_csv(DST_CENTROIDS, index=False, encoding="utf-8")
print(f"Centroïdes exportés vers {DST_CENTROIDS}")

# ---------- 8) PCA pour visualisation (2 composantes) ----------
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)

pca_df = pd.DataFrame(
    {
        "airline": df[id_col],
        "cluster": final_labels,
        "pc1": X_pca[:, 0],
        "pc2": X_pca[:, 1],
    }
)

pca_df.to_csv(DST_PCA, index=False, encoding="utf-8")
print(f"PCA (2D) exportée vers {DST_PCA}")

print("\nAIR-15 K-means terminé avec succès.")
