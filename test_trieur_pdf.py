import pytest
from unittest.mock import patch
from trieur_pdf import git_auto_push

def test_git_auto_push_disabled():
    """Test that git_auto_push returns False immediately if github_url is empty."""
    config = {"github_url": ""}
    with patch("trieur_pdf.executer_commande_git") as mock_exec:
        result = git_auto_push(config)
        assert result is False
        mock_exec.assert_not_called()

def test_git_auto_push_enabled():
    """Test that git_auto_push proceeds if github_url is provided."""
    config = {"github_url": "https://github.com/test/repo.git"}
    with patch("trieur_pdf.executer_commande_git", return_value=(True, "mocked_output")) as mock_exec:
        with patch("trieur_pdf.Path.exists", return_value=True):
            result = git_auto_push(config)
            assert result is True
            # It should at least check the remote url
            mock_exec.assert_any_call("remote", "get-url", "origin")
