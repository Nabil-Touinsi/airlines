
# 📘 API de lecture — Projet Airlines (README complet)

## 1. Vue d’ensemble (pour comprendre rapidement)

Schéma simplifié :

[Clients]  →  [API Flask (api.py)]  →  [MySQL airlines_sql]

- Les scripts AIR-1 → AIR-21 produisent les fichiers CSV et la base MySQL `airlines_sql`.
- Le script `sql/air21_schema_and_views.sql` crée les tables et vues (`v_airline_full`, `v_region_modernity`).
- L’API Flask (`api.py`) expose une **API REST en lecture seule** permettant de récupérer les résultats.


---

## 2. Prérequis

- Python 3.x
- Environnement virtuel `.venv`
- Base MySQL initialisée :

```sql
SOURCE sql/air21_schema_and_views.sql;
```

- Configuration dans `api.py` :

```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "root",
    "password": "0000",
    "database": "airlines_sql",
    "charset": "utf8mb4",
}
```

---

## 3. Installation

```bash
.\.venv\Scripts\activate
pip install flask pymysql
```

---

## 4. Lancer l’API

```bash
python api.py
```

Accès :
http://127.0.0.1:5000/health

---

## 5. Endpoints disponibles

### 5.1. GET /health  
Vérifie que l’API fonctionne.

---

### 5.2. GET /airlines  

Query params :  
- limit  
- region (non filtré)

Source SQL : `v_airline_full`

---

### 5.3. GET /clusters/{id}  
Liste des compagnies d’un cluster.

Source SQL : `v_airline_full`

---

### 5.4. GET /regions/summary  
Résumé par région (via `v_region_modernity`)

---

## 6. Limitations connues

- Le paramètre region n’est pas appliqué.
- API Flask en mode développement.

---




