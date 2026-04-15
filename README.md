# VTEX SKU Finder

A Streamlit application to retrieve VTEX product SKU IDs from their corresponding URLs.

## 📂 Project Structure

```
get-sku-from-url/
├── app.py                       # Streamlit Interface (entry point)
├── src/
│   ├── config.py                # Credential loading (secrets / .env)
│   ├── services/
│   │   └── vtex_service.py      # VTEX API Integration
│   └── utils/
│       └── validators.py        # URL Validation
├── tests/
│   ├── test_validators.py       # Tests for validators
│   └── test_vtex_service.py     # Tests for vtex_service
├── requirements.txt
└── .gitignore
```

## 🚀 Local Execution

### 1. Create and activate the virtual environment

```bash
# Example for Windows using Python 3.12 (64-bit)
py -3.12 -m venv .venv_64
.\.venv_64\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

Create a `secrets/vtex.env` file in the project root:

```env
VTEX_APP_KEY=your_app_key
VTEX_APP_TOKEN=your_app_token
VTEX_ACCOUNT=bemol
```

### 4. Run the application

```bash
streamlit run app.py
```

### 5. Run tests

```bash
python -m pytest tests/ -v
```

## ☁️ Streamlit Cloud Deployment

1. Push the repository to GitHub (credentials are **not** versioned).
2. Connect the repository on [Streamlit Cloud](https://share.streamlit.io).
3. Under **Settings → Secrets**, add the following configuration:

```toml
VTEX_APP_KEY = "your_app_key"
VTEX_APP_TOKEN = "your_app_token"
VTEX_ACCOUNT = "bemol"
```

4. Click **Deploy**. The application will be available at a public URL.

## ⚙️ How It Works

The application extracts the `slug` (linkText) from the provided URL and queries the VTEX Catalog API using the `?fq=productLink:{slug}` filter to retrieve the product's details and SKUs.

**Endpoint utilized:**
```
GET https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?fq=productLink:{slug}
```
