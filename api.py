# api.py
# Petite API REST en lecture seule par-dessus la base airlines_sql

from flask import Flask, jsonify, request
import pymysql
from pymysql.err import MySQLError

app = Flask(__name__)

# ------------------------------------------------------------------
# 1) Configuration de la base de données
# ------------------------------------------------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "root",
    "password": "0000",        # ton mot de passe MySQL
    "database": "airlines_sql",
    "charset": "utf8mb4",
}


def get_db_connection():
    """Ouvre une connexion MySQL avec PyMySQL."""
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset=DB_CONFIG["charset"],
        cursorclass=pymysql.cursors.DictCursor,  # renvoie des dicts
    )


# ------------------------------------------------------------------
# 2) Endpoints
# ------------------------------------------------------------------

@app.get("/health")
def healthcheck():
    """Endpoint de test très simple."""
    return jsonify({"status": "ok", "message": "airlines API is alive"})


@app.get("/airlines")
def list_airlines():
    """
    Endpoint de lecture principale.
    - Option : ?region=EU (pour l’instant *non filtré* car la région n’est pas stockée par compagnie en SQL)
    - Option : ?limit=20 pour limiter le nombre de lignes
    """
    region = request.args.get("region")   # ex: "EU" dans la spec Jira
    limit = request.args.get("limit", type=int, default=50)

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Pour l’instant on retourne toutes les compagnies
        # triées par modernity_index_score (le score principal).
        query = """
            SELECT
                airline,
                fleet_size,
                modernity_index_score,
                new_gen_share_features,
                pct_newgen_narrow,
                pct_newgen_wide,
                cluster
            FROM v_airline_full
            ORDER BY modernity_index_score DESC
            LIMIT %s
        """
        params = (limit,)

        # NOTE : on récupère quand même le param region pour plus tard
        # (la BDD actuelle ne stocke pas la région par compagnie).
        # if region:
        #     ... ici on pourrait filtrer si on avait la colonne region ...

        cur.execute(query, params)
        rows = cur.fetchall()

        return jsonify({
            "region_param": region,   # pour voir ce qui a été demandé
            "count": len(rows),
            "airlines": rows,
        })

    except MySQLError as e:
        print("[/airlines] MySQL error:", e)
        return jsonify({"error": "database error"}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@app.get("/clusters/<int:cluster_id>")
def airlines_by_cluster(cluster_id: int):
    """
    Retourne les compagnies appartenant à un cluster donné.
    Exemple : /clusters/0
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT
                airline,
                fleet_size,
                modernity_index_score,
                new_gen_share_features,
                pct_newgen_narrow,
                pct_newgen_wide,
                cluster
            FROM v_airline_full
            WHERE cluster = %s
            ORDER BY modernity_index_score DESC
        """
        cur.execute(query, (cluster_id,))
        rows = cur.fetchall()

        return jsonify({
            "cluster": cluster_id,
            "count": len(rows),
            "airlines": rows,
        })

    except MySQLError as e:
        print("[/clusters] MySQL error:", e)
        return jsonify({"error": "database error"}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@app.get("/regions/summary")
def regions_summary():
    """
    Retourne le résumé par région.
    Utilise la vue SQL v_region_modernity (AIR-21).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT
                region,
                n_airlines,
                mean_modernity_index,
                top_airlines
            FROM v_region_modernity
            ORDER BY mean_modernity_index DESC
        """
        cur.execute(query)
        rows = cur.fetchall()

        return jsonify({
            "count": len(rows),
            "regions": rows,
        })

    except MySQLError as e:
        print("[/regions/summary] MySQL error:", e)
        return jsonify({"error": "database error"}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# 3) Lancement de l’API en local
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
