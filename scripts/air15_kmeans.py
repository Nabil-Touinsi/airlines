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
        - release/air15_k_scores.csv
        - release/air15_clusters_by_airline.csv
        - release/air15_cluster_centroids.csv
        - release/air15_pca_clusters.csv
    7) Générer des visualisations :
        - courbe du coude
        - courbe silhouette
        - scatter PCA 2D coloré par cluster
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Fichiers d'entrée / sortie
SRC = Path("release/air15_features_for_clustering.csv")

DST_K_SCORES = Path("release/air15_k_scores.csv")
DST_CLUSTERS = Path("release/air15_clusters_by_airline.csv")
DST_CENTROIDS = Path("release/air15_cluster_centroids.csv")
DST_PCA = Path("release/air15_pca_clusters.csv")

# Figures
FIG_ELBOW = Path("release/air15_kmeans_elbow.png")
FIG_SILH = Path("release/air15_kmeans_silhouette.png")
FIG_PCA = Path("release/air15_kmeans_pca_clusters.png")

for p in [
    DST_K_SCORES,
    DST_CLUSTERS,
    DST_CENTROIDS,
    DST_PCA,
    FIG_ELBOW,
    FIG_SILH,
    FIG_PCA,
]:
    p.parent.mkdir(parents=True, exist_ok=True)

# ---------- 1) Charger les données ----------
if not SRC.exists():
    raise SystemExit(f"Introuvable : {SRC.resolve()}")

df = pd.read_csv(SRC)

if "airline" not in df.columns:
    raise SystemExit("La colonne 'airline' est manquante.")

id_col = "airline"
feature_cols = [c for c in df.columns if c != id_col]

X = df[feature_cols].copy()

# Vérifier numérique
if not np.all([np.issubdtype(X[c].dtype, np.number) for c in X.columns]):
    non_numeric = [c for c in X.columns if not np.issubdtype(X[c].dtype, np.number)]
    raise SystemExit(f"Colonnes non numériques détectées : {non_numeric}")

# ---------- 2) Standardisation ----------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------- 3) Tester plusieurs valeurs de k ----------
k_values = [2, 3, 4, 5]
k_results = []

print("=== Test des différentes valeurs de k ===")
for k in k_values:
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X_scaled)

    inertia = model.inertia_
    sil = silhouette_score(X_scaled, labels)

    k_results.append({"k": k, "inertia": inertia, "silhouette": sil})
    print(f"k={k}  inertia={inertia:.2f}  silhouette={sil:.4f}")

k_df = pd.DataFrame(k_results).sort_values("k")
k_df.to_csv(DST_K_SCORES, index=False)
print(f"\nScores par k exportés vers {DST_K_SCORES}")

# ---------- 3bis) Visualisation inertie / silhouette ----------
try:
    # Elbow
    fig, ax = plt.subplots()
    ax.plot(k_df["k"], k_df["inertia"], marker="o")
    ax.set_xlabel("k")
    ax.set_ylabel("Inertie")
    ax.set_title("K-means — méthode du coude")
    fig.savefig(FIG_ELBOW, bbox_inches="tight")
    plt.close(fig)

    # Silhouette
    fig, ax = plt.subplots()
    ax.plot(k_df["k"], k_df["silhouette"], marker="o")
    ax.set_xlabel("k")
    ax.set_ylabel("Score de silhouette")
    ax.set_title("K-means — score silhouette")
    fig.savefig(FIG_SILH, bbox_inches="tight")
    plt.close(fig)

    print(f"Graphiques inertie / silhouette exportés.")
except Exception as e:
    print(f"⚠️ Erreur graphiques k: {e}")

# ---------- 4) Choisir k optimal ----------
best_row = max(k_results, key=lambda d: d["silhouette"])
best_k = best_row["k"]
print(f"\n--> k optimal = {best_k} (silhouette={best_row['silhouette']:.4f})")

# ---------- 5) Réentraîner KMeans ----------
best_model = KMeans(n_clusters=best_k, n_init=10, random_state=42)
final_labels = best_model.fit_predict(X_scaled)

# ---------- 6) Export clusters ----------
clusters_df = df.copy()
clusters_df["cluster"] = final_labels
clusters_df.to_csv(DST_CLUSTERS, index=False)
print(f"Clusters exportés → {DST_CLUSTERS}")

# ---------- 7) Export centroïdes ----------
centers_scaled = best_model.cluster_centers_
centers_original = scaler.inverse_transform(centers_scaled)

centroids_df = pd.DataFrame(centers_original, columns=feature_cols)
centroids_df.insert(0, "cluster", range(best_k))
centroids_df.to_csv(DST_CENTROIDS, index=False)
print(f"Centroïdes exportés → {DST_CENTROIDS}")

# ---------- 8) PCA ----------
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)

pca_df = pd.DataFrame({
    "airline": df[id_col],
    "cluster": final_labels,
    "pc1": X_pca[:, 0],
    "pc2": X_pca[:, 1],
})
pca_df.to_csv(DST_PCA, index=False)
print(f"PCA exportée → {DST_PCA}")

# ---------- 8bis) Visualisation PCA corrigée ----------
try:
    fig, ax = plt.subplots()
    scatter = ax.scatter(pca_df["pc1"], pca_df["pc2"], c=pca_df["cluster"], s=30)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(f"PCA 2D — K-means (k={best_k})")

    # Correction ici : on récupère handles + labels séparés
    handles, labels = scatter.legend_elements()
    legend = ax.legend(handles, labels, title="Cluster", loc="best")
    ax.add_artist(legend)

    fig.savefig(FIG_PCA, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure PCA exportée → {FIG_PCA}")

except Exception as e:
    print(f"⚠️ Erreur PCA : {e}")

print("\nAIR-15 K-means terminé avec succès.")
