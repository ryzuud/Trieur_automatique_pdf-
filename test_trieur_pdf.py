import sys
from unittest.mock import MagicMock

# Mock dependencies that are not installed
sys.modules["pdfplumber"] = MagicMock()
sys.modules["watchdog"] = MagicMock()
sys.modules["watchdog.observers"] = MagicMock()
sys.modules["watchdog.events"] = MagicMock()

import pytest
from trieur_pdf import identifier_fournisseur


@pytest.fixture
def fournisseurs_mock():
    mock_data = {
        "EDF": {
            "nom": "EDF",
            "mots_cles": ["edf", "électricité de france"],
            "dossier": "EDF",
        },
        "Free": {
            "nom": "Free",
            "mots_cles": ["free", "free mobile"],
            "dossier": "Free",
        },
        "Free_Specific": {
            "nom": "Free Specific",
            "mots_cles": ["freebox ultra"],
            "dossier": "Free",
        },
    }

    # Sort the keywords by length, in descending order (longest to shortest)
    for infos in mock_data.values():
        infos["mots_cles"] = sorted(infos["mots_cles"], key=len, reverse=True)

    # Sort the provider dictionary by the length of their longest keyword
    return dict(
        sorted(
            mock_data.items(),
            key=lambda item: (
                max(len(kw) for kw in item[1]["mots_cles"])
                if item[1]["mots_cles"]
                else 0
            ),
            reverse=True,
        )
    )


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
