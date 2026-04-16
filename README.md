# VTEX SKU Finder – Engineering Documentation

A robust, enterprise-grade Streamlit application engineered to extract VTEX product SKU details directly from e-commerce URLs.

## 📑 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [VTEX Integration Strategy](#vtex-integration-strategy)
3. [Performance & Concurrency](#performance--concurrency)
4. [Security Implementations](#security-implementations)
5. [Project Structure](#project-structure)
6. [Local Setup & Execution](#local-setup--execution)
7. [Testing Strategy](#testing-strategy)
8. [Cloud Deployment](#cloud-deployment)

---

## 🏗️ Architecture Overview

The system is decoupled into three primary layers to ensure maintainability, testability, and isolated failure domains:

1. **Presentation Layer (`app.py`)**: A Streamlit interface responsible completely for rendering inputs, progress bars, and the result data table. Contains no direct HTTP request logic.
2. **Service Layer (`vtex_service.py`)**: A Data Access Layer (DAL) that establishes resilient HTTP session policies, implements the business logic for VTEX API interactions, and parses raw VTEX payloads into structured `SkuResult` objects.
3. **Core Utilities (`config.py`, `validators.py`)**: Handlers for environment configuration, securely loading secrets, and rigorously validating domains before any HTTP requests are dispatched.

---

## 🔌 VTEX Integration Strategy

The core extraction runs a **two-step enrichment process** to bypass VTEX search constraints and gather full catalog data:

1. **Slug Discovery & Base Query**:
   The application intercepts an arbitrary VTEX URL, parses its URI path, and extracts the product `slug` (linkText).
   - **Endpoint**: `GET /api/catalog_system/pub/products/search/{slug}/p`
   - *Engineering Context*: We explicitly map the slug to the URL path rather than using the standard `?fq=productLink:{slug}` parameter constraint. This prevents HTTP 400 Bad Request variations when slugs contain mathematical characters (e.g., `88x188`), avoiding search engine parsing failures.

2. **SKU Deep Enrichment**:
   Once the base `SKU ID` is acquired from the first call, a supplementary private API is queried to extract complementary catalog specifications.
   - **Endpoint**: `GET /api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}`
   - *Fetched Data*: `EAN` (barcodes), `RefId` (reference codes), and `BrandName`.

---

## ⚡ Performance & Concurrency

When users paste large lists of URLs, synchronous `for`-loops introduce severe latency. 
- **Thread Pool Execution**: URL batches are submitted to a `ThreadPoolExecutor`, enabling simultaneous asynchronous lookups without blocking the Streamlit UI frame.
- **Fail-Fast Fault Tolerance**: Individual URL request failures are caught early within isolate futures and return `Error: {exception}` object rows, preventing the whole batch from halting.
- **Rate-Limit Resilience**: The HTTP session uses `urllib3`'s `Retry` strategy to gracefully intercept HTTP `429 Too Many Requests` API throttles. It scales exponentially (1s, 2s, 4s...) rather than throwing connection resets.

---

## 🛡️ Security Implementations

This tool manages sensitive VTEX API Keys and Tokens. Its defense strategy focuses on secret leak prevention and SSRF mitigation.

- **Strict Domain Validation**: The `is_valid_url` component asserts that the URL hostname explicitly belongs to `bemol.com.br` or its subdomains.
- **Secret Masking Logger**: Instantiates a custom `logging.Filter` that scans log messages pre-emission. If a `VTEX_APP_KEY` or `VTEX_APP_TOKEN` string appears anywhere in a traceback, it is scrubbed with `***MASKED***`.
- For deeper vulnerability reporting frameworks, please refer to [SECURITY.md](./SECURITY.md).

---

## 📂 Project Structure

```text
get-sku-from-url/
├── app.py                       # Streamlit Interface (entry point)
├── src/
│   ├── config.py                # Secure credential loading
│   ├── services/
│   │   └── vtex_service.py      # VTEX API Client
│   └── utils/
│       └── validators.py        # Abstract validation logic
├── tests/
│   ├── test_validators.py       # Pytest suite
│   ├── test_vtex_service.py     # VTEX mock testing
│   └── test_api.py              # E2E endpoint troubleshooting
├── requirements.txt
├── .gitignore
└── SECURITY.md
```

---

## 🚀 Local Setup & Execution

### 1. Environment Standardization

```bash
# Example for Windows using Python 3.12+
py -3.12 -m venv .venv_64
.\.venv_64\Scripts\Activate.ps1
```

### 2. Dependency Installation

```bash
pip install -r requirements.txt
```

### 3. Load Secrets

Create an environment file (e.g., `secrets/vtex.env` or `.env` inside the root). *These are covered by .gitignore to prevent exposure.*

```env
VTEX_APP_KEY=vtexappkey-example
VTEX_APP_TOKEN=your_private_vtex_token_here
VTEX_ACCOUNT_NAME=bemol
```

### 4. Boot Web Service

```bash
streamlit run app.py
```

---

## 🧪 Testing Strategy

The application relies on `pytest` to conduct localized unit testing:

```bash
python -m pytest tests/ -v
```

All test units inside `test_vtex_service.py` heavily use `requests-mock` to test the API translation layer without mutating real production VTEX endpoints or consuming actual rate limits.

---

## ☁️ Cloud Deployment (Streamlit)

1. Push your stable codebase to GitHub.
2. Initialize the project mapping on [Streamlit Cloud](https://share.streamlit.io).
3. Access **Settings → Secrets** before deploying, and inject toml configurations:

```toml
[general]
VTEX_APP_KEY = "vtexappkey-example"
VTEX_APP_TOKEN = "your_private_vtex_token_here"
VTEX_ACCOUNT_NAME = "bemol"
```

4. Deploy. Streamlit will mount `config.py` correctly and start mapping queries gracefully.
