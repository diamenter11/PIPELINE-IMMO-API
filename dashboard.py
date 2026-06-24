import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_BASE = "http://35.180.128.101:8000"
API_KEY = "pipeline-immo-secret-key-2024"
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(
    page_title="Pipeline Immobiliere — Dashboard",
    layout="wide"
)

@st.cache_data(ttl=300)
def get_stats():
    r = requests.get(f"{API_BASE}/stats", headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=300)
def get_departements(type_bien, annee):
    r = requests.get(f"{API_BASE}/departements",
                     headers=HEADERS,
                     params={"type_bien": type_bien, "annee": annee})
    return r.json() if r.status_code == 200 else []

@st.cache_data(ttl=300)
def get_top_communes(type_bien, annee, ordre, limit):
    r = requests.get(f"{API_BASE}/top-communes",
                     headers=HEADERS,
                     params={"type_bien": type_bien, "annee": annee,
                             "ordre": ordre, "limit": limit})
    return r.json() if r.status_code == 200 else []

@st.cache_data(ttl=300)
def get_comparaison(type_bien, limit=1000):
    r = requests.get(f"{API_BASE}/comparaison-revenu",
                     headers=HEADERS,
                     params={"type_bien": type_bien, "limit": limit})
    return r.json() if r.status_code == 200 else []

def get_commune(code_commune, type_bien=None):
    params = {"code_commune": code_commune}
    if type_bien:
        params["type_bien"] = type_bien
    r = requests.get(f"{API_BASE}/prix-m2", headers=HEADERS, params=params)
    return r.json() if r.status_code == 200 else []

def rechercher(nom):
    r = requests.get(f"{API_BASE}/recherche",
                     headers=HEADERS,
                     params={"nom": nom, "limit": 10})
    return r.json() if r.status_code == 200 else []

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.title("Pipeline Immobiliere — Dashboard Gold")
st.markdown("""
**Source :** DVF DGFiP x INSEE Filosofi | **Architecture :** AWS S3 -> Glue -> RDS -> FastAPI -> EC2
""")
st.divider()

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────
stats = get_stats()
if stats:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Communes couvertes",
                f"{stats.get('nb_communes_couvertes', 0):,}".replace(",", " "))
    col2.metric("Transactions analysees",
                f"{stats.get('nb_transactions_total', 0):,}".replace(",", " "))
    col3.metric("Prix median national",
                f"{stats.get('prix_m2_median_national', 0):,.0f} EUR/m2".replace(",", " "))
    col4.metric("Periode couverte", stats.get("periode", "2023-2025"))
    st.divider()

# ─────────────────────────────────────────────
# Filtres globaux
# ─────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
type_bien = col_f1.selectbox("Type de bien", ["Appartement", "Maison"])
annee = col_f2.selectbox("Annee", [2025, 2024, 2023])

# ─────────────────────────────────────────────
# Section 1 — Prix par departement
# ─────────────────────────────────────────────
st.subheader(f"Prix moyen au m2 par departement — {type_bien} {annee}")

dept_data = get_departements(type_bien, annee)
if dept_data:
    df_dept = pd.DataFrame(dept_data)
    df_dept = df_dept[df_dept["prix_m2_moyen"].notna()]
    df_dept["code_departement"] = df_dept["code_departement"].astype(str).str.zfill(2)
    df_dept_sorted = df_dept.sort_values("prix_m2_moyen", ascending=True).tail(30)

    fig_dept = px.bar(
        df_dept_sorted,
        x="prix_m2_moyen",
        y="code_departement",
        orientation="h",
        color="prix_m2_moyen",
        color_continuous_scale="RdYlGn_r",
        labels={
            "prix_m2_moyen": "Prix moyen au m2 (EUR)",
            "code_departement": "Departement"
        },
        text="prix_m2_moyen",
        title=f"Top 30 departements par prix au m2 — {type_bien} {annee}"
    )
    fig_dept.update_traces(texttemplate="%{text:.0f} EUR", textposition="outside")
    fig_dept.update_layout(
        height=700,
        showlegend=False,
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"}
    )
    st.plotly_chart(fig_dept, use_container_width=True)

    st.dataframe(
        df_dept.sort_values("prix_m2_moyen", ascending=False)[
            ["code_departement", "prix_m2_moyen", "prix_m2_median",
             "nb_transactions", "nb_communes"]
        ].rename(columns={
            "code_departement": "Departement",
            "prix_m2_moyen": "Prix moyen (EUR/m2)",
            "prix_m2_median": "Prix median (EUR/m2)",
            "nb_transactions": "Transactions",
            "nb_communes": "Communes"
        }).head(20),
        use_container_width=True
    )

st.divider()

# ─────────────────────────────────────────────
# Section 2 — Classement communes
# ─────────────────────────────────────────────
st.subheader(f"Classement des communes — {type_bien} {annee}")

col_t1, col_t2 = st.columns(2)

with col_t1:
    st.markdown("**Top 10 communes les plus cheres**")
    top_cher = get_top_communes(type_bien, annee, "desc", 10)
    if top_cher:
        df_cher = pd.DataFrame(top_cher)
        fig_cher = px.bar(
            df_cher,
            x="prix_m2_moyen",
            y="nom_commune",
            orientation="h",
            color="prix_m2_moyen",
            color_continuous_scale="Reds",
            labels={
                "prix_m2_moyen": "Prix/m2 (EUR)",
                "nom_commune": "Commune"
            },
            text="prix_m2_moyen"
        )
        fig_cher.update_traces(texttemplate="%{text:.0f} EUR",
                                textposition="outside")
        fig_cher.update_layout(
            height=400,
            showlegend=False,
            coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig_cher, use_container_width=True)

