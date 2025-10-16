import requests
from app_v2.models import DB, Payment, Merchant
from sqlalchemy import select

BASE_URL = "https://api.mercadopago.com"


def mp_search_payments(access_token: str, limit: int = 10):
    """
    Consulta los últimos pagos desde la API de Mercado Pago.
    """
    url = f"{BASE_URL}/v1/payments/search?sort=date_created&criteria=desc&limit={limit}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def process_payments(db_session):
    """
    Descarga los pagos de cada merchant y los guarda si son nuevos.
    """
    print("📡 Consultando pagos recientes desde Mercado Pago...")

    merchants = db_session.session.execute(select(Merchant)).scalars().all()
    nuevos = 0

    for m in merchants:
        if not m.access_token:
            continue

        try:
            data = mp_search_payments(m.access_token, limit=5)
            results = data.get("results", [])

            for p in results:
                payment_id = str(p.get("id"))
                existing = db_session.session.execute(
                    select(Payment).where(Payment.payment_id == payment_id)
                ).scalar_one_or_none()

                if not existing:
                    pay = Payment(
                        payment_id=payment_id,
                        status=p.get("status"),
                        amount=p.get("transaction_amount"),
                        description=p.get("description", ""),
                        payer_email=p.get("payer", {}).get("email", ""),
                        merchant_id=m.id,
                    )
                    db_session.session.add(pay)
                    nuevos += 1

            db_session.session.commit()

        except Exception as e:
            print(f"⚠️ Error al procesar pagos de {m.merchant_id}: {e}")

    print(f"✅ {nuevos} nuevos pagos registrados." if nuevos else "ℹ️ Sin pagos nuevos.")
