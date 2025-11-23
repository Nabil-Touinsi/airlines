# -*- coding: utf-8 -*-
"""
AIR-20 — GridSearch k et évaluation KNN
- Source : release/features_knn.csv
- Cible  : fleet_bucket (Small/Medium/Large)
- Split  : 80% train / 20% test
- Grid   : k ∈ {1,3,5,7,9}
- Sorties :
    * release/knn_confusion_matrix.csv
    * release/knn_report.txt
    * release/knn_confusion_matrix.png
    * release/knn_f1_per_class.png
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
)

SRC = Path("release/features_knn.csv")
OUT_CM = Path("release/knn_confusion_matrix.csv")
OUT_REPORT = Path("release/knn_report.txt")

# ---------- 1) Charger les données ----------
if not SRC.exists():
    raise SystemExit(f"Introuvable : {SRC.resolve()}")

df = pd.read_csv(SRC)

if "fleet_bucket" not in df.columns:
    raise SystemExit("Colonne 'fleet_bucket' introuvable dans features_knn.csv")

# ---------- 2) Préparer X (features) et y (cible) ----------
# On enlève les colonnes non pertinentes pour le modèle
cols_to_drop = ["airline", "fleet_bucket", "fleet_size"]  # évite la fuite via fleet_size
X = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
y = df["fleet_bucket"]

print("Shape X :", X.shape)
print("Répartition de y :")
print(y.value_counts())

# ---------- 3) Split train / test ----------
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

print("\nTaille train :", X_train.shape[0])
print("Taille test  :", X_test.shape[0])

# ---------- 4) GridSearch sur k ----------
param_grid = {"n_neighbors": [1, 3, 5, 7, 9]}

knn = KNeighborsClassifier()

grid = GridSearchCV(
    estimator=knn,
    param_grid=param_grid,
    scoring="f1_macro",  # on optimise F1 macro
    cv=5,
    n_jobs=-1,
)

grid.fit(X_train, y_train)

best_k = grid.best_params_["n_neighbors"]
print(f"\nMeilleur k trouvé : {best_k}")
print(f"Score moyen (F1 macro, CV) : {grid.best_score_:.4f}")

# ---------- 5) Évaluation sur le test ----------
best_model = grid.best_estimator_
y_pred = best_model.predict(X_test)

acc = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, average="macro")

print("\nPerformance sur le test :")
print(f" - Accuracy : {acc:.4f}")
print(f" - F1 macro : {f1:.4f}")

# ---------- 6) Confusion matrix (CSV) ----------
labels_sorted = sorted(y.unique())
cm = confusion_matrix(y_test, y_pred, labels=labels_sorted)

cm_df = pd.DataFrame(
    cm,
    index=[f"true_{cls}" for cls in labels_sorted],
    columns=[f"pred_{cls}" for cls in labels_sorted],
)

OUT_CM.parent.mkdir(parents=True, exist_ok=True)
cm_df.to_csv(OUT_CM, encoding="utf-8")
print(f"\nMatrice de confusion sauvegardée dans : {OUT_CM}")

# ---------- 6bis) Plot matrice de confusion (PNG) ----------
plt.figure()
plt.imshow(cm, interpolation="nearest")
plt.xticks(range(len(labels_sorted)), labels_sorted)
plt.yticks(range(len(labels_sorted)), labels_sorted)
plt.xlabel("Prédit")
plt.ylabel("Vrai")
plt.title("Matrice de confusion KNN (fleet_bucket)")
plt.tight_layout()
plt.savefig("release/knn_confusion_matrix.png", dpi=150)
plt.close()

print("Matrice de confusion plot sauvegardée dans : release/knn_confusion_matrix.png")

# ---------- 7) Classification report (texte + F1 par classe) ----------
# a) dict pour récupérer les F1 par classe
report_dict = classification_report(y_test, y_pred, output_dict=True)

# b) texte pour le fichier .txt
report_text = classification_report(y_test, y_pred)

with OUT_REPORT.open("w", encoding="utf-8") as f:
    f.write("AIR-20 — Rapport KNN (classification fleet_bucket)\n\n")
    f.write(f"Meilleur k : {best_k}\n")
    f.write(f"Accuracy (test) : {acc:.4f}\n")
    f.write(f"F1 macro (test) : {f1:.4f}\n\n")
    f.write("Classification report détaillé :\n")
    f.write(report_text)

print(f"Rapport détaillé sauvegardé dans : {OUT_REPORT}")

# ---------- 8) Graphique F1 par classe ----------
cls_labels = []
f1_scores = []

for cls in labels_sorted:
    if cls in report_dict:
        cls_labels.append(cls)
        f1_scores.append(report_dict[cls]["f1-score"])

plt.figure()
plt.bar(cls_labels, f1_scores)
plt.ylim(0, 1)
plt.xlabel("Classe (fleet_bucket)")
plt.ylabel("F1-score")
plt.title("F1 par classe — modèle KNN")
plt.tight_layout()
plt.savefig("release/knn_f1_per_class.png", dpi=150)
plt.close()

print("Graphique F1 par classe sauvegardé dans : release/knn_f1_per_class.png")

print("\nOK : AIR-20 terminé.")
