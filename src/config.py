"""Centralized project configuration."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


def _load_local_env() -> None:
    """Loads environment variables from local .env files."""
    candidates = [
        Path("secrets/vtex.env"),
        Path("env/vtex.env"),
        Path(".env"),
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path)
            return


def get_credentials() -> tuple[str, str, str]:
    """Returns (app_key, app_token, account_name).

    Priority order:
      1. ``st.secrets`` (Streamlit Cloud)
      2. Environment variables / local .env files
    """
    # Streamlit Cloud — secrets.toml
    try:
        app_key = st.secrets["VTEX_APP_KEY"]
        app_token = st.secrets["VTEX_APP_TOKEN"]
        account = st.secrets.get("VTEX_ACCOUNT", "bemol")
        return app_key, app_token, account
    except (KeyError, FileNotFoundError):
        pass

    # Local development — .env files
    _load_local_env()

    app_key = os.getenv("VTEX_APP_KEY", "")
    app_token = os.getenv("VTEX_APP_TOKEN", "")
    account = os.getenv("VTEX_ACCOUNT", "bemol")
    return app_key, app_token, account
