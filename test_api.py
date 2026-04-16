import requests

from src.config import get_credentials

app_key, app_token, account_name = get_credentials()

for sku_id in [10002161741, 1, 2, 3, 4, 5]:
    try:
        resp = requests.get(
            f"https://{account_name}.vtexcommercestable.com.br/api/catalog/pvt/stockkeepingunit/{sku_id}",
            headers={
                "X-VTEX-API-AppKey": app_key,
                "X-VTEX-API-AppToken": app_token,
                "Accept": "application/json",
            }
        )
        if resp.status_code == 200:
            import json
            print(f"\nFound SKU Details for {sku_id}:")
            data = resp.json()
            # print only keys and types to save space
            print({k: type(v).__name__ for k, v in data.items()})
            print(json.dumps(data, indent=2))
            break
        else:
            print(f"SKU {sku_id} returned {resp.status_code}")
    except Exception as e:
        print(f"Error for {sku_id}: {e}")
