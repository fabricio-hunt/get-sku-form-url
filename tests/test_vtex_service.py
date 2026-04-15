"""Unit tests for src.services.vtex_service."""

import pytest
from unittest.mock import patch, MagicMock

from src.services.vtex_service import VTEXService, SkuResult, NOT_AVAILABLE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def service() -> VTEXService:
    return VTEXService(
        app_key="fake-key",
        app_token="fake-token",
        account_name="bemol",
    )


# ---------------------------------------------------------------------------
# _extract_slug
# ---------------------------------------------------------------------------
class TestExtractSlug:
    """Tests for slug extraction from a URL."""

    @pytest.mark.parametrize(
        "url, expected_slug",
        [
            ("https://www.bemol.com.br/geladeira-frost-free/p", "geladeira-frost-free"),
            ("https://www.bemol.com.br/categoria/produto-exemplo/p", "produto-exemplo"),
            ("https://www.bemol.com.br/produto-simples", "produto-simples"),
            ("https://www.bemol.com.br/a/b/c/produto-final/p", "produto-final"),
            ("https://www.bemol.com.br/produto-com-trailing-slash/p/", "produto-com-trailing-slash"),
        ],
    )
    def test_extracts_slug_correctly(self, url: str, expected_slug: str) -> None:
        assert VTEXService._extract_slug(url) == expected_slug

    def test_empty_path_returns_empty_string(self) -> None:
        assert VTEXService._extract_slug("https://www.bemol.com.br") == ""
        assert VTEXService._extract_slug("https://www.bemol.com.br/") == ""


# ---------------------------------------------------------------------------
# get_sku_by_url — success scenarios
# ---------------------------------------------------------------------------
class TestGetSkuByUrlSuccess:
    """Tests for successful API query scenarios."""

    MOCK_RESPONSE = [
        {
            "productName": "Geladeira Frost Free 340L",
            "items": [
                {"itemId": "12345", "name": "Geladeira Frost Free 340L - Branca"}
            ],
        }
    ]

    @patch("src.services.vtex_service.requests.get")
    def test_returns_sku_on_success(self, mock_get: MagicMock, service: VTEXService) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = service.get_sku_by_url("https://www.bemol.com.br/geladeira-frost-free/p")

        assert result["sku"] == "12345"
        assert result["product_name"] == "Geladeira Frost Free 340L"
        assert "Success" in result["status"]
        assert result["slug"] == "geladeira-frost-free"

    @patch("src.services.vtex_service.requests.get")
    def test_uses_fq_query_param(self, mock_get: MagicMock, service: VTEXService) -> None:
        """Verifies that the endpoint uses ?fq=productLink:{slug} instead of a path."""
        mock_response = MagicMock()
        mock_response.json.return_value = self.MOCK_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        service.get_sku_by_url("https://www.bemol.com.br/meu-produto/p")

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"] == {"fq": "productLink:meu-produto"}
        assert call_kwargs.args[0].endswith("/search")


# ---------------------------------------------------------------------------
# get_sku_by_url — error scenarios
# ---------------------------------------------------------------------------
class TestGetSkuByUrlErrors:
    """Tests for error scenarios."""

    @patch("src.services.vtex_service.requests.get")
    def test_empty_response_returns_not_found(self, mock_get: MagicMock, service: VTEXService) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = service.get_sku_by_url("https://www.bemol.com.br/produto-inexistente/p")

        assert result["sku"] == NOT_AVAILABLE
        assert "not found" in result["status"].lower()

    @patch("src.services.vtex_service.requests.get")
    def test_product_without_items_returns_error(self, mock_get: MagicMock, service: VTEXService) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [{"productName": "No SKU", "items": []}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = service.get_sku_by_url("https://www.bemol.com.br/sem-sku/p")

        assert result["sku"] == NOT_AVAILABLE
        assert "not found" in result["status"].lower()

    @patch("src.services.vtex_service.requests.get")
    def test_timeout_returns_error(self, mock_get: MagicMock, service: VTEXService) -> None:
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("timeout")

        result = service.get_sku_by_url("https://www.bemol.com.br/produto/p")

        assert result["sku"] == NOT_AVAILABLE
        assert "timeout" in result["status"].lower()

    @patch("src.services.vtex_service.requests.get")
    def test_http_error_returns_status_code(self, mock_get: MagicMock, service: VTEXService) -> None:
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        result = service.get_sku_by_url("https://www.bemol.com.br/produto/p")

        assert "429" in result["status"]

    def test_slug_not_found_returns_error(self, service: VTEXService) -> None:
        result = service.get_sku_by_url("https://www.bemol.com.br/")

        assert result["sku"] == NOT_AVAILABLE
        assert "slug" in result["status"].lower()


# ---------------------------------------------------------------------------
# SkuResult dataclass
# ---------------------------------------------------------------------------
class TestSkuResult:
    """Tests for the SkuResult dataclass."""

    def test_default_values(self) -> None:
        result = SkuResult(url="https://example.com")
        assert result.url == "https://example.com"
        assert result.slug == NOT_AVAILABLE
        assert result.sku == NOT_AVAILABLE
        assert result.status == "Pending"

    def test_dict_conversion(self) -> None:
        result = SkuResult(url="https://example.com", sku="99999")
        d = result.__dict__
        assert isinstance(d, dict)
        assert d["sku"] == "99999"
