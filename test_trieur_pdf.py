import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from trieur_pdf import extraire_texte, MAX_PAGES_TO_EXTRACT

def test_extraire_texte_limits_pages():
    mock_pdf = MagicMock()
    # Create 50 mock pages
    mock_pages = []
    for i in range(50):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = f"Page {i+1} text"
        mock_pages.append(mock_page)

    mock_pdf.pages = mock_pages

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf

        # Call the function
        texte = extraire_texte(Path("dummy.pdf"))

        # Verify that only the first MAX_PAGES_TO_EXTRACT pages were processed
        # Calculate how many pages should have been processed
        expected_pages_processed = min(50, MAX_PAGES_TO_EXTRACT)

        # Check the extracted text lines
        lines = [line for line in texte.split("\n") if line]
        assert len(lines) == expected_pages_processed
        assert lines[-1] == f"Page {expected_pages_processed} text"

        # Verify extract_text was called on exactly MAX_PAGES_TO_EXTRACT pages
        call_count = sum(1 for page in mock_pages if page.extract_text.called)
        assert call_count == expected_pages_processed

def test_extraire_texte_handles_fewer_pages():
    mock_pdf = MagicMock()
    # Create 5 mock pages (less than MAX_PAGES_TO_EXTRACT)
    mock_pages = []
    num_pages = 5
    for i in range(num_pages):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = f"Page {i+1} text"
        mock_pages.append(mock_page)

    mock_pdf.pages = mock_pages

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf

        texte = extraire_texte(Path("dummy.pdf"))

        lines = [line for line in texte.split("\n") if line]
        assert len(lines) == num_pages
        assert lines[-1] == f"Page {num_pages} text"

        call_count = sum(1 for page in mock_pages if page.extract_text.called)
        assert call_count == num_pages
