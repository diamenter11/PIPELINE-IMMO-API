from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from database import get_db
from auth import verify_api_key

# ─────────────────────────────────────────────
# Initialisation de l'application
# ─────────────────────────────────────────────
app = FastAPI(
    title="Pipeline Immobilière API",
    description="""
## API REST — Pipeline Immobilière Médaillon AWS

Cette API expose les datamarts Gold de la pipeline immobilière construite sur AWS.

### Sources de données
- **DVF (DGFiP)** : 2,5M+ transactions immobilières 2023-2025
- **INSEE Filosofi** : Revenus médians par commune (millésime 2020)
- **Architecture** : Bronze → Silver → Gold sur AWS S3/Glue/RDS

### Sécurité
Tous les endpoints nécessitent une clé API dans le header `X-API-Key`.

### Conformité RGPD
K-anonymat appliqué : seules les communes avec ≥ 5 transactions sont exposées.
    """,
    version="1.0.0",
    contact={
        "name": "Pipeline Immobilière M2 Data Engineering",
    },
    license_info={
        "name": "Données DVF — Licence Ouverte Etalab 2.0",
        "url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence"
    }
)

# CORS pour le dashboard Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# ENDPOINT 1 : Statistiques globales
# ─────────────────────────────────────────────
@app.get(
    "/stats",
    summary="Statistiques nationales",
    description="Retourne les KPIs globaux de la pipeline : "
                "nombre de communes, transactions totales, prix médian national.",
    tags=["Vue nationale"]
)
async def get_stats(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    result = db.execute(text("""
        SELECT
            COUNT(DISTINCT code_commune) as nb_communes,
            SUM(nb_transactions) as nb_transactions_total,
            ROUND(AVG(prix_m2_moyen)::numeric, 2) as prix_m2_moyen_national,
            ROUND(AVG(prix_m2_median)::numeric, 2) as prix_m2_median_national,
            MIN(annee) as annee_debut,
            MAX(annee) as annee_fin
        FROM gold_prix_commune
    """)).fetchone()

    return {
        "nb_communes_couvertes": result[0],
        "nb_transactions_total": result[1],
        "prix_m2_moyen_national": float(result[2]) if result[2] else 0,
        "prix_m2_median_national": float(result[3]) if result[3] else 0,
        "periode": f"{result[4]}-{result[5]}",
        "source": "DVF DGFiP",
        "conformite_rgpd": "K-anonymat >= 5 transactions appliqué"
    }

# ─────────────────────────────────────────────
# ENDPOINT 2 : Prix par commune
# ─────────────────────────────────────────────
@app.get(
    "/prix-m2",
    summary="Prix au m² pour une commune",
    description="Retourne le prix moyen/médian au m² pour une commune "
                "et un type de bien donné, par année disponible.",
    tags=["Commune"]
)
async def get_prix_commune(
    code_commune: str = Query(..., description="Code INSEE commune (5 chiffres, ex: 75056)"),
    type_bien: Optional[str] = Query(None, description="Appartement ou Maison"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    code_commune = code_commune.zfill(5)

    query = """
        SELECT code_commune, nom_commune, code_departement,
               type_local, annee, nb_transactions,
               prix_m2_moyen, prix_m2_median, prix_m2_min, prix_m2_max
        FROM gold_prix_commune
        WHERE code_commune = :code_commune
    """
    params = {"code_commune": code_commune}

    if type_bien:
        query += " AND type_local = :type_bien"
        params["type_bien"] = type_bien

    query += " ORDER BY annee DESC, type_local"

    results = db.execute(text(query), params).fetchall()

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"Commune {code_commune} non trouvée ou insuffisamment de transactions (seuil RGPD k=5)"
        )

    return [
        {
            "code_commune": r[0],
            "nom_commune": r[1],
            "code_departement": r[2],
            "type_bien": r[3],
            "annee": r[4],
            "nb_transactions": r[5],
            "prix_m2_moyen": float(r[6]) if r[6] else None,
            "prix_m2_median": float(r[7]) if r[7] else None,
            "prix_m2_min": float(r[8]) if r[8] else None,
            "prix_m2_max": float(r[9]) if r[9] else None
        }
        for r in results
    ]

# ─────────────────────────────────────────────
# ENDPOINT 3 : Évolution temporelle
# ─────────────────────────────────────────────
@app.get(
    "/evolution/{code_commune}",
    summary="Évolution des prix pour une commune",
    description="Retourne l'évolution du prix au m² sur 2023-2025 "
                "pour une commune donnée, par type de bien.",
    tags=["Commune"]
)
async def get_evolution(
    code_commune: str,
    type_bien: Optional[str] = Query(None, description="Appartement ou Maison"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    code_commune = code_commune.zfill(5)

    query = """
        SELECT type_local, annee, prix_m2_moyen, nb_transactions
        FROM gold_prix_commune
        WHERE code_commune = :code_commune
    """
    params = {"code_commune": code_commune}

    if type_bien:
        query += " AND type_local = :type_bien"
        params["type_bien"] = type_bien

    query += " ORDER BY type_local, annee"
    results = db.execute(text(query), params).fetchall()

    if not results:
        raise HTTPException(status_code=404, detail="Commune non trouvée")

    # Regrouper par type de bien
    evolution = {}
    for r in results:
        type_b = r[0]
        if type_b not in evolution:
            evolution[type_b] = {"type_bien": type_b, "historique": []}
        evolution[type_b]["historique"].append({
            "annee": r[1],
            "prix_m2_moyen": float(r[2]) if r[2] else None,
            "nb_transactions": r[3]
        })

    # Calcul évolution % 2023→2025
    for type_b, data in evolution.items():
        hist = {h["annee"]: h["prix_m2_moyen"] for h in data["historique"]}
        if 2023 in hist and 2025 in hist and hist[2023]:
            data["evolution_pct_2023_2025"] = round(
                (hist[2025] - hist[2023]) / hist[2023] * 100, 2
            )
        else:
            data["evolution_pct_2023_2025"] = None

    return list(evolution.values())

# ─────────────────────────────────────────────
# ENDPOINT 4 : Top communes
# ─────────────────────────────────────────────
@app.get(
    "/top-communes",
    summary="Classement des communes par prix",
    description="Top N communes les plus chères ou les moins chères "
                "pour un type de bien et une année donnés.",
    tags=["Classements"]
)
async def get_top_communes(
    type_bien: str = Query("Appartement", description="Appartement ou Maison"),
    annee: int = Query(2024, description="Année (2023, 2024 ou 2025)"),
    ordre: str = Query("desc", description="desc = plus chères, asc = moins chères"),
    limit: int = Query(10, description="Nombre de communes à retourner (max 50)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    limit = min(limit, 50)
    ordre_sql = "DESC" if ordre == "desc" else "ASC"

    results = db.execute(text(f"""
        SELECT code_commune, nom_commune, code_departement,
               prix_m2_moyen, prix_m2_median, nb_transactions
        FROM gold_prix_commune
        WHERE type_local = :type_bien
          AND annee = :annee
          AND prix_m2_moyen IS NOT NULL
        ORDER BY prix_m2_moyen {ordre_sql}
        LIMIT :limit
    """), {"type_bien": type_bien, "annee": annee, "limit": limit}).fetchall()

    return [
        {
            "rang": i + 1,
            "code_commune": r[0],
            "nom_commune": r[1],
            "code_departement": r[2],
            "prix_m2_moyen": float(r[3]),
            "prix_m2_median": float(r[4]) if r[4] else None,
            "nb_transactions": r[5]
        }
        for i, r in enumerate(results)
    ]

# ─────────────────────────────────────────────
# ENDPOINT 5 : Agrégation par département
# ─────────────────────────────────────────────
@app.get(
    "/departements",
    summary="Prix moyen par département",
    description="Retourne le prix moyen au m² agrégé par département, "
                "pour alimenter la carte choroplèthe du dashboard.",
    tags=["Vue nationale"]
)
async def get_departements(
    type_bien: str = Query("Appartement", description="Appartement ou Maison"),
    annee: int = Query(2024, description="Année (2023, 2024 ou 2025)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    results = db.execute(text("""
        SELECT
            code_departement,
            ROUND(AVG(prix_m2_moyen)::numeric, 2) as prix_m2_moyen_dept,
            ROUND(AVG(prix_m2_median)::numeric, 2) as prix_m2_median_dept,
            SUM(nb_transactions) as nb_transactions_total,
            COUNT(DISTINCT code_commune) as nb_communes
        FROM gold_prix_commune
        WHERE type_local = :type_bien
          AND annee = :annee
        GROUP BY code_departement
        ORDER BY prix_m2_moyen_dept DESC
    """), {"type_bien": type_bien, "annee": annee}).fetchall()

    return [
        {
            "code_departement": r[0],
            "prix_m2_moyen": float(r[1]) if r[1] else None,
            "prix_m2_median": float(r[2]) if r[2] else None,
            "nb_transactions": r[3],
            "nb_communes": r[4]
        }
        for r in results
    ]

# ─────────────────────────────────────────────
# ENDPOINT 6 : Prix vs Revenu INSEE
# ─────────────────────────────────────────────
@app.get(
    "/comparaison-revenu",
    summary="Comparaison prix immobilier et évolution temporelle",
    description="Croise le prix moyen au m² avec l'évolution 2023-2025 "
                "par commune. Données DVF DGFiP.",
    tags=["Analyse socio-économique"]
)
async def get_comparaison_revenu(
    type_bien: str = Query("Appartement", description="Appartement ou Maison"),
    limit: int = Query(500, description="Nombre de communes (max 2000)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    limit = min(limit, 2000)

    results = db.execute(text("""
        SELECT
            code_commune,
            nom_commune,
            type_local,
            prix_m2_moyen_global,
            evolution_prix_pct_2023_2025,
            nb_transactions_total
        FROM gold_prix_revenu_insee
        WHERE type_local = :type_bien
          AND prix_m2_moyen_global IS NOT NULL
          AND evolution_prix_pct_2023_2025 IS NOT NULL
        ORDER BY prix_m2_moyen_global DESC
        LIMIT :limit
    """), {"type_bien": type_bien, "limit": limit}).fetchall()

    return [
        {
            "code_commune": r[0],
            "nom_commune": r[1],
            "type_bien": r[2],
            "prix_m2_moyen": float(r[3]),
            "evolution_prix_pct_2023_2025": float(r[4]),
            "nb_transactions": r[5]
        }
        for r in results
    ]

# ─────────────────────────────────────────────
# ENDPOINT 7 : Recherche par nom de commune
# ─────────────────────────────────────────────
@app.get(
    "/recherche",
    summary="Rechercher une commune par nom",
    description="Recherche une commune par son nom (recherche partielle). "
                "Utile pour l'autocomplétion dans le dashboard.",
    tags=["Commune"]
)
async def rechercher_commune(
    nom: str = Query(..., description="Nom ou début de nom de commune (ex: 'Par' pour Paris)"),
    limit: int = Query(10, description="Nombre de résultats max"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    results = db.execute(text("""
        SELECT DISTINCT code_commune, nom_commune, code_departement
        FROM gold_prix_commune
        WHERE LOWER(nom_commune) LIKE LOWER(:nom)
        ORDER BY nom_commune
        LIMIT :limit
    """), {"nom": f"%{nom}%", "limit": limit}).fetchall()

    return [
        {
            "code_commune": r[0],
            "nom_commune": r[1],
            "code_departement": r[2]
        }
        for r in results
    ]