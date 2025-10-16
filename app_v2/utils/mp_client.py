import requests


BASE_URL = "https://api.mercadopago.com"


def mp_search_payments(access_token: str, limit: int = 10):
url = f"{BASE_URL}/v1/payments/search?sort=date_created&criteria=desc&limit={limit}"
headers = {"Authorization": f"Bearer {access_token}"}
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
return resp.json()