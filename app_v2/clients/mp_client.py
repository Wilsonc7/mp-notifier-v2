import requests

BASE_URL = "https://api.mercadopago.com"


def mp_search_payments(access_token: str, limit: int = 10):
    """
    Busca los pagos más recientes del usuario en Mercado Pago.

    Args:
        access_token (str): Token de acceso de la API de Mercado Pago.
        limit (int): Número máximo de resultados (por defecto 10).

    Returns:
        dict: JSON con la lista de pagos o un dict vacío si hubo error.
    """
    url = f"{BASE_URL}/v1/payments/search?sort=date_created&criteria=desc&limit={limit}"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[mp_client] Error al consultar pagos: {e}")
        return {}
