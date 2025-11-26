# -*- coding: utf-8 -*-
"""
AIR-26 — Dataviz finale (3 vues)

Objectif :
    Produire 3 visualisations "produit" à partir des exports précédents :

    1) Index moyen par région
       Source : release/region_summary.csv

    2) Top compagnies selon l'index de modernité
       Source : release/airline_scores.csv

    3) PCA 2D colorée par cluster K-means
       Source : release/air15_pca_clusters.csv
                + (optionnel) release/air15_clusters_by_airline.csv

Résultats :
    - release/air26_region_index.png
    - release/air26_top_airlines.png
    - release/air26_pca_clusters.png
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# ---------- Chemins des fichiers (adaptés à ton projet) ----------

REGION_SUMMARY_CSV = Path("release/region_summary.csv")
AIRLINE_SCORES_CSV = Path("release/airline_scores.csv")
PCA_COORDS_CSV = Path("release/air15_pca_clusters.csv")
CLUSTERS_CSV = Path("release/air15_clusters_by_airline.csv")

OUTPUT_DIR = Path("release")
OUTPUT_REGION_FIG = OUTPUT_DIR / "air26_region_index.png"
OUTPUT_TOPN_FIG = OUTPUT_DIR / "air26_top_airlines.png"
OUTPUT_PCA_FIG = OUTPUT_DIR / "air26_pca_clusters.png"


# ---------- 1) Index moyen par région ----------

def plot_region_index(df_region: pd.DataFrame, outpath: Path) -> None:
    """
    df_region doit contenir au minimum :
        - 'region'
        - une colonne numérique représentant l'index moyen
          (index_mean, modernity_index_mean, etc.)
    """
    if "region" not in df_region.columns:
        raise ValueError("La colonne 'region' est absente de region_summary.csv")

    # On essaye de trouver une colonne 'moyenne'
    candidate_cols = [
        "index_mean",
        "modernity_index_mean",
        "mean_modernity_index",
        "mean_index",
    ]
    col_index = None
    for c in candidate_cols:
        if c in df_region.columns:
            col_index = c
            break

    # fallback : première colonne numérique si on n'a rien trouvé
    if col_index is None:
        num_cols = df_region.select_dtypes("number").columns
        if not len(num_cols):
            raise ValueError(
                "Impossible de trouver une colonne numérique d'index moyen "
                "dans region_summary.csv"
            )
        col_index = num_cols[0]

    df_plot = df_region[["region", col_index]].sort_values(col_index, ascending=False)

    plt.figure(figsize=(8, 5))
    plt.barh(df_plot["region"], df_plot[col_index])
    plt.xlabel("Index moyen de modernité")
    plt.title("Index moyen par région")
    plt.gca().invert_yaxis()  # région la plus moderne en haut
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()


# ---------- 2) Top-N compagnies selon modernity_index ----------

def plot_top_airlines(
    df_scores: pd.DataFrame,
    outpath: Path,
    top_n: int = 15,
) -> None:
    """
    df_scores doit contenir :
        - 'airline'
        - 'modernity_index' (score final)
    """

    if "airline" not in df_scores.columns:
        raise ValueError("La colonne 'airline' est absente de airline_scores.csv")

    if "modernity_index" not in df_scores.columns:
        raise ValueError(
            "La colonne 'modernity_index' est absente de airline_scores.csv "
            "(vérifier le fichier)."
        )

    df_top = (
        df_scores[["airline", "modernity_index"]]
        .sort_values("modernity_index", ascending=False)
        .head(top_n)
    )

    plt.figure(figsize=(10, 6))
    plt.barh(df_top["airline"], df_top["modernity_index"])
    plt.xlabel("Index de modernité")
    plt.title(f"Top {top_n} compagnies — modernity_index")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()


# ---------- 3) PCA 2D colorée par cluster ----------

def plot_pca_clusters(df_pca: pd.DataFrame, df_clusters: pd.DataFrame, outpath: Path):
    """
    df_pca doit contenir au minimum :
        - 'airline'
        - 'PC1' / 'pc1'
        - 'PC2' / 'pc2'
        - éventuellement 'cluster'

    df_clusters doit contenir :
        - 'airline'
        - 'cluster'
    """

    if "airline" not in df_pca.columns:
        raise ValueError("df_pca doit contenir la colonne 'airline'.")

    # Normaliser les noms de colonnes PC1 / PC2 (pc1/pc2 -> PC1/PC2)
    rename_map = {}
    if "pc1" in df_pca.columns:
        rename_map["pc1"] = "PC1"
    if "pc2" in df_pca.columns:
        rename_map["pc2"] = "PC2"
    if rename_map:
        df_pca = df_pca.rename(columns=rename_map)

    if "PC1" not in df_pca.columns or "PC2" not in df_pca.columns:
        raise ValueError("df_pca doit contenir les colonnes 'PC1' et 'PC2' (ou 'pc1'/'pc2').")

    # Si df_pca contient déjà cluster (c'est ton cas), on l'utilise directement
    if "cluster" in df_pca.columns:
        df = df_pca.copy()
    else:
        if "airline" not in df_clusters.columns or "cluster" not in df_clusters.columns:
            raise ValueError(
                "df_clusters doit contenir 'airline' et 'cluster' "
                "si df_pca n'a pas déjà 'cluster'."
            )
        df = df_pca.merge(
            df_clusters[["airline", "cluster"]],
            on="airline",
            how="left",
        )

    plt.figure(figsize=(8, 6))

    for cl in sorted(df["cluster"].dropna().unique()):
        sub = df[df["cluster"] == cl]
        plt.scatter(sub["PC1"], sub["PC2"], label=f"Cluster {cl}", alpha=0.8)

    # Cas optionnel : points sans cluster
    if df["cluster"].isna().any():
        sub = df[df["cluster"].isna()]
        plt.scatter(sub["PC1"], sub["PC2"], label="Sans cluster", alpha=0.5, marker="x")

    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title("PCA 2D — compagnies colorées par cluster K-means")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()


# ---------- Main ----------

def main() -> None:
    print("Chargement des fichiers…")

    if not REGION_SUMMARY_CSV.exists():
        raise SystemExit(f"Fichier manquant : {REGION_SUMMARY_CSV}")
    if not AIRLINE_SCORES_CSV.exists():
        raise SystemExit(f"Fichier manquant : {AIRLINE_SCORES_CSV}")
    if not PCA_COORDS_CSV.exists():
        raise SystemExit(f"Fichier manquant : {PCA_COORDS_CSV}")
    if not CLUSTERS_CSV.exists():
        print(
            f"⚠ Attention : {CLUSTERS_CSV} introuvable, "
            "on suppose que air15_pca_clusters.csv contient déjà 'cluster'."
        )

    df_region = pd.read_csv(REGION_SUMMARY_CSV)
    df_scores = pd.read_csv(AIRLINE_SCORES_CSV)
    df_pca = pd.read_csv(PCA_COORDS_CSV)
    df_clusters = (
        pd.read_csv(CLUSTERS_CSV) if CLUSTERS_CSV.exists() else pd.DataFrame()
    )

    print("➡ 1) Index moyen par région…")
    plot_region_index(df_region, OUTPUT_REGION_FIG)
    print(f"   ✔ Sauvegardé : {OUTPUT_REGION_FIG}")

    print("➡ 2) Top compagnies (modernity_index)…")
    plot_top_airlines(df_scores, OUTPUT_TOPN_FIG)
    print(f"   ✔ Sauvegardé : {OUTPUT_TOPN_FIG}")

    print("➡ 3) PCA 2D colorée par cluster…")
    plot_pca_clusters(df_pca, df_clusters, OUTPUT_PCA_FIG)
    print(f"   ✔ Sauvegardé : {OUTPUT_PCA_FIG}")


if __name__ == "__main__":
    main()
