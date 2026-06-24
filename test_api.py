import requests
import json

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "pipeline-immo-secret-key-2024"
HEADERS = {"X-API-Key": API_KEY}

def print_result(endpoint, response):
    print(f"\n{'='*60}")
    print(f"ENDPOINT : {endpoint}")
    print(f"STATUS   : {response.status_code}")
    print(f"RÉPONSE  :")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        print("..." if len(json.dumps(data)) > 500 else "")
    except:
        print(response.text[:300])
    print(f"{'='*60}")

# ─────────────────────────────────────────────
# Test 1 — Statistiques globales
# ─────────────────────────────────────────────
print("\n🔵 TEST 1 — /stats")
r = requests.get(f"{BASE_URL}/stats", headers=HEADERS)
print_result("/stats", r)

# ─────────────────────────────────────────────
# Test 2 — Prix pour Paris (75056)
# ─────────────────────────────────────────────
print("\n🔵 TEST 2 — /prix-m2?code_commune=75056&type_bien=Appartement")
r = requests.get(
    f"{BASE_URL}/prix-m2",
    headers=HEADERS,
    params={"code_commune": "75056", "type_bien": "Appartement"}
)
print_result("/prix-m2", r)

# ─────────────────────────────────────────────
# Test 3 — Évolution temporelle Paris
# ─────────────────────────────────────────────
print("\n🔵 TEST 3 — /evolution/75056")
r = requests.get(
    f"{BASE_URL}/evolution/75056",
    headers=HEADERS,
    params={"type_bien": "Appartement"}
)
print_result("/evolution/75056", r)

# ─────────────────────────────────────────────
# Test 4 — Top 10 communes les plus chères
# ─────────────────────────────────────────────
print("\n🔵 TEST 4 — /top-communes (Appartement 2024 DESC)")
r = requests.get(
    f"{BASE_URL}/top-communes",
    headers=HEADERS,
    params={"type_bien": "Appartement", "annee": 2024, "ordre": "desc", "limit": 10}
)
print_result("/top-communes", r)

# ─────────────────────────────────────────────
# Test 5 — Top 10 communes les moins chères
# ─────────────────────────────────────────────
print("\n🔵 TEST 5 — /top-communes (Maison 2024 ASC)")
r = requests.get(
    f"{BASE_URL}/top-communes",
    headers=HEADERS,
    params={"type_bien": "Maison", "annee": 2024, "ordre": "asc", "limit": 10}
)
print_result("/top-communes", r)

# ─────────────────────────────────────────────
# Test 6 — Prix par département
# ─────────────────────────────────────────────
print("\n🔵 TEST 6 — /departements (Appartement 2024)")
r = requests.get(
    f"{BASE_URL}/departements",
    headers=HEADERS,
    params={"type_bien": "Appartement", "annee": 2024}
)
print_result("/departements", r)

# ─────────────────────────────────────────────
# Test 7 — Comparaison prix vs revenu INSEE
# ─────────────────────────────────────────────
print("\n🔵 TEST 7 — /comparaison-revenu (Appartement, 20 communes)")
r = requests.get(
    f"{BASE_URL}/comparaison-revenu",
    headers=HEADERS,
    params={"type_bien": "Appartement", "limit": 20}
)
print_result("/comparaison-revenu", r)

# ─────────────────────────────────────────────
# Test 8 — Recherche par nom
# ─────────────────────────────────────────────
print("\n🔵 TEST 8 — /recherche?nom=Lyon")
r = requests.get(
    f"{BASE_URL}/recherche",
    headers=HEADERS,
    params={"nom": "Lyon", "limit": 5}
)
print_result("/recherche", r)

# ─────────────────────────────────────────────
# Test 9 — Sécurisation : appel sans clé API
# ─────────────────────────────────────────────
print("\n🔴 TEST 9 — Sans clé API (doit retourner 403)")
r = requests.get(f"{BASE_URL}/stats")
print_result("/stats SANS clé", r)

# ─────────────────────────────────────────────
# Test 10 — Sécurisation : mauvaise clé API
# ─────────────────────────────────────────────
print("\n🔴 TEST 10 — Mauvaise clé API (doit retourner 403)")
r = requests.get(
    f"{BASE_URL}/stats",
    headers={"X-API-Key": "mauvaise-cle"}
)
print_result("/stats MAUVAISE CLÉ", r)

print("\n✅ Tests terminés.")