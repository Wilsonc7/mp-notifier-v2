from datetime import datetime
import requests
from sqlalchemy import select
from .models import Merchant, Payment
from .security import decrypt_token


def mp_search_payments(access_token, limit=10):
    url = f"https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc&limit={limit}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print("Error polling:", e)
        return {"results": []}


def upsert_payment(session, merchant_id, pago):
    if pago.get("status") != "approved":
        return False

    pid = str(pago.get("id"))
    existing = session.get(Payment, pid)
    if existing:
        return False

    p = Payment(
        id=pid,
        merchant_id=merchant_id,
        amount=pago.get("transaction_amount", 0),
        payer_name=(pago.get("payer") or {}).get("first_name") or "Desconocido",
        status=pago.get("status"),
        date_created=datetime.fromisoformat(pago.get("date_created").replace("Z", "+00:00")),
    )
    session.add(p)
    return True


def poll_merchant(session, merchant: Merchant):
    if not merchant.mp_access_token_enc:
        return 0
    try:
        token = decrypt_token(merchant.mp_access_token_enc)
    except Exception:
        return 0

    data = mp_search_payments(token, limit=10)
    created = 0
    for p in data.get("results", []):
        if upsert_payment(session, merchant.id, p):
            created += 1
    if created:
        session.commit()
    return created


def poll_all_merchants(session):
    merchants = session.execute(select(Merchant)).scalars().all()
    total_new = 0
    for m in merchants:
        total_new += poll_merchant(session, m)
    if total_new:
        print(f"[{datetime.utcnow()}] Nuevos pagos: {total_new}")
