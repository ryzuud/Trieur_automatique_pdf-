import pytest
from pathlib import Path
from trieur_pdf import extraire_date
from unittest.mock import patch, MagicMock

def test_extraire_date_format_texte():
    texte = "Facture du 15 avril 2026 pour les services."
    chemin = Path("dummy.pdf")
    annee, mois = extraire_date(texte, chemin)
    assert annee == "2026"
    assert mois == "04"

def test_extraire_date_format_jj_mm_aaaa():
    texte = "Date : 15/04/2026. A payer avant fin du mois."
    chemin = Path("dummy.pdf")
    annee, mois = extraire_date(texte, chemin)
    assert annee == "2026"
    assert mois == "04"

def test_extraire_date_format_iso():
    texte = "Invoice date: 2026-04-15."
    chemin = Path("dummy.pdf")
    annee, mois = extraire_date(texte, chemin)
    assert annee == "2026"
    assert mois == "04"
