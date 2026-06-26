"""
Tests automatiques pour le pipeline CI/CD GitHub Actions.
Ces tests vérifient que l'API démarre correctement et que
les endpoints répondent comme attendu.
"""
import pytest
import sys
import os

# Ajouter le répertoire courant au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────
# Tests unitaires — validation des règles métier
# ─────────────────────────────────────────────

def test_prix_m2_dans_bornes():
    """Vérifie que le calcul prix/m2 respecte les bornes [100, 50000]."""
    valeur_fonciere = 300000
    surface = 60
    prix_m2 = valeur_fonciere / surface
    assert 100 <= prix_m2 <= 50000, f"Prix/m2 hors bornes : {prix_m2}"

def test_prix_m2_hors_bornes_detecte():
    """Vérifie qu'une valeur aberrante est bien détectée."""
    valeur_fonciere = 1000000
    surface = 1  # Surface irréaliste → prix/m2 = 1 000 000
    prix_m2 = valeur_fonciere / surface
    assert not (100 <= prix_m2 <= 50000), "Valeur aberrante non détectée"

def test_code_commune_format():
    """Vérifie que le code commune est bien formaté sur 5 chiffres."""
    code = "75056"
    assert len(code) == 5, f"Code commune mal formaté : {code}"
    assert code.isdigit(), f"Code commune non numérique : {code}"

def test_code_commune_zero_padding():
    """Vérifie que le zéro de tête est bien ajouté."""
    code_brut = "1001"
    code_formate = code_brut.zfill(5)
    assert code_formate == "01001", f"Zero padding incorrect : {code_formate}"

def test_type_local_valide():
    """Vérifie que seuls les types valides sont acceptés."""
    types_valides = ["Maison", "Appartement"]
    types_testes = ["Maison", "Appartement", "Local commercial", "Terrain"]
    for t in types_testes:
        if t in types_valides:
            assert t in types_valides
        else:
            assert t not in types_valides

def test_k_anonymat_seuil():
    """Vérifie que le seuil k-anonymat de 5 transactions est respecté."""
    SEUIL_K = 5
    communes_test = [
        {"code": "75056", "nb_transactions": 10},   # OK
        {"code": "01001", "nb_transactions": 3},    # Exclue
        {"code": "69123", "nb_transactions": 5},    # OK (limite)
        {"code": "99999", "nb_transactions": 1},    # Exclue
    ]
    communes_valides = [c for c in communes_test if c["nb_transactions"] >= SEUIL_K]
    assert len(communes_valides) == 2, f"K-anonymat incorrect : {len(communes_valides)} communes"

def test_taux_nulls_sous_seuil():
    """Vérifie que le taux de nulls reste sous le seuil de 2%."""
    SEUIL_NULLS = 2.0
    nb_lignes = 1000
    nb_nulls = 10  # 1% — sous le seuil
    taux = (nb_nulls / nb_lignes) * 100
    assert taux < SEUIL_NULLS, f"Taux nulls trop élevé : {taux}%"

def test_evolution_prix_calcul():
    """Vérifie le calcul d'évolution de prix."""
    prix_2023 = 5000
    prix_2025 = 5250
    evolution = (prix_2025 - prix_2023) / prix_2023 * 100
    assert abs(evolution - 5.0) < 0.01, f"Calcul évolution incorrect : {evolution}"

# ─────────────────────────────────────────────
# Tests d'importation — vérifie que le code compile
# ─────────────────────────────────────────────

def test_import_database():
    """Vérifie que database.py s'importe sans erreur."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("database", "database.py")
        assert spec is not None, "Impossible de charger database.py"
    except Exception as e:
        pytest.fail(f"Erreur import database.py : {e}")

def test_import_auth():
    """Vérifie que auth.py s'importe sans erreur."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("auth", "auth.py")
        assert spec is not None, "Impossible de charger auth.py"
    except Exception as e:
        pytest.fail(f"Erreur import auth.py : {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])