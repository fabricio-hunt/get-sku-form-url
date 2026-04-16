"""Integration service for the VTEX Catalog API."""

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
NOT_AVAILABLE = "N/A"


@dataclass
class SkuResult:
    """Structured result from a SKU query."""

    url: str
    slug: str = NOT_AVAILABLE
    product_name: str = NOT_AVAILABLE
    sku: str = NOT_AVAILABLE
    status: str = "Pending"


class VTEXService:
    """Client for the VTEX Catalog Search API.

    Uses the public endpoint ``catalog_system/pub/products/search``
    with the filter ``fq=productLink:{slug}`` to locate a product
    based on the slug extracted from the URL.
    """

    _SEARCH_PATH = "/api/catalog_system/pub/products/search"

    def __init__(self, app_key: str, app_token: str, account_name: str = "bemol") -> None:
        self._account_name = account_name
        self._base_url = f"https://{account_name}.vtexcommercestable.com.br{self._SEARCH_PATH}"
        self._headers = {
            "X-VTEX-API-AppKey": app_key,
            "X-VTEX-API-AppToken": app_token,
            "Accept": "application/json",
        }
        
        # Configure a robust session with Retries against Rate Limiting (429)
        self._session = requests.Session()
        retry_strategy = Retry(
            total=3,  # Max retries
            backoff_factor=1,  # Wait 1s, 2s, 4s... between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    # ------------------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------------------

    def get_sku_by_url(self, url: str) -> dict:
        """Returns a dictionary containing SKU information for the given *url*."""
        slug = self._extract_slug(url)
        result = SkuResult(url=url, slug=slug)

        if not slug:
            result.status = "Error: slug not found in URL"
            return result.__dict__

        return self._fetch_product(result)

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_slug(url: str) -> str:
        """Extracts the slug (linkText) from the product URL.

        Supported examples:
            https://www.bemol.com.br/produto-exemplo/p  → produto-exemplo
            https://www.bemol.com.br/categoria/produto-exemplo/p → produto-exemplo
            https://www.bemol.com.br/produto-exemplo    → produto-exemplo
        """
        path = urlparse(url).path.strip("/")

        if path.endswith("/p"):
            path = path[:-2].rstrip("/")

        segments = path.split("/")
        return segments[-1] if segments else ""

    def _fetch_product(self, result: SkuResult) -> dict:
        """Queries the VTEX API and populates *result* with product data."""
        try:
            logger.info("Querying VTEX — slug: %s", result.slug)
            response = self._session.get(
                self._base_url,
                headers=self._headers,
                params={"fq": f"productLink:{result.slug}"},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            parsed_dict = self._parse_response(response.json(), result)
            
            if result.sku != NOT_AVAILABLE and result.status == "✅ Success":
                extra_details = self._fetch_sku_details(result.sku)
                parsed_dict.update(extra_details)
                
            return parsed_dict

        except requests.exceptions.Timeout:
            logger.error("Timeout querying slug=%s", result.slug)
            result.status = "Error: request timeout"
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP %s for slug=%s", exc.response.status_code, result.slug)
            result.status = f"API Error: {exc.response.status_code}"
        except requests.exceptions.RequestException as exc:
            logger.error("Network failure for slug=%s: %s", result.slug, exc)
            result.status = f"Connection error: {exc}"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error for slug=%s", result.slug)
            result.status = f"Unexpected error: {exc}"

        return result.__dict__

    @staticmethod
    def _parse_response(data: list, result: SkuResult) -> dict:
        """Extracts product_name and sku from the VTEX JSON response."""
        if not data:
            result.status = "Error: product not found"
            return result.__dict__

        product = data[0]
        items = product.get("items", [])

        if not items:
            result.status = "Error: SKU not found for product"
            return result.__dict__

        result.product_name = product.get("productName", NOT_AVAILABLE)
        result.sku = items[0].get("itemId", NOT_AVAILABLE)
        result.status = "✅ Success"
        return result.__dict__

    def _fetch_sku_details(self, sku_id: str) -> dict:
        """Fetches complementary SKU information to enrich the dataset."""
        try:
            logger.info("Querying VTEX SKU details — sku: %s", sku_id)
            url = f"https://{self._account_name}.vtexcommercestable.com.br/api/catalog/pvt/stockkeepingunit/{sku_id}"
            response = self._session.get(
                url,
                headers=self._headers,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to fetch extra details for SKU %s: %s", sku_id, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error fetching extra details for SKU %s: %s", sku_id, exc)
        return {}
