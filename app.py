"""VTEX SKU Finder — Streamlit Interface."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

from src.config import get_credentials
from src.services.vtex_service import VTEXService
from src.utils.validators import is_valid_url

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_URL_DISPLAY_LENGTH: int = 70
_REQUEST_CONCURRENCY: int = 5        # Tune based on VTEX rate-limit headroom
_SLEEP_BETWEEN_BATCHES: float = 0.1  # Seconds between concurrent batches

# ---------------------------------------------------------------------------
# Credentials (loaded once at module level — safe; no I/O side-effects here)
# ---------------------------------------------------------------------------
_app_key, _app_token, _account_name = get_credentials()

# ---------------------------------------------------------------------------
# Logging with Secret Masking
# ---------------------------------------------------------------------------
class _SecretsMasker(logging.Filter):
    """Strips credential values from log records before emission."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        # Only track secrets long enough to be meaningful
        self._secrets = [s for s in secrets if s and len(s) > 5]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        for secret in self._secrets:
            msg = msg.replace(secret, "***MASKED***")
        record.msg = msg
        return True


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    masker = _SecretsMasker([_app_token, _app_key])
    for handler in logging.root.handlers:
        handler.addFilter(masker)


_configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cached Service — instantiated once per Streamlit session
# ---------------------------------------------------------------------------
@st.cache_resource
def _get_vtex_service() -> VTEXService:
    """Returns a cached VTEXService instance, avoiding per-render reconstruction."""
    return VTEXService(_app_key, _app_token, _account_name)


# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(page_title="VTEX SKU Finder", page_icon="🔍", layout="wide")

_CUSTOM_CSS = """
<style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #004b93;
        color: white;
        font-weight: 600;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #003366;
        border: none;
    }
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_urls(raw_text: str) -> tuple[list[str], list[str]]:
    """Separates valid from invalid URLs found in raw multi-line input."""
    valid: list[str] = []
    invalid: list[str] = []
    for line in raw_text.splitlines():
        url = line.strip()
        if not url:
            continue
        (valid if is_valid_url(url) else invalid).append(url)
    return valid, invalid


def _fetch_single(service: VTEXService, url: str) -> dict:
    """
    Wraps a single SKU lookup with error isolation.

    Returning a structured error dict instead of raising ensures
    one bad URL never aborts the entire batch.
    """
    try:
        return service.get_sku_by_url(url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error fetching SKU for %s", url)
        return {
            "url": url,
            "slug": "N/A",
            "product_name": "N/A",
            "sku": "N/A",
            "ean": "N/A",
            "ref_id": "N/A",
            "brand_name": "N/A",
            "status": f"Error: {exc}",
        }


def _process_urls(service: VTEXService, urls: list[str]) -> pd.DataFrame:
    """
    Fetches SKUs concurrently using a thread pool.

    Results are collected as futures complete, keeping the progress bar
    accurate regardless of individual request latency.
    """
    results: list[dict] = [{}] * len(urls)   # Pre-allocate to preserve order
    url_to_index = {url: idx for idx, url in enumerate(urls)}

    progress_bar = st.progress(0)
    status_text = st.empty()
    completed = 0

    with ThreadPoolExecutor(max_workers=_REQUEST_CONCURRENCY) as executor:
        future_to_url = {
            executor.submit(_fetch_single, service, url): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            result = future.result()          # _fetch_single never raises
            results[url_to_index[url]] = result

            completed += 1
            progress_bar.progress(completed / len(urls))
            status_text.text(
                f"Processing {completed}/{len(urls)}: "
                f"{url[:_URL_DISPLAY_LENGTH]}…"
            )

            # Brief pause between completions to stay within rate-limit budgets
            if completed < len(urls):
                time.sleep(_SLEEP_BETWEEN_BATCHES)

    status_text.text("✅ Processing complete!")
    return pd.DataFrame(results)


def _render_results(df: pd.DataFrame) -> None:
    """Displays the results table and offers a CSV export."""
    st.divider()
    st.subheader("📊 Results")

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "url":          st.column_config.LinkColumn("URL"),
            "slug":         st.column_config.TextColumn("Slug"),
            "product_name": st.column_config.TextColumn("Product Name"),
            "sku":          st.column_config.TextColumn("SKU ID"),
            "ean":          st.column_config.TextColumn("EAN"),
            "ref_id":       st.column_config.TextColumn("Ref ID"),
            "brand_name":   st.column_config.TextColumn("Brand Name"),
            "status":       st.column_config.TextColumn("Status"),
        },
    )

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Results (CSV)",
        data=csv_bytes,
        file_name="vtex_skus_results.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point for the Streamlit application."""
    st.title("🔍 VTEX SKU Finder")
    st.markdown("Easily and cleanly extract SKU IDs from VTEX product URLs.")

    # --- Credentials Gate ---
    if not _app_key or not _app_token:
        st.error(
            "⚠️ VTEX credentials not found. "
            "Configure them via **Streamlit Secrets** or a local `.env` file."
        )
        st.stop()

    service = _get_vtex_service()

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info(f"**VTEX Account:** {_account_name}")
        st.divider()
        st.markdown("### How to use")
        st.markdown(
            "1. Paste one or more URLs into the text area (one per line).\n"
            "2. Click **Process URLs**.\n"
            "3. View the retrieved SKUs and export them to CSV."
        )

    # --- Input Area ---
    # Use an explicit session_state key so the Clear button can reset it cleanly
    if "url_input" not in st.session_state:
        st.session_state["url_input"] = ""

    col_input, col_actions = st.columns([3, 1])

    with col_input:
        url_input: str = st.text_area(
            "Enter URLs (one per line):",
            key="url_input",
            height=200,
            placeholder=(
                "https://www.bemol.com.br/produto-exemplo/p\n"
                "https://www.bemol.com.br/outro-produto/p"
            ),
        )

    with col_actions:
        st.markdown("### Actions")
        process_btn = st.button("🚀 Process URLs", type="primary")
        
        def clear_urls() -> None:
            st.session_state["url_input"] = ""
            
        st.button("🗑️ Clear", on_click=clear_urls)

    # --- Processing ---
    if process_btn:
        if not url_input.strip():
            st.warning("Please enter at least one URL.")
            st.stop()

        valid_urls, invalid_urls = _parse_urls(url_input)

        if invalid_urls:
            with st.expander(f"⚠️ {len(invalid_urls)} invalid URL(s) ignored"):
                for url in invalid_urls:
                    st.code(url, language=None)

        if not valid_urls:
            st.error("No valid URLs were found.")
            st.stop()

        df = _process_urls(service, valid_urls)
        _render_results(df)


if __name__ == "__main__":
    main()