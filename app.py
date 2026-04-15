"""VTEX SKU Finder — Streamlit Interface."""

import logging
import time

import pandas as pd
import streamlit as st

from src.config import get_credentials
from src.services.vtex_service import VTEXService
from src.utils.validators import is_valid_url

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
app_key, app_token, account_name = get_credentials()

# ---------------------------------------------------------------------------
# Logging with Secret Masking
# ---------------------------------------------------------------------------
class SecretsMasker(logging.Filter):
    """Filters outgoing logs and strips any secrets found in them."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, str):
            record.msg = str(record.msg)
            
        if app_token and len(app_token) > 5:
            record.msg = record.msg.replace(app_token, "***MASKED_TOKEN***")
        if app_key and len(app_key) > 5:
            record.msg = record.msg.replace(app_key, "***MASKED_KEY***")
            
        return True

# Make sure basic configuration creates the root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

# Apply masker to all existing logging handlers
for handler in logging.root.handlers:
    handler.addFilter(SecretsMasker())

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
    """Separates valid and invalid URLs from raw input text."""
    valid: list[str] = []
    invalid: list[str] = []
    for line in raw_text.splitlines():
        url = line.strip()
        if not url:
            continue
        (valid if is_valid_url(url) else invalid).append(url)
    return valid, invalid


def _process_urls(service: VTEXService, urls: list[str]) -> pd.DataFrame:
    """Queries the API for each URL and returns a DataFrame with the results."""
    results: list[dict] = []
    progress = st.progress(0)
    status = st.empty()

    for idx, url in enumerate(urls, start=1):
        status.text(f"Processing {idx}/{len(urls)}: {url[:60]}…")
        results.append(service.get_sku_by_url(url))
        progress.progress(idx / len(urls))
        
        # Slight throttle to gracefully adhere to general rate distributions
        # The service also has a built-in Exponential Backoff mechanism via urllib3 Retry
        if idx < len(urls):
            time.sleep(0.1)

    status.text("✅ Processing complete!")
    return pd.DataFrame(results)


def _render_results(df: pd.DataFrame) -> None:
    """Displays the results table and CSV download button."""
    st.divider()
    st.subheader("📊 Results")

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("URL"),
            "slug": st.column_config.TextColumn("Slug"),
            "product_name": st.column_config.TextColumn("Product Name"),
            "sku": st.column_config.TextColumn("SKU ID"),
            "status": st.column_config.TextColumn("Status"),
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
    if not app_key or not app_token:
        st.error(
            "⚠️ VTEX Credentials not found. "
            "Please configure them via **Streamlit Secrets** or a local `.env` file."
        )
        st.stop()

    service = VTEXService(app_key, app_token, account_name)

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info(f"**VTEX Account:** {account_name}")
        st.divider()
        st.markdown("### How to use")
        st.markdown(
            "1. Paste one or more URLs into the text area (one per line).\n"
            "2. Click **Process URLs**.\n"
            "3. View the retrieved SKUs and export them to CSV."
        )

    # --- Input Area ---
    col_input, col_actions = st.columns([3, 1])

    with col_input:
        url_input = st.text_area(
            "Enter URLs (one per line):",
            height=200,
            placeholder=(
                "https://www.bemol.com.br/produto-exemplo/p\n"
                "https://www.bemol.com.br/outro-produto/p"
            ),
        )

    with col_actions:
        st.markdown("### Actions")
        process_btn = st.button("🚀 Process URLs", type="primary")
        if st.button("🗑️ Clear"):
            st.rerun()

    # --- Processing ---
    if process_btn:
        if not url_input.strip():
            st.warning("Please enter at least one URL.")
            st.stop()

        valid_urls, invalid_urls = _parse_urls(url_input)

        if invalid_urls:
            with st.expander(f"⚠️ {len(invalid_urls)} invalid URL(s) ignored"):
                for u in invalid_urls:
                    st.code(u, language=None)

        if not valid_urls:
            st.error("No valid URLs were found.")
            st.stop()

        df = _process_urls(service, valid_urls)
        _render_results(df)


if __name__ == "__main__":
    main()
