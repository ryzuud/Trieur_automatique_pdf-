import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from trieur_pdf import extraire_date

def test_extraire_date_format_texte():
    texte = "La date du document est le 15 avril 2026."
    annee, mois = extraire_date(texte, Path("dummy.pdf"))
    assert annee == "2026"
    assert mois == "04"

def test_extraire_date_format_texte_casse():
    texte = "Fait à Paris, le 3 MARS 2025"
    annee, mois = extraire_date(texte, Path("dummy.pdf"))
    assert annee == "2025"
    assert mois == "03"

def test_extraire_date_format_jj_mm_aaaa():
    texte = "Facture du 15/04/2026"
    annee, mois = extraire_date(texte, Path("dummy.pdf"))
    assert annee == "2026"
    assert mois == "04"

    texte2 = "Date: 10-05-2024"
    annee2, mois2 = extraire_date(texte2, Path("dummy.pdf"))
    assert annee2 == "2024"
    assert mois2 == "05"

def test_extraire_date_format_iso():
    texte = "Date de création : 2026-04-15"
    annee, mois = extraire_date(texte, Path("dummy.pdf"))
    assert annee == "2026"
    assert mois == "04"

@patch('trieur_pdf.os.path.getmtime')
def test_extraire_date_fallback(mock_getmtime):
    # Mock timestamp for 2023-11-20 12:00:00
    mock_getmtime.return_value = datetime(2023, 11, 20, 12, 0, 0).timestamp()
    texte = "Aucune date ici"
    annee, mois = extraire_date(texte, Path("dummy.pdf"))
    assert annee == "2023"
    assert mois == "11"
    mock_getmtime.assert_called_once_with(Path("dummy.pdf"))
