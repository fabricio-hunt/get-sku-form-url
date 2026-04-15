"""Unit tests for src.utils.validators."""

import pytest

from src.utils.validators import is_valid_url


class TestIsValidUrl:
    """Test cases for the is_valid_url function."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.bemol.com.br/produto/p",
            "https://www.bemol.com.br/geladeira-frost-free-340l/p",
            "https://bemol.com.br",
            "https://loja.bemol.com.br/api/test",
            "https://sub.domain.bemol.com.br/path?q=1&b=2",
        ],
    )
    def test_valid_urls(self, url: str) -> None:
        assert is_valid_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "   ",
            "not-a-url",
            "ftp://files.example.com",
            "www.example.com",
            "://missing-scheme.com",
            "just some text",
            "https://example.com/produto/p",  # Unallowed domain
            "https://www.google.com",         # Unallowed domain
        ],
    )
    def test_invalid_urls(self, url: str) -> None:
        assert is_valid_url(url) is False

    def test_strips_whitespace(self) -> None:
        assert is_valid_url("  https://www.bemol.com.br/produto/p  ") is True
