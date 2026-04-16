import requests
from src.config import get_credentials

app_key, app_token, account_name = get_credentials()
headers = {
    "X-VTEX-API-AppKey": app_key,
    "X-VTEX-API-AppToken": app_token,
    "Accept": "application/json",
}

def test_search(slug):
    print(f"\n--- Testing Search API for slug: {slug} ---")
    url = f"https://{account_name}.vtexcommercestable.com.br/api/catalog_system/pub/products/search"
    params = {"fq": f"productLink:{slug}"}
    try:
        resp = requests.get(url, headers=headers, params=params)
        print(f"Request URL: {resp.request.url}")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

def test_sku(sku_id):
    print(f"\n--- Testing SKU Details API for sku: {sku_id} ---")
    url = f"https://{account_name}.vtexcommercestable.com.br/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
    try:
        resp = requests.get(url, headers=headers)
        print(f"Request URL: {resp.request.url}")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Testting the URLs that failed
    test_search("cama-box-solteiro-marjom-iara-mola-bonnell-euro-top-88x188x62cm")
    test_search("adesivo-dundun-vinil-fcc-75g--mp-")
    # Testing the successful SKU
    test_sku(156082)
