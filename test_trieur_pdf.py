import sys
from unittest.mock import MagicMock

# Mock dependencies that are not installed
sys.modules["pdfplumber"] = MagicMock()
sys.modules["watchdog"] = MagicMock()
sys.modules["watchdog.observers"] = MagicMock()
sys.modules["watchdog.events"] = MagicMock()

import pytest
from trieur_pdf import identifier_fournisseur, extraire_texte
from pathlib import Path
from unittest.mock import patch

@pytest.fixture
def fournisseurs_mock():
    return {
        "EDF": {
            "nom": "EDF",
            "mots_cles": ["électricité de france", "edf"],
            "dossier": "EDF"
        },
        "Free_Specific": {
            "nom": "Free Specific",
            "mots_cles": ["freebox ultra"],
            "dossier": "Free"
        },
        "Free": {
            "nom": "Free",
            "mots_cles": ["free mobile", "free"],
            "dossier": "Free"
        }
    }

def test_identifier_fournisseur_basic(fournisseurs_mock):
    texte = "Ceci est une facture EDF."
    result = identifier_fournisseur(texte, fournisseurs_mock)
    assert result is not None
    assert result["nom"] == "EDF"

def test_identifier_fournisseur_case_insensitive(fournisseurs_mock):
    texte = "Ceci est une facture edf."
    result = identifier_fournisseur(texte, fournisseurs_mock)
    assert result is not None
    assert result["nom"] == "EDF"

def test_identifier_fournisseur_multiple_keywords(fournisseurs_mock):
    # Note: the match is case-insensitive, but "Électricité de France" in the test text
    # should match "électricité de france" if we are careful about accents.
    # The current implementation does .lower() on both.
    texte = "Facture électricité de france pour votre contrat."
    result = identifier_fournisseur(texte, fournisseurs_mock)
    assert result is not None
    assert result["nom"] == "EDF"

def test_identifier_fournisseur_prioritization_longest_keyword_first(fournisseurs_mock):
    # "freebox ultra" is longer than "free"
    texte = "Bienvenue chez Free, voici votre freebox ultra."
    result = identifier_fournisseur(texte, fournisseurs_mock)
    assert result is not None
    assert result["nom"] == "Free Specific"

def test_identifier_fournisseur_no_match(fournisseurs_mock):
    texte = "Ceci est un document inconnu."
    result = identifier_fournisseur(texte, fournisseurs_mock)
    assert result is None

def test_identifier_fournisseur_empty_text(fournisseurs_mock):
    result = identifier_fournisseur("", fournisseurs_mock)
    assert result is None

def test_identifier_fournisseur_empty_fournisseurs():
    result = identifier_fournisseur("EDF", {})
    assert result is None


def test_extraire_texte_success():
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 text"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 text"
    mock_pdf.pages = [mock_page1, mock_page2]

    with patch("trieur_pdf.pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf
        texte = extraire_texte(Path("dummy.pdf"))

    assert "Page 1 text\nPage 2 text\n" == texte


def test_extraire_texte_empty_page():
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 text"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = None
    mock_page3 = MagicMock()
    mock_page3.extract_text.return_value = ""
    mock_page4 = MagicMock()
    mock_page4.extract_text.return_value = "Page 4 text"
    mock_pdf.pages = [mock_page1, mock_page2, mock_page3, mock_page4]

    with patch("trieur_pdf.pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf
        texte = extraire_texte(Path("dummy.pdf"))

    assert "Page 1 text\nPage 4 text\n" == texte


def test_extraire_texte_no_text():
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = None
    mock_pdf.pages = [mock_page1]

    with patch("trieur_pdf.pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf
        texte = extraire_texte(Path("dummy.pdf"))

    assert "" == texte


def test_extraire_texte_exception():
    with patch("trieur_pdf.pdfplumber.open") as mock_open:
        mock_open.side_effect = Exception("Mocked exception")
        texte = extraire_texte(Path("dummy.pdf"))

    assert "" == texte