with col_t2:
    st.markdown("**Top 10 communes les moins cheres**")
    top_abordable = get_top_communes(type_bien, annee, "asc", 10)
    if top_abordable:
        df_abordable = pd.DataFrame(top_abordable)
        fig_abordable = px.bar(
            df_abordable,
            x="prix_m2_moyen",
            y="nom_commune",
            orientation="h",
            color="prix_m2_moyen",
            color_continuous_scale="Greens_r",
            labels={
                "prix_m2_moyen": "Prix/m2 (EUR)",
                "nom_commune": "Commune"
            },
            text="prix_m2_moyen"
        )
        fig_abordable.update_traces(texttemplate="%{text:.0f} EUR",
                                     textposition="outside")
        fig_abordable.update_layout(
            height=400,
            showlegend=False,
            coloraxis_showscale=False,
            yaxis={"categoryorder": "total descending"}
        )
        st.plotly_chart(fig_abordable, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# Section 3 — Scatter prix vs evolution
# ─────────────────────────────────────────────
st.subheader("Prix au m2 vs Evolution 2023-2025")
st.caption("Filtre applique : evolution entre -30% et +30% (valeurs aberrantes exclues)")

comparaison_data = get_comparaison(type_bien, 1000)
if comparaison_data:
    df_comp = pd.DataFrame(comparaison_data)
    df_comp = df_comp[df_comp["evolution_prix_pct_2023_2025"].notna()]

    # Filtre valeurs aberrantes
    df_comp = df_comp[
        (df_comp["evolution_prix_pct_2023_2025"] >= -30) &
        (df_comp["evolution_prix_pct_2023_2025"] <= 30)
    ]

    fig_scatter = px.scatter(
        df_comp,
        x="evolution_prix_pct_2023_2025",
        y="prix_m2_moyen",
        hover_name="nom_commune",
        size="nb_transactions",
        color="prix_m2_moyen",
        color_continuous_scale="RdYlGn_r",
        labels={
            "evolution_prix_pct_2023_2025": "Evolution prix 2023-2025 (%)",
            "prix_m2_moyen": "Prix moyen au m2 (EUR)",
            "nb_transactions": "Nb transactions"
        },
        title=f"Prix/m2 vs Evolution temporelle — {type_bien}"
    )
    fig_scatter.add_vline(x=0, line_dash="dash", line_color="gray",
                          annotation_text="Stable")
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

    col_s1, col_s2, col_s3 = st.columns(3)
    hausse = df_comp[df_comp["evolution_prix_pct_2023_2025"] > 0]
    baisse = df_comp[df_comp["evolution_prix_pct_2023_2025"] < 0]
    col_s1.metric("Communes en hausse",
                  f"{len(hausse):,}".replace(",", " "))
    col_s2.metric("Communes en baisse",
                  f"{len(baisse):,}".replace(",", " "))
    col_s3.metric("Communes analysees",
                  f"{len(df_comp):,}".replace(",", " "))

st.divider()

# ─────────────────────────────────────────────
# Section 4 — Recherche commune
# ─────────────────────────────────────────────
st.subheader("Rechercher une commune")

col_r1, col_r2 = st.columns([2, 1])
nom_recherche = col_r1.text_input(
    "Nom de la commune",
    placeholder="ex: Lyon, Bordeaux, Nantes..."
)
type_recherche = col_r2.selectbox(
    "Type de bien",
    ["Appartement", "Maison"],
    key="type_recherche"
)

if nom_recherche:
    suggestions = rechercher(nom_recherche)
    if suggestions:
        options = {
            f"{s['nom_commune']} ({s['code_departement']})": s["code_commune"]
            for s in suggestions
        }
        choix = st.selectbox("Communes trouvees", list(options.keys()))
        code_selectionne = options[choix]

        data_commune = get_commune(code_selectionne, type_recherche)
        if data_commune:
            df_commune = pd.DataFrame(data_commune)

            derniere_annee = df_commune[
                df_commune["annee"] == df_commune["annee"].max()
            ]
            if not derniere_annee.empty:
                row = derniere_annee.iloc[0]
                col_c1, col_c2, col_c3 = st.columns(3)
                col_c1.metric(
                    "Prix moyen/m2",
                    f"{row['prix_m2_moyen']:,.0f} EUR".replace(",", " ")
                )
                col_c2.metric(
                    "Prix median/m2",
                    f"{row['prix_m2_median']:,.0f} EUR".replace(",", " ")
                    if row['prix_m2_median'] else "N/A"
                )
                col_c3.metric(
                    "Transactions",
                    f"{row['nb_transactions']:,}".replace(",", " ")
                )

            fig_evol = px.line(
                df_commune.sort_values("annee"),
                x="annee",
                y="prix_m2_moyen",
                color="type_bien",
                markers=True,
                labels={
                    "annee": "Annee",
                    "prix_m2_moyen": "Prix/m2 (EUR)",
                    "type_bien": "Type"
                },
                title=f"Evolution du prix/m2 — {choix}"
            )
            fig_evol.update_layout(height=350)
            st.plotly_chart(fig_evol, use_container_width=True)
        else:
            st.warning(
                "Aucune donnee disponible pour cette commune "
                "(seuil RGPD k-anonymat : minimum 5 transactions requises)"
            )
    else:
        st.info("Aucune commune trouvee. Essayez un autre nom.")

st.divider()
st.caption(
    "Donnees DVF DGFiP | INSEE Filosofi 2020 | "
    "Architecture AWS S3/Glue/RDS/EC2 | "
    "RGPD : k-anonymat >= 5 transactions"
)